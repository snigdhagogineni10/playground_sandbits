"""
bot/whatsapp_bot.py — WhatsApp bot via Green API + Flask.

Language-selection flow (numbered replies)
──────────────────────────────────────────
/start  (or the word "start")
  → Bot sends Step 1 menu listing all 6 languages + "0. Auto-detect"
  → User replies with a number (0–6)
  → Bot sends Step 2 menu listing the remaining 5 languages
  → User replies with a number (1–5)
  → Session updated, confirmation sent.

All subsequent routing is handled by Sub-Task 6.
"""

from __future__ import annotations

import logging
import sys
import os

# Make sure Python can find utils/, services/, config.py from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

from flask import Flask, Response, request

from config import GREEN_API_INSTANCE_ID, GREEN_API_TOKEN
from utils.language_map import SUPPORTED_LANGUAGES, get_name
from utils.session import get_session, update_session

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── Green API helper ──────────────────────────────────────────────────────────

GREEN_API_URL = "https://api.green-api.com"


def send_message(chat_id: str, message: str) -> None:
    """Send a WhatsApp message via Green API."""
    url = f"{GREEN_API_URL}/waInstance{GREEN_API_INSTANCE_ID}/sendMessage/{GREEN_API_TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": message,
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error("Failed to send message via Green API: %s", e)


# ── language menu helpers ─────────────────────────────────────────────────────
_ORDERED_LANGUAGES: list[tuple[str, str]] = list(SUPPORTED_LANGUAGES.items())
# [(display_name, iso), …]  — stable order, index 1-based in menus


def _step1_menu() -> str:
    lines = ["*Step 1 of 2* — Choose your *source language*:\n"]
    for i, (name, _) in enumerate(_ORDERED_LANGUAGES, start=1):
        lines.append(f"{i}. {name}")
    lines.append("0. Auto-detect")
    lines.append("\nReply with the number of your choice.")
    return "\n".join(lines)


def _step2_menu(excluded_iso: str) -> str:
    lines = ["*Step 2 of 2* — Choose your *target language*:\n"]
    idx = 1
    for name, iso in _ORDERED_LANGUAGES:
        if iso == excluded_iso:
            continue
        lines.append(f"{idx}. {name}")
        idx += 1
    lines.append("\nReply with the number of your choice.")
    return "\n".join(lines)


def _target_choices(excluded_iso: str) -> list[tuple[str, str]]:
    """Return ordered (name, iso) pairs with the source language excluded."""
    return [(n, i) for n, i in _ORDERED_LANGUAGES if i != excluded_iso]


# ── webhook ───────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health() -> Response:
    """Health check endpoint so Render knows the service is alive."""
    return Response("OK", status=200)


@app.route("/webhook", methods=["POST"])
def webhook() -> Response:
    """Receive inbound Green API WhatsApp messages and dispatch them."""
    data = request.get_json(force=True, silent=True) or {}

    # Green API sends a nested structure
    sender_data = data.get("senderData", {})
    message_data = data.get("messageData", {})

    chat_id: str = sender_data.get("chatId", "")
    body: str = (
        message_data.get("textMessageData", {}).get("textMessage", "")
        or message_data.get("extendedTextMessageData", {}).get("text", "")
    ).strip()

    if not chat_id or not body:
        return Response("ok", status=200)

    session = get_session(chat_id)
    reply_text = _dispatch(chat_id, session, body)
    send_message(chat_id, reply_text)

    return Response("ok", status=200)


def _dispatch(chat_id: str, session: dict, body: str) -> str:
    """Route an inbound message to the correct handler; return reply text."""
    step: str | None = session.get("_step")
    normalized = body.lower().strip()

    # ── trigger: "start" keyword resets the wizard ───────────────────────────
    if normalized in ("start", "/start"):
        update_session(chat_id, _step="choose_source")
        return _step1_menu()

    # ── step 1: awaiting source language choice ───────────────────────────────
    if step == "choose_source":
        return _handle_source_choice(chat_id, body)

    # ── step 2: awaiting target language choice ───────────────────────────────
    if step == "choose_target":
        return _handle_target_choice(chat_id, session, body)

    # ── no active wizard — prompt setup ──────────────────────────────────────
    if not session.get("target_language_code"):
        update_session(chat_id, _step="choose_source")
        return (
            "Welcome to the Multilingual Education Bot!\n\n"
            + _step1_menu()
        )

    # ── language pair already set — hand off to message router (Sub-Task 6) ──
    return _placeholder_router(session, body)


def _handle_source_choice(chat_id: str, body: str) -> str:
    """Parse the user's Step-1 reply and advance to Step 2."""
    body = body.strip()

    # Accept "0" for auto-detect
    if body == "0":
        update_session(
            chat_id,
            source_language="Auto-detect",
            source_language_code="auto",
            _step="choose_target",
        )
        return (
            "Source: Auto-detect\n\n"
            + _step2_menu("")
        )

    try:
        idx = int(body)
        if 1 <= idx <= len(_ORDERED_LANGUAGES):
            name, iso = _ORDERED_LANGUAGES[idx - 1]
            update_session(
                chat_id,
                source_language=name,
                source_language_code=iso,
                _step="choose_target",
            )
            return (
                f"Source: {name}\n\n"
                + _step2_menu(iso)
            )
    except ValueError:
        pass

    return (
        "Please reply with a number from the list.\n\n"
        + _step1_menu()
    )


def _handle_target_choice(chat_id: str, session: dict, body: str) -> str:
    """Parse the user's Step-2 reply and finalise the language pair."""
    src_iso: str = session.get("source_language_code") or ""
    src_label: str = session.get("source_language") or "Auto-detect"
    choices = _target_choices(src_iso)

    try:
        idx = int(body.strip())
        if 1 <= idx <= len(choices):
            tgt_name, tgt_iso = choices[idx - 1]
            update_session(
                chat_id,
                target_language=tgt_name,
                target_language_code=tgt_iso,
                _step=None,
            )
            return (
                f"Language pair set!\n\n"
                f"  Source: {src_label}\n"
                f"  Target: {tgt_name}\n\n"
                "You can now send me text to translate. "
                'Reply "start" at any time to change the language pair.'
            )
    except ValueError:
        pass

    return (
        "Please reply with a number from the list.\n\n"
        + _step2_menu(src_iso)
    )


def _placeholder_router(session: dict, body: str) -> str:
    """Stub — full message routing implemented in Sub-Task 6."""
    src = session.get("source_language", "?")
    tgt = session.get("target_language", "?")
    return (
        f"[Router not yet implemented]\n"
        f"Pair: {src} to {tgt}\n"
        f'Message received: "{body}"'
    )


# ── entry-point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
