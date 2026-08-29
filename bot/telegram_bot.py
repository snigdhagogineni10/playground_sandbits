"""
Telegram bot — full command and message routing layer.

Handles all pipelines:
  - /start           : two-step language pair selector
  - /setlang         : re-open language pair selector mid-session
  - /explain <text>  : concept simplification alias
  - /summarise       : generate summary of last output
  - Text message     : concept simplification or transcript translation (auto-classified)
  - Video/document   : video dubbing pipeline or transcript translation
  - URL in text      : video dubbing pipeline
  - Feedback buttons : feedback loop (regeneration with new mode)
"""

import logging
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config
from utils.session import get_session, update_session
from utils.language_map import get_name, SUPPORTED_LANGUAGES
from utils.language_detector import detect_language
from utils.pair_resolver import resolve_pair
from utils.input_classifier import classify_text, classify_document, is_url
from utils.feedback_menu import send_feedback_menu
from services.simplifier import simplify
from services.translator import translate_segments, translate_text
from services.transcriber import transcribe
from services.tts import synthesise_aligned
from services.video_dubber import dub_video
from services.summariser import summarise
from services.link_fetcher import fetch_links
import utils.audio_extractor as audio_extractor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# /start  and  /setlang  — language pair selector
# ---------------------------------------------------------------------------

def _source_keyboard() -> InlineKeyboardMarkup:
    langs = list(SUPPORTED_LANGUAGES.keys())  # 6 language names
    rows = [[InlineKeyboardButton(name, callback_data=f"src:{iso}")]
            for name, iso in SUPPORTED_LANGUAGES.items()]
    rows.append([InlineKeyboardButton("🔍 Auto-detect", callback_data="src:auto")])
    return InlineKeyboardMarkup(rows)


def _target_keyboard(excluded_iso: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(name, callback_data=f"tgt:{iso}")]
        for name, iso in SUPPORTED_LANGUAGES.items()
        if iso != excluded_iso
    ]
    return InlineKeyboardMarkup(rows)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    update_session(chat_id, _step="choose_source")
    await update.message.reply_text(
        "👋 Welcome! Let's set up your language pair.\n\nStep 1: Choose your *source* language:",
        reply_markup=_source_keyboard(),
        parse_mode="Markdown",
    )


async def setlang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-open language pair selector without resetting other session data."""
    chat_id = update.effective_chat.id
    update_session(chat_id, _step="choose_source")
    await update.message.reply_text(
        "🔄 Let's update your language pair.\n\nStep 1: Choose your *source* language:",
        reply_markup=_source_keyboard(),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Callback handler — language pair selection + feedback
# ---------------------------------------------------------------------------

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    session = get_session(chat_id)
    data: str = query.data

    # ---- Language pair selection ----
    if data.startswith("src:"):
        iso = data[4:]
        if iso == "auto":
            update_session(chat_id, source_language="Auto-detect", source_language_code="auto", _step="choose_target")
            await query.edit_message_text(
                "✅ Source: Auto-detect\n\nStep 2: Choose your *target* language:",
                reply_markup=_target_keyboard("auto"),
                parse_mode="Markdown",
            )
        else:
            name = get_name(iso)
            update_session(chat_id, source_language=name, source_language_code=iso, _step="choose_target")
            await query.edit_message_text(
                f"✅ Source: *{name}*\n\nStep 2: Choose your *target* language:",
                reply_markup=_target_keyboard(iso),
                parse_mode="Markdown",
            )

    elif data.startswith("tgt:"):
        iso = data[4:]
        name = get_name(iso)
        src = session.get("source_language", "Auto-detect")
        update_session(chat_id, target_language=name, target_language_code=iso, _step="ready", mode="default")
        await query.edit_message_text(
            f"✅ Language pair set: *{src}* → *{name}*\n\n"
            f"You're all set! Send me:\n"
            f"• A text question or concept to explain\n"
            f"• A video file or URL to dub\n"
            f"• A .txt transcript to translate\n"
            f"• /summarise after any output for a quick summary\n"
            f"• /setlang to change the language pair",
            parse_mode="Markdown",
        )

    # ---- Feedback loop ----
    elif data.startswith("fb:"):
        await _handle_feedback(chat_id, data[3:], query, context)


# ---------------------------------------------------------------------------
# /explain command
# ---------------------------------------------------------------------------

async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Usage: /explain <concept or term>")
        return
    await _run_simplify(chat_id, text, update, context)


# ---------------------------------------------------------------------------
# Text message handler
# ---------------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    text = update.message.text.strip()

    # If awaiting custom feedback text
    if session.get("awaiting_custom_feedback"):
        await _apply_custom_feedback(chat_id, text, update, context)
        return

    # Check if this is a URL
    if is_url(text):
        await _run_video_pipeline(chat_id, text, update, context, is_url_source=True)
        return

    kind = classify_text(text)

    if kind == "summarise":
        await _run_summarise(chat_id, update, context)
    elif kind == "transcript":
        await _run_translate_text(chat_id, text, update, context)
    else:  # concept
        await _run_simplify(chat_id, text, update, context)


# ---------------------------------------------------------------------------
# Document/video handler
# ---------------------------------------------------------------------------

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    doc = update.message.document
    mime = doc.mime_type if doc else None
    fname = doc.file_name if doc else None

    kind = classify_document(mime, fname)

    if kind == "video":
        await _run_video_pipeline(chat_id, None, update, context, doc_obj=doc)
    elif kind == "transcript":
        await _download_and_translate_txt(chat_id, doc, update, context)
    else:
        await update.message.reply_text(
            "⚠️ Unsupported file type. Please send a video file (.mp4, .mkv) or a .txt transcript."
        )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct video file uploads."""
    chat_id = update.effective_chat.id
    video = update.message.video or update.message.document
    await _run_video_pipeline(chat_id, None, update, context, doc_obj=video)


# ---------------------------------------------------------------------------
# /summarise command
# ---------------------------------------------------------------------------

async def summarise_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await _run_summarise(chat_id, update, context)


# ---------------------------------------------------------------------------
# Core pipeline runners
# ---------------------------------------------------------------------------

async def _run_simplify(
    chat_id: int,
    text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    session = get_session(chat_id)
    target_lang = session.get("target_language", "English")
    target_iso = session.get("target_language_code", "en")
    mode = session.get("mode", "default")

    detected_iso = detect_language(text)
    source_iso, _ = resolve_pair(detected_iso, session)
    source_lang = get_name(source_iso) if source_iso != "auto" else "the source language"

    await update.message.reply_text("⏳ Generating explanation…")

    result = simplify(text, source_lang, target_lang, mode)

    update_session(chat_id, last_input_text=text, last_text=result, awaiting_feedback=True)
    await update.message.reply_text(result)
    await send_feedback_menu(chat_id, context.bot, target_lang)


async def _run_translate_text(
    chat_id: int,
    text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    session = get_session(chat_id)
    target_lang = session.get("target_language", "English")
    target_iso = session.get("target_language_code", "en")
    mode = session.get("mode", "default")

    detected_iso = detect_language(text)
    source_iso, _ = resolve_pair(detected_iso, session)
    source_lang = get_name(source_iso) if source_iso != "auto" else "the source language"

    await update.message.reply_text("⏳ Translating transcript…")

    translated = translate_text(text, source_lang, target_lang, mode)

    # Save to temp .txt and send
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tmp.write(translated)
    tmp.close()

    update_session(chat_id, last_text=translated, last_input_text=text, awaiting_feedback=True)

    try:
        with open(tmp.name, "rb") as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f,
                filename=f"translated_{target_iso}.txt",
                caption=f"📄 Translated transcript from {source_lang} to {target_lang}.",
            )
    finally:
        os.unlink(tmp.name)

    await send_feedback_menu(chat_id, context.bot, target_lang)


async def _run_video_pipeline(
    chat_id: int,
    url_source: str | None,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    is_url_source: bool = False,
    doc_obj=None,
) -> None:
    session = get_session(chat_id)
    target_lang = session.get("target_language", "English")
    target_iso = session.get("target_language_code", "en")
    mode = session.get("mode", "default")

    await update.message.reply_text("⏳ Processing video… this may take a minute.")

    tmp_video_path = None
    aligned_audio_path = None
    dubbed_path = None

    try:
        # 1. Get video path
        if is_url_source and url_source:
            source = url_source
            audio_path = audio_extractor.extract_audio(source)
            tmp_video_path = _find_downloaded_video(audio_path)
        elif doc_obj:
            file = await context.bot.get_file(doc_obj.file_id)
            tmp_dir = tempfile.mkdtemp()
            tmp_video_path = os.path.join(tmp_dir, doc_obj.file_name or "video.mp4")
            await file.download_to_drive(tmp_video_path)
            audio_path = audio_extractor.extract_audio(tmp_video_path)
        else:
            await update.message.reply_text("⚠️ Could not locate a video source.")
            return

        # 2. Transcribe
        transcription = transcribe(audio_path)
        segments = transcription["segments"]
        detected_iso = transcription["detected_language"]
        source_iso, target_iso_resolved = resolve_pair(detected_iso, session)
        source_lang = get_name(source_iso)

        if not segments:
            await update.message.reply_text("⚠️ Could not transcribe audio — no speech detected.")
            return

        # 3. Translate segments
        translated_segs = translate_segments(segments, source_lang, target_lang, mode)

        # 4. Synthesise aligned TTS audio
        aligned_audio_path = synthesise_aligned(translated_segs, target_iso)

        # 5. Dub video
        dubbed_path = dub_video(tmp_video_path, aligned_audio_path)

        # 6. Save segments and video path in session for feedback regeneration
        update_session(
            chat_id,
            last_segments=translated_segs,
            last_video_path=tmp_video_path,
            awaiting_feedback=True,
        )

        # 7. Send dubbed video
        file_size = os.path.getsize(dubbed_path)
        with open(dubbed_path, "rb") as f:
            if file_size <= 50 * 1024 * 1024:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=f"🎬 Dubbed from {source_lang} to {target_lang}.",
                )
            else:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    filename="dubbed.mp4",
                    caption=f"🎬 Dubbed from {source_lang} to {target_lang} (large file).",
                )

        await send_feedback_menu(chat_id, context.bot, target_lang)

    except Exception as exc:
        logger.exception("Video pipeline failed: %s", exc)
        await update.message.reply_text(f"❌ Video processing failed: {exc}")
    finally:
        # Clean up temp audio — keep video path in session until user is satisfied
        if aligned_audio_path and os.path.exists(aligned_audio_path):
            _cleanup_dir(os.path.dirname(aligned_audio_path), keep=[tmp_video_path])
        if dubbed_path and os.path.exists(dubbed_path):
            os.unlink(dubbed_path)


async def _download_and_translate_txt(
    chat_id: int,
    doc,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    file = await context.bot.get_file(doc.file_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    await file.download_to_drive(tmp.name)
    with open(tmp.name, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    os.unlink(tmp.name)
    await _run_translate_text(chat_id, text, update, context)


async def _run_summarise(
    chat_id: int,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    session = get_session(chat_id)
    target_lang = session.get("target_language", "English")
    target_iso = session.get("target_language_code", "en")
    mode = session.get("mode", "default")
    source_lang = session.get("source_language", "English")

    content = session.get("last_input_text") or session.get("last_text")
    if not content:
        await update.message.reply_text(
            "⚠️ No recent content to summarise. Please send a concept or transcript first."
        )
        return

    await update.message.reply_text("⏳ Generating summary…")

    result = summarise(content, source_lang, target_lang, mode)
    summary_text = result["summary_text"]

    # Fetch reference links
    links = fetch_links(content, num_links=3)

    # Format message
    message = summary_text
    if links:
        message += "\n\n📚 *References:*"
        for link in links:
            emoji = "🎬" if link["type"] == "video" else "📄"
            message += f"\n{emoji} [{link['title']}]({link['url']})"

    update_session(chat_id, last_summary=summary_text, awaiting_feedback=True)

    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    await send_feedback_menu(chat_id, context.bot, target_lang)


# ---------------------------------------------------------------------------
# Feedback loop
# ---------------------------------------------------------------------------

async def _handle_feedback(
    chat_id: int,
    action: str,
    query,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    session = get_session(chat_id)
    target_lang = session.get("target_language", "English")

    if action == "satisfied":
        update_session(chat_id, awaiting_feedback=False, mode="default")
        await query.edit_message_text("✅ Great! Let me know if you need anything else.")
        return

    if action == "simpler":
        update_session(chat_id, mode="simpler")
    elif action == "more_english":
        update_session(chat_id, mode="more_english")
    elif action == "custom":
        update_session(chat_id, awaiting_custom_feedback=True)
        await query.edit_message_text("✏️ Please type your feedback:")
        return

    # Regenerate with new mode
    await query.edit_message_text("⏳ Regenerating with your preference…")
    await _regenerate(chat_id, context)


async def _apply_custom_feedback(
    chat_id: int,
    text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    update_session(
        chat_id,
        mode=f"custom:{text}",
        awaiting_custom_feedback=False,
    )
    await update.message.reply_text("⏳ Regenerating with your feedback…")
    await _regenerate(chat_id, context)


async def _regenerate(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Re-run the last pipeline with the current session mode (no re-transcription)."""
    session = get_session(chat_id)
    target_lang = session.get("target_language", "English")
    target_iso = session.get("target_language_code", "en")
    source_lang = session.get("source_language", "English")
    mode = session.get("mode", "default")

    # Determine what to regenerate based on what's cached
    if session.get("last_segments") and session.get("last_video_path"):
        # Re-translate segments + re-dub video
        segs = session["last_segments"]
        video_path = session["last_video_path"]
        try:
            translated_segs = translate_segments(segs, source_lang, target_lang, mode)
            aligned_audio = synthesise_aligned(translated_segs, target_iso)
            dubbed = dub_video(video_path, aligned_audio)
            update_session(chat_id, last_segments=translated_segs, awaiting_feedback=True)
            file_size = os.path.getsize(dubbed)
            with open(dubbed, "rb") as f:
                if file_size <= 50 * 1024 * 1024:
                    await context.bot.send_video(chat_id=chat_id, video=f, caption=f"🎬 {source_lang} → {target_lang}")
                else:
                    await context.bot.send_document(chat_id=chat_id, document=f, filename="dubbed.mp4")
            os.unlink(dubbed)
            if os.path.exists(aligned_audio):
                _cleanup_dir(os.path.dirname(aligned_audio))
        except Exception as exc:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Regeneration failed: {exc}")

    elif session.get("last_text") and session.get("last_input_text"):
        # Re-simplify or re-translate text
        input_text = session["last_input_text"]
        detected_iso = detect_language(input_text)
        source_iso, _ = resolve_pair(detected_iso, session)
        src = get_name(source_iso)

        if len(input_text) >= 300 or "\n" in input_text:
            result = translate_text(input_text, src, target_lang, mode)
        else:
            result = simplify(input_text, src, target_lang, mode)

        update_session(chat_id, last_text=result, awaiting_feedback=True)
        await context.bot.send_message(chat_id=chat_id, text=result)

    else:
        await context.bot.send_message(
            chat_id=chat_id, text="⚠️ Nothing to regenerate. Please send a new concept or video."
        )
        return

    await send_feedback_menu(chat_id, context.bot, target_lang)


# ---------------------------------------------------------------------------
# Application builder
# ---------------------------------------------------------------------------

def build_application() -> Application:
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("setlang", setlang_command))
    app.add_handler(CommandHandler("explain", explain_command))
    app.add_handler(CommandHandler("summarise", summarise_command))
    app.add_handler(CommandHandler("summarize", summarise_command))

    app.add_handler(CallbackQueryHandler(callback_handler))

    # Video file uploads
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    # Documents (.mp4 files come as documents on some clients)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # All text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_downloaded_video(audio_path: str) -> str:
    """Return the video file in the same temp dir as the extracted audio."""
    tmp_dir = os.path.dirname(audio_path)
    for fname in os.listdir(tmp_dir):
        if fname.startswith("video."):
            return os.path.join(tmp_dir, fname)
    return audio_path  # fallback


def _cleanup_dir(directory: str, keep: list[str | None] | None = None) -> None:
    keep_set = {p for p in (keep or []) if p}
    for fname in os.listdir(directory):
        full = os.path.join(directory, fname)
        if full not in keep_set:
            try:
                os.unlink(full)
            except OSError:
                pass
