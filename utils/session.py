"""
utils/session.py — In-memory session store keyed by chat_id.

Each session carries all state needed across bot turns:
  source/target language choice, output cache for feedback-driven
  regeneration, and mode/feedback flags.
"""

from __future__ import annotations

from typing import Any

# ── in-memory store ──────────────────────────────────────────────────────────
_sessions: dict[str, dict[str, Any]] = {}

_DEFAULTS: dict[str, Any] = {
    "source_language": None,          # display name, e.g. "Hindi"
    "source_language_code": None,     # ISO 639-1, e.g. "hi"  (or "auto")
    "target_language": None,          # display name, e.g. "Telugu"
    "target_language_code": None,     # ISO 639-1, e.g. "te"
    "last_segments": None,            # list of timed transcript segments
    "last_text": None,                # last translated/output text
    "last_video_path": None,          # path to last processed video file
    "last_input_text": None,          # raw input text from the user
    "last_summary": None,             # last generated summary string
    "mode": None,                     # "video" | "text" | "concept"
    "awaiting_feedback": False,       # True after every output delivery
    "awaiting_custom_feedback": False,# True after user picks ✏️ free-text
    # internal — language selection wizard state
    "_step": None,                    # "choose_source" | "choose_target"
}


def get_session(chat_id: str | int) -> dict[str, Any]:
    """Return the session for *chat_id*, creating it with defaults if absent."""
    key = str(chat_id)
    if key not in _sessions:
        _sessions[key] = dict(_DEFAULTS)
    return _sessions[key]


def update_session(chat_id: str | int, **kwargs: Any) -> None:
    """Merge *kwargs* into the session for *chat_id*."""
    session = get_session(chat_id)
    session.update(kwargs)
