# Multilingual Education Bot — Plan

## Top-Level Overview

Build a bot (Telegram + WhatsApp) that supports **any-to-any translation** across **6 languages**, with on-demand structured summaries and curated reference links:

> **Supported Languages:** English, Hindi, Telugu, Tamil, Kannada, Malayalam
> **Any pair is valid:** Telugu→Tamil, Hindi→Kannada, Malayalam→English, English→Telugu, Tamil→Hindi, etc.
> Total: 6 × 5 = **30 directional pairs**

### Core behaviours:
1. **Concept simplification** — explain a technical concept in any target language
2. **Smart output by input type:**
   - **Video input (file or URL)** → dubbed video returned (translated audio muxed back in, timestamp-aligned)
   - **Text/transcript input** → translated `.txt` file returned
3. **On-demand summary** — when user sends `/summarise` or "summarise" after any output:
   - Generates a short, structured summary in the user's **target language**
   - Format: bullet points + a comparison/key-concept table where relevant + an illustrative diagram description if helpful
   - Attaches **2–3 curated reference links**: YouTube videos and articles/websites related to the topic
   - Summary stays small and simple — not a re-explanation, just a quick-reference digest
4. **Terminology handling (universal rule across all pairs):**
   - **Technical terms** (variable, array, loop, function, class, etc.) are **always kept or rendered in English** — regardless of source or target language
   - In **video/audio output:** TTS speaks the technical term in English inline (surrounded by the target-language sentence)
   - In **text output:** technical terms are written in **target-language script transliteration + (English)** — e.g. `వేరియబుల్ (variable)` for Telugu, `वेरिएबल (variable)` for Hindi
   - Exception: if the **target is English**, technical terms appear as clean English words only (no parenthetical needed)
4. **Meaning preservation:** every translation verified via GPT-4 back-translation check
5. **Post-output feedback loop** after every output:
   - Option 1: ✅ Satisfied
   - Option 2: 🔄 Simpler — fewer / no English technical terms (use target-language equivalents)
   - Option 3: 📘 More English terms — keep more technical vocabulary in English
   - Option 4: ✏️ Share your own feedback (free-text)
   - Bot regenerates output with the new instruction (no re-transcription for video)

**Tech Stack:**
- Python backend
- `python-telegram-bot` for Telegram
- Twilio API for WhatsApp
- OpenAI Whisper for speech-to-text (auto-detects language; supports all 6)
- OpenAI GPT-4 for translation, simplification, language detection confirmation, back-translation check, feedback-driven regeneration
- `langdetect` library for fast client-side language detection (pre-filter before GPT-4)
- `googlesearch-python` for fetching curated reference links (YouTube + articles)
- Google Text-to-Speech (`gTTS`) for synthesising output audio in all 6 languages
- `ffmpeg` / `ffmpeg-python` for audio extraction and video muxing
- `yt-dlp` for downloading video from online URLs
- `srt` Python library for SRT formatting (internal use)

**Languages & ISO codes:**

| Language  | ISO code |
|-----------|----------|
| English   | en       |
| Hindi     | hi       |
| Telugu    | te       |
| Tamil     | ta       |
| Kannada   | kn       |
| Malayalam | ml       |

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffolding & Configuration

**Intent**
Set up the project structure, dependencies, and environment configuration so all subsequent sub-tasks have a consistent foundation.

**Expected Outcomes**
- A working Python project with `requirements.txt`
- `.env.example` documenting all required secrets
- A `config.py` that loads environment variables
- Top-level folder structure in place

**Todo List**
1. Create project root with folders: `bot/`, `services/`, `utils/`, `subtitles/`, `tests/`
2. Create `requirements.txt` with: `python-telegram-bot`, `twilio`, `openai`, `yt-dlp`, `gTTS`, `srt`, `python-dotenv`, `ffmpeg-python`, `validators`, `flask`, `langdetect`, `googlesearch-python`
3. Create `.env.example` with keys: `TELEGRAM_BOT_TOKEN`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`, `OPENAI_API_KEY`
4. Create `config.py` to load and expose all env vars
5. Create a top-level `main.py` entry point (empty shell)

**Relevant Context**
- No existing codebase; greenfield project
- `python-telegram-bot` v20+ uses async handlers

**Status:** `[ ] pending`

---

### Sub-Task 2 — Language Selection, Pair Resolution & Session Management

**Intent**
Allow users to pick any **source → target** language pair from the 6 supported languages at `/start`. Store the pair in session alongside the output cache for feedback-driven regeneration. Also implement automatic source-language detection so the bot can validate or auto-correct the pair based on actual content.

**Expected Outcomes**
- `/start` presents a two-step inline keyboard:
  - Step 1: "Choose source language" — 6 buttons (English, Hindi, Telugu, Tamil, Kannada, Malayalam) + "Auto-detect"
  - Step 2: "Choose target language" — 5 remaining buttons (source language excluded)
- If user picks "Auto-detect" as source, bot detects source from each incoming message automatically
- Session stores: `source_language`, `source_language_code`, `target_language`, `target_language_code`, `last_segments`, `last_text`, `last_video_path`, `last_input_text`, `mode`, `awaiting_feedback`, `awaiting_custom_feedback`
- `get_session(chat_id)` and `update_session(chat_id, **kwargs)` exposed

**Todo List**
1. Create `utils/session.py` with in-memory dict per chat ID with all fields above; expose `get_session` and `update_session`
2. Create `utils/language_map.py`:
   - All 6 languages with display name → ISO code mapping
   - Expose `SUPPORTED_LANGUAGES` dict and `get_iso(name)` / `get_name(iso)` helpers
3. Create `utils/language_detector.py` with `detect_language(text: str) -> str`:
   - Run `langdetect` (set `DetectorFactory.seed = 0` for reproducibility)
   - If result confidence is low or script is non-Latin and ambiguous, confirm with GPT-4: "What language is this text written in? Reply with the ISO 639-1 code only."
   - Return ISO code
4. Create `utils/pair_resolver.py` with `resolve_pair(detected_source: str, session: dict) -> tuple[str, str]`:
   - Returns `(source_iso, target_iso)` confirmed pair
   - If `detected_source == session['target_language_code']`: warn user "Your input appears to be in the target language. Did you mean to swap source and target?"
   - If `detected_source == session['source_language_code']` or session has `auto_detect` source: proceed normally
   - Never block processing — just notify and proceed with detected source
5. In `bot/telegram_bot.py`, implement `/start` two-step inline keyboard (source → target)
6. In `bot/whatsapp_bot.py`, implement equivalent numbered-reply two-step flow
7. Wire `CallbackQueryHandler` to update session with chosen source and target

**Relevant Context**
- `langdetect` non-deterministic; seed fixes output
- For video inputs, language detection runs on Whisper transcript text (first 500 chars)
- Whisper itself returns a `language` field — use that as ground-truth for video source language, overriding `langdetect`
- All 6 ISO codes are valid both as source and as target

**Status:** `[ ] pending`

---

### Sub-Task 3 — Concept Simplification Service (Any-to-Any)

**Intent**
Accept a short technical question or term in **any of the 6 languages** and explain it simply in the **chosen target language**, preserving technical terms in English regardless of source or target.

**Expected Outcomes**
- `services/simplifier.py` exposes `simplify(text: str, source_lang: str, target_lang: str, mode: str = "default") -> str`
- Technical terms always appear in English in the output (in all directions)
- If target is English: terms appear as clean English words
- If target is a local language: terms appear in English inline within the target-language explanation
- `mode`: `"default"` | `"simpler"` | `"more_english"` | `"custom:<text>"`
- After response, feedback menu is shown

**Todo List**
1. Create `services/simplifier.py` with `simplify(text, source_lang, target_lang, mode)`
2. Build GPT-4 system prompt dynamically:
   - Base (all pairs): "You are an education assistant. The input is in {source_lang}. Explain the concept simply in {target_lang}."
   - **mode=default:** "Keep all technical programming terms (variable, array, loop, function, class, object, etc.) in English as-is, embedded naturally within the {target_lang} explanation."
   - **mode=simpler:** "Replace English technical terms with simple everyday {target_lang} words or phrases. Avoid English terms entirely."
   - **mode=more_english:** "Keep as many technical English terms as possible in English. Only translate the connecting/structural language into {target_lang}."
   - **mode=custom:** append user's free text as an extra instruction after the base prompt
   - Special case when `target_lang == "English"`: "Explain in clear, simple English." (no local-script formatting needed)
3. Wire Telegram `MessageHandler` and WhatsApp webhook to detect source language, call `simplify`, and reply
4. After reply, store input in `session['last_input_text']`, output in `session['last_text']`, then show feedback menu
5. Add a `/explain <text>` Telegram command alias

**Relevant Context**
- Language name strings (not ISO codes) passed to GPT-4 prompts: e.g. "Telugu", "Tamil", "Hindi"
- `detect_language` from Sub-Task 2 used to confirm source language if session has `auto_detect`

**Status:** `[ ] pending`

---

### Sub-Task 4 — Audio Extraction & Transcription Service

**Intent**
Accept a video file or URL in **any of the 6 languages**, extract audio, and transcribe it using Whisper (which natively supports all 6). Return timestamped segments and the detected source language.

**Expected Outcomes**
- `services/transcriber.py` exposes `transcribe(audio_path: str) -> dict`:
  - Returns `{"segments": [{start, end, text}], "detected_language": "<iso>"}`
  - Whisper's own `language` field is used as the authoritative source language for video
- `utils/audio_extractor.py` exposes `extract_audio(source: str) -> str`

**Todo List**
1. Create `utils/audio_extractor.py`:
   - URL → `yt-dlp` downloads full video to temp file → `ffmpeg` extracts audio to `.mp3`
   - Local file → `ffmpeg-python` extracts audio to `.mp3`
2. Create `services/transcriber.py`:
   - `openai.audio.transcriptions.create` with `model="whisper-1"` and `response_format="verbose_json"`
   - Do **not** set the `language` parameter — let Whisper auto-detect (works for all 6 languages)
   - Return `{"segments": [{start, end, text}], "detected_language": whisper_response.language}`
3. After transcription, call `pair_resolver.resolve_pair(detected_language, session)` to confirm the source/target pair
4. Handle files > 25 MB: chunk audio with `ffmpeg` before sending to Whisper
5. Clean up temp audio files after transcription

**Relevant Context**
- Whisper `verbose_json` response top-level `language` field returns ISO code
- Whisper supports all 6: en, hi, te, ta, kn, ml
- Never hardcode language in the Whisper call

**Status:** `[ ] pending`

---

### Sub-Task 5A — Translation Service (Any-to-Any, Terminology & Meaning Preservation)

**Intent**
Translate transcript segments or plain text between **any pair of the 6 languages**, applying universal terminology rules and verifying meaning via back-translation.

**Universal Terminology Rules:**
- Technical terms (variable, array, loop, function, class, etc.) are **always kept or rendered in English** regardless of source/target pair
- **Target is a local language, text output:** terms written as `targetscript (English)` — e.g. `వేరియబుల్ (variable)`, `मेथड (method)`
- **Target is a local language, video/audio:** terms spoken in English inline within target-language TTS
- **Target is English:** terms appear as clean English; no parenthetical

**Expected Outcomes**
- `services/translator.py` exposes:
  - `translate_segments(segments, source_lang, target_lang, mode) -> list[dict]` — timestamps preserved
  - `translate_text(text, source_lang, target_lang, mode) -> str` — with terminology formatting
- Both functions run `_back_translation_check` after every batch
- `mode`: `"default"` | `"simpler"` | `"more_english"` | `"custom:<text>"`

**Todo List**
1. Create `services/translator.py`
2. Implement `translate_segments(segments, source_lang, target_lang, mode)`:
   - Build prompt dynamically for any source/target pair:
   - **default:** "Translate from {source_lang} into {target_lang}. Keep all technical programming terms (variable, array, loop, function, class, object, method, string, integer, boolean, pointer, stack, queue, API, database, algorithm, and any other domain-specific English terms) in English exactly as written, embedded naturally in the {target_lang} translation. Preserve meaning fully without adding or removing information."
   - **simpler:** "Translate from {source_lang} into {target_lang}. Replace all English technical terms with simple everyday {target_lang} words. Preserve meaning."
   - **more_english:** "Translate from {source_lang} into {target_lang} grammar and sentence structure, but keep the maximum amount of English technical vocabulary in English. Preserve meaning."
   - **custom:** append user's free text as extra instruction after default prompt
   - Special case when `target_lang == "English"`: add "Output clean English; do not add any parenthetical annotations."
   - Return list of translated segments with original `start`/`end` timestamps
3. Implement `translate_text(text, source_lang, target_lang, mode)`:
   - Same prompt logic as above
   - If `target_lang != "English"`: additionally instruct: "For each technical English term embedded in the translation, also write it in {target_lang} script immediately before it in parentheses — format: `targetscript (English)`. Example for Telugu: `లూప్ (loop)`"
   - If `target_lang == "English"`: no parenthetical instruction; clean English output only
4. Implement `_back_translation_check(original, translated, source_lang, target_lang) -> bool`:
   - Translate `translated` back to `source_lang` using GPT-4
   - Ask GPT-4: "Do these two texts convey exactly the same meaning? Answer YES or NO only." — comparing original vs back-translated
   - If NO: retry once, adding: "The previous translation changed the meaning. Translate again more carefully, preserving all information."
   - Return True (passed) or False after retry (log warning, still return translated result)
5. Call `_back_translation_check` on every translation batch before returning

**Relevant Context**
- Technical term seed list: variable, array, loop, function, class, object, method, string, integer, boolean, pointer, stack, queue, API, database, algorithm — prompt also instructs GPT-4 to detect and preserve any other domain-specific English terms
- For non-English↔non-English pairs (e.g. Telugu→Tamil): GPT-4 translates directly without English as a pivot; this is well within GPT-4's capability
- Back-translation for a local↔local pair (e.g. Telugu→Tamil): back-translate Tamil output → Telugu, compare with original Telugu

**Status:** `[ ] pending`

---

### Sub-Task 5B — Timestamp-Aligned TTS Audio Synthesis & Video Dubbing (Any Target Language)

**Intent**
Synthesise translated segment text into speech in **any target language** (all 6 supported by gTTS) and place each clip **exactly within its original timestamp window**. Mux the resulting aligned audio track back into the original video.

**Expected Outcomes**
- `services/tts.py` exposes `synthesise_aligned(segments: list[dict], target_language_code: str) -> str`:
  - Accepts any of the 6 ISO codes as `target_language_code`
  - Per segment: TTS → measure duration → fit into `[start, end]` window via silence padding or `atempo`
  - All windowed clips concatenated into one `.mp3` matching original video duration
- `services/video_dubber.py` exposes `dub_video(video_path, aligned_audio_path) -> str`
- Bot sends dubbed video back

**Todo List**
1. Create `services/tts.py` with `synthesise_aligned(segments, target_language_code)`:
   - Call `gTTS(text=segment['text'], lang=target_language_code)` — works for en, hi, te, ta, kn, ml
   - Measure each clip duration via `ffprobe -v error -show_entries format=duration`
   - Compute `window = segment['end'] - segment['start']`
   - Compute `gap = segment['start'] - prev_segment['end']` (for first segment: `gap = segment['start']`)
   - If `clip_duration <= window`: generate `gap`-sec silence + TTS clip + `(window - clip_duration)`-sec trailing silence
   - If `clip_duration > window`: compute `speed = clip_duration / window` (cap at 2.0), apply `atempo`, prepend `gap`-sec silence
   - Concatenate all windowed clips in order into one final aligned `.mp3`
2. Create `services/video_dubber.py` with `dub_video(video_path, aligned_audio_path)`:
   - `ffmpeg -i video.mp4 -i aligned.mp3 -c:v copy -map 0:v:0 -map 1:a:0 -shortest dubbed.mp4`
   - Return dubbed `.mp4` path
3. Store dubbed video path in session for feedback re-dub without re-downloading
4. Clean up all temp files after user confirms satisfied

**Relevant Context**
- `gTTS` ISO codes for all 6: `en`, `hi`, `te`, `ta`, `kn`, `ml`
- `ffmpeg` silence: `ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t {dur} silence.mp3`
- `atempo` range 0.5–2.0; chain for ratio > 2.0: `atempo=2.0,atempo=x`
- `ffprobe` duration: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 clip.mp3`
- Telegram `send_video` limit 50 MB; use `send_document` for larger

**Status:** `[ ] pending`

---

### Sub-Task 5C — Transcript-Only Output (Any-to-Any)

**Intent**
When the user provides only a text transcript (no video), detect its language, confirm the source/target pair, translate it, and return a `.txt` file — applying the universal terminology formatting rule for the resolved target language.

**Expected Outcomes**
- Any-to-any pair supported: e.g. Telugu `.txt` → Tamil output; Hindi `.txt` → English output; English `.txt` → Kannada output
- **Target is local language:** `targetscript (English)` format for technical terms
- **Target is English:** clean English only
- After sending `.txt`, feedback menu is shown

**Todo List**
1. In `utils/input_classifier.py`, distinguish:
   - Short text < 300 chars, no newlines → concept question → simplifier
   - Long text or `.txt` file upload → transcript → `translate_text`
   - Video file or URL → video pipeline
2. For transcript inputs: call `detect_language` on first 500 chars, then `resolve_pair(detected_source, session)` to confirm pair
3. In `bot/telegram_bot.py`, handle `.txt` uploads: read content → `translate_text(text, source_lang, target_lang, mode)` → return translated `.txt`
4. For WhatsApp: treat long text messages as transcript
5. Reply: "Here is your translated transcript from {source_language} to {target_language}." + attach `.txt`
6. Show feedback menu after sending

**Relevant Context**
- `document.mime_type == "text/plain"` for Telegram `.txt` detection
- Classification heuristic: length > 300 chars OR newlines > 3 → transcript

**Status:** `[ ] pending`

---

### Sub-Task 6 — Bot Command & Message Routing (Any-to-Any)

**Intent**
Wire all services under a unified routing layer. Every incoming message is routed correctly by detecting source language, confirming against session pair, and calling the appropriate pipeline — for any of the 30 valid language pairs.

**Expected Outcomes**
- Telegram commands: `/start`, `/explain <text>`, `/setlang` (shortcut to re-open language pair selector)
- Video/URL → dub pipeline (any source → any target) → send dubbed video → feedback menu
- `.txt`/long text → translate (any pair) → send `.txt` → feedback menu
- Short question → simplify (any pair) → reply → feedback menu
- Feedback → regenerate with same source/target pair, new mode → feedback menu again
- All responses respect session source/target pair

**Todo List**
1. In `bot/telegram_bot.py`, register all handlers: `CommandHandler` (start, explain, setlang), `MessageHandler` (text, video, document), `CallbackQueryHandler`
2. Implement `handle_video(update, context)`:
   - `extract_audio → transcribe` (returns `detected_language`)
   - `resolve_pair(detected_language, session)` → confirms `(source_iso, target_iso)`
   - `translate_segments(...) → synthesise_aligned(target_iso) → dub_video → send_video → show_feedback_menu`
3. Implement `handle_url`: detect URL → download full video → same as `handle_video`
4. Implement `handle_document`: `.txt` → detect language → `translate_text → send .txt → show_feedback_menu`; video MIME → `handle_video`
5. Implement `handle_text`: detect language → `resolve_pair` → route to `simplify` or `translate_text`
6. Implement `handle_feedback`: read choice from session → regenerate with new `mode`, same source/target pair → send output → show feedback menu
7. Implement `/setlang` command: re-presents the two-step language pair selector without resetting other session data
8. In `bot/whatsapp_bot.py` (Flask webhook), mirror all routing
9. Add user-facing error messages for: same source/target language, unsupported file type, failed download

**Relevant Context**
- `awaiting_feedback` session flag prevents routing feedback replies as new inputs
- URL detection: `validators` library
- Telegram video MIME: `video/mp4`, `video/x-matroska`
- Twilio media: `MediaUrl0` in webhook payload
- `/setlang` is important for any-to-any — users will frequently want to switch pairs

**Status:** `[ ] pending`

---

### Sub-Task 7 — Post-Output Feedback Loop (Any-to-Any, Direction-Aware Labels)

**Intent**
After every output, show a feedback menu with labels that adapt to the current source/target pair, then regenerate using the same pair with the new mode instruction.

**Feedback label logic:**
- Button 2 ("Simpler"): "🔄 Simpler — use {target_language} words instead of English terms"
- Button 3 ("More English"): "📘 More English technical terms"
- These labels are always meaningful regardless of which pair is active

**Expected Outcomes**
- Feedback menu shown after every output; labels dynamically reference `target_language` name
- Free-text feedback appended as extra instruction to GPT-4 prompt on regeneration
- Loop repeats until Satisfied
- Video regeneration skips re-transcription and re-download (uses `session['last_segments']` + `session['last_video_path']`)
- Transcript regeneration uses `session['last_text']`
- Simplification regeneration uses `session['last_input_text']`

**Todo List**
1. Create `utils/feedback_menu.py` with `send_feedback_menu(chat_id, context, source_lang, target_lang)`:
   - Button 1: "✅ Satisfied"
   - Button 2: `f"🔄 Simpler — use {target_lang} words instead of English terms"`
   - Button 3: "📘 More English technical terms"
   - Button 4: "✏️ Share your feedback"
   - Telegram: `InlineKeyboardMarkup` with `callback_data`: `"satisfied"` | `"simpler"` | `"more_english"` | `"custom"`
   - WhatsApp: numbered list "Reply 1/2/3/4"
2. Register `CallbackQueryHandler` for feedback buttons in `bot/telegram_bot.py`
3. Implement `handle_feedback_callback(update, context)`:
   - `"satisfied"` → clear session output cache, send "Great! Let me know if you need anything else."
   - `"simpler"` / `"more_english"` → set `session['mode']`, call regeneration function with same source/target pair, send output, show feedback menu
   - `"custom"` → set `session['awaiting_custom_feedback'] = True`, prompt "Please type your feedback"
4. Implement `handle_custom_feedback_text(update, context)`:
   - When `awaiting_custom_feedback` is True: read text, set `session['mode'] = f"custom:{user_text}"`, regenerate, send output, show menu again, clear flag
5. Mirror in `bot/whatsapp_bot.py` via numbered reply parsing

**Relevant Context**
- `mode` values: `"default"`, `"simpler"`, `"more_english"`, `"custom:<free_text>"`
- Session must retain `source_language_code` and `target_language_code` throughout feedback loop

**Status:** `[ ] pending`

---

### Sub-Task 8 — Summary Service with Reference Links

**Intent**
When the user explicitly requests a summary (via `/summarise` command, or by replying "summarise" / "summary" after any output), generate a concise, well-structured digest of the topic/content in the user's **target language**, then fetch and attach 2–3 relevant YouTube video links and article/website links for further reading.

**Expected Outcomes**
- `services/summariser.py` exposes `summarise(content: str, source_lang: str, target_lang: str, mode: str = "default") -> dict`:
  - Returns `{"summary_text": "...", "links": [{"title": "...", "url": "...", "type": "video|article"}]}`
- Summary is always in **target language**; technical terms follow the same terminology rules as translations
- Summary format (GPT-4 generated):
  - **3–5 bullet points** covering the key ideas
  - **1 compact table** if the topic has comparable items (e.g. list vs array, for loop vs while loop)
  - **1 short "In plain words" sentence** at the top (max 1 line)
- Reference links: 2–3 links returned — at least 1 YouTube video and at least 1 article/website
- After the summary is sent, the feedback menu is shown (same 4-option loop)

**Todo List**
1. Create `services/summariser.py` with `summarise(content, source_lang, target_lang, mode)`:
   - Build GPT-4 prompt:
     - "You are a study assistant. Given the following content, produce a short summary in {target_lang}."
     - "Format: 1 plain-words sentence, then 3–5 bullet points of key ideas, then a compact comparison table if relevant (max 3 rows). Keep it brief and simple."
     - "Keep all technical English terms in English (with {target_lang} script transliteration before them in parentheses if target is not English). Preserve meaning."
     - Append mode instruction if mode is not default (same simpler/more_english/custom logic as translator)
   - Call GPT-4 and extract `summary_text`
2. Create `services/link_fetcher.py` with `fetch_links(topic: str, num_links: int = 3) -> list[dict]`:
   - Extract the topic keyword(s) from the content using a short GPT-4 call: "What is the main technical topic of this text? Reply with 2–4 keywords only."
   - Use `googlesearch-python` to search: `"{topic} tutorial site:youtube.com"` → pick top 1–2 YouTube results
   - Use `googlesearch-python` to search: `"{topic} explained tutorial"` → pick top 1–2 article results (filter out YouTube URLs)
   - Return list of `{"title": "...", "url": "...", "type": "video"|"article"}`
   - Cap at 3 links total: prefer 1–2 videos + 1–2 articles
3. In `bot/telegram_bot.py`:
   - Register `/summarise` `CommandHandler`
   - Register `MessageHandler` for messages matching "summarise" or "summary" (case-insensitive) when `session['awaiting_feedback']` is True or immediately after any output
   - `handle_summarise(update, context)`: read `session['last_input_text']` or `session['last_text']` as content, call `summarise` + `fetch_links`, format and send the response, then show feedback menu
4. Format the Telegram response:
   - Send summary text as a message (markdown: bold headers, bullet points via `-`)
   - Append a "📚 References:" section listing each link as `[title](url)` on a new line, with an emoji prefix: 🎬 for video, 📄 for article
5. In `bot/whatsapp_bot.py`, send the summary as plain text with links on separate lines (WhatsApp does not render markdown)
6. Store the summary in `session['last_summary']` for potential feedback-driven regeneration

**Relevant Context**
- `googlesearch-python` usage: `from googlesearch import search; results = list(search(query, num_results=5))`
- YouTube links contain `youtube.com/watch` or `youtu.be` — use this to classify `type`
- Topic extraction via GPT-4 should be a minimal call (low token cost): just ask for keywords
- Summary is triggered only on explicit request (`/summarise` or keyword) — not automatically after every output
- The feedback loop applies to summaries too: user can ask for simpler summary, more English terms, or custom instruction
- `session['last_input_text']` is used as the content source for concept simplifications; `session['last_text']` for transcript outputs; if both empty, prompt user to first send a concept or transcript

**Status:** `[ ] pending`

---

### Sub-Task 9 — Testing & Validation

**Intent**
Verify every service across multiple language pairs and validate end-to-end flows, terminology rules, and the feedback loop.

**Expected Outcomes**
- Unit tests covering all services, both local↔local and local↔English pairs
- Integration tests for video and transcript pipelines across representative pairs
- Feedback loop tested for at least 2 pairs
- All tests pass with `pytest`

**Todo List**
1. `tests/test_language_detector.py` — assert each of the 6 languages detected correctly from sample text
2. `tests/test_pair_resolver.py`:
   - en→te pair: source detected as en → resolves correctly
   - te→ta pair: source detected as te → resolves correctly
   - ta→ta (same language): → warning message returned
   - auto-detect mode: source detected dynamically per message
3. `tests/test_simplifier.py` — test all 4 modes for 3 representative pairs (en→te, hi→en, te→ta); assert English terms preserved/absent per mode; assert correct output language
4. `tests/test_translator.py`:
   - `translate_segments` for en→te, te→ta, hi→en — assert timestamps preserved, terminology rules applied
   - `translate_text` for en→te — assert `targetscript (English)` format
   - `translate_text` for te→en — assert clean English, no parentheticals
   - `translate_text` for te→ta — assert `targetscript (English)` format in Tamil output
5. `tests/test_back_translation.py` — mock GPT-4 diverging translation; assert retry triggered for en→te and te→ta pairs
6. `tests/test_tts.py` — mock gTTS for all 6 ISO codes; assert windowed clip duration matches segment window
7. `tests/test_video_dubber.py` — mock ffmpeg; assert output path returned
8. `tests/test_input_classifier.py` — short text → concept, long text → transcript, video → video
9. `tests/test_session.py` — assert all session fields including `source_language_code` and `target_language_code` round-trip
10. `tests/test_feedback_menu.py` — assert button 2 label contains `target_lang` name; assert mode set correctly per option; assert custom text appended
11. `tests/test_summariser.py`:
    - Mock GPT-4; assert summary contains bullet points and is in target language
    - Assert table is present when topic has comparable items
    - Assert mode instructions applied (simpler → fewer English terms in summary)
12. `tests/test_link_fetcher.py` — mock `googlesearch`; assert at least 1 video link and 1 article link returned; assert YouTube URLs classified as `"video"`
13. `tests/test_integration_en_to_te.py` — English `.mp4` → Telugu dubbed `.mp4`
14. `tests/test_integration_te_to_en.py` — Telugu `.mp4` → English dubbed `.mp4`
15. `tests/test_integration_te_to_ta.py` — Telugu `.mp4` → Tamil dubbed `.mp4` (local→local)
16. `tests/test_integration_transcript_en_to_hi.py` — English `.txt` → Hindi `.txt` with `targetscript (English)` format
17. `tests/test_integration_transcript_te_to_en.py` — Telugu `.txt` → clean English `.txt`
18. `tests/test_integration_transcript_hi_to_ta.py` — Hindi `.txt` → Tamil `.txt` (local→local)
19. `tests/test_integration_summarise.py` — send a concept, then `/summarise`; assert summary message + 3 links returned in target language

**Status:** `[x] done`

---

## Architecture Overview

```
User (Telegram / WhatsApp)
        |
   /start → two-step language pair selector
   source language (6 options + auto) → target language (5 options)
   stored in session as source_language_code + target_language_code
        |
   Bot Layer
   telegram_bot.py | whatsapp_bot.py
        |
   language_detector.py + pair_resolver.py
   detects source lang per message/video
   confirms or warns about pair mismatch
        |
   input_classifier.py
   /           |              \              \
Concept    Transcript      Video / URL    /summarise or
Question   Text or .txt    File or URL    "summarise" keyword
   |             |               |                |
simplifier  translator      audio_extractor   summariser.py
.py         .py             .py               + link_fetcher.py
any pair    translate_text       |            GPT-4 summary
mode param  any pair         transcriber.py   googlesearch links
GPT-4       mode param       Whisper           bullets + table
   |        back-translation auto-detect       target language
   |        check GPT-4           |                  |
   |        terminology      pair_resolver    Summary + 2-3 links
   |        rules                 |           🎬 YouTube  📄 Article
   |        targetscript     translator.py    sent to user
   |        or clean English  translate_segs       |
   |               |          any pair + mode       |
   |        .txt sent to user back-translation      |
   |                               |                |
   |                            tts.py              |
   |                        synthesise_aligned       |
   |                        any target ISO code      |
   |                        gTTS all 6 langs         |
   |                               |                |
   |                        video_dubber.py          |
   |                           ffmpeg mux            |
   |                               |                |
   |                    Dubbed .mp4 sent to user     |
   |                                                |
   +----------------+-------------------------------+
                    |
           feedback_menu.py
           dynamic labels with target_lang name
           1.Satisfied  2.Simpler  3.More English  4.Free text
                    |
           handle_feedback + set mode in session
           same source/target pair
                    |
           Regenerate (skip re-transcription for video)
                    |
           Send new output + feedback menu again
```

---

## Non-Goals
- No user authentication or payment gating
- No persistent database (sessions are in-memory; lost on restart)
- No real-time lip-sync dubbing (timing approximated via silence padding and atempo)
- No subtitle burn-in to video (subtitles used internally only)
- No mobile app — bot interface only
- Feedback loop does not re-download or re-transcribe; only re-translates/re-generates
- No more than 2 languages selected at once (source + target); no multi-target broadcast
- Summary links are fetched via web search and are best-effort — link quality is not guaranteed
- No image generation; diagram descriptions are text-only (described in words, not rendered images)
