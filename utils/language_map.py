"""
utils/language_map.py — Canonical language ↔ ISO-639-1 mapping for the six
languages supported by the Multilingual Education Bot.
"""

from __future__ import annotations

# ── canonical mapping ─────────────────────────────────────────────────────────
# Keys are exact display names used in bot menus and session storage.
SUPPORTED_LANGUAGES: dict[str, str] = {
    "English":   "en",
    "Hindi":     "hi",
    "Telugu":    "te",
    "Tamil":     "ta",
    "Kannada":   "kn",
    "Malayalam": "ml",
}

# Reverse lookup: ISO code → display name
_ISO_TO_NAME: dict[str, str] = {v: k for k, v in SUPPORTED_LANGUAGES.items()}


def get_iso(name: str) -> str | None:
    """Return the ISO 639-1 code for a display *name*, or ``None`` if unknown."""
    return SUPPORTED_LANGUAGES.get(name)


def get_name(iso: str) -> str | None:
    """Return the display name for an ISO 639-1 *code*, or ``None`` if unknown."""
    return _ISO_TO_NAME.get(iso.lower() if iso else iso)
