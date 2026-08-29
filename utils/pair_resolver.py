"""
utils/pair_resolver.py — Resolve and validate the (source, target) language
pair for a single processing turn.

Rules (from the plan):
- If the detected source equals the session target: warn, but still proceed
  using the detected source so processing is never blocked.
- If the detected source equals the session source, or the session has
  ``auto_detect`` as source: proceed normally.
- Always return ``(source_iso, target_iso)`` — never raises.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_pair(detected_source: str, session: dict) -> tuple[str, str]:
    """
    Return the ``(source_iso, target_iso)`` pair to use for this turn.

    Parameters
    ----------
    detected_source:
        ISO 639-1 code produced by ``detect_language()`` (or the Whisper
        ``language`` field for video input).
    session:
        The caller's session dict as returned by ``get_session()``.

    Returns
    -------
    tuple[str, str]
        ``(source_iso, target_iso)`` — guaranteed to be non-empty strings
        drawn from the resolved values.
    """
    session_source: str | None = session.get("source_language_code")
    session_target: str | None = session.get("target_language_code")

    # If target is not yet set, we cannot meaningfully route — use detected
    # source as-is and leave target as-is (caller must handle None target).
    target_iso: str = session_target or detected_source

    auto_detect: bool = session_source == "auto" or session_source is None

    if not auto_detect and detected_source == session_target:
        # Detected language is the same as what the user wants *output* in.
        # Warn, but honour the detection and proceed.
        logger.warning(
            "Detected source language '%s' matches the session target language. "
            "Input may already be in the target language. "
            "Tip: swap source and target if you intended to translate the other way.",
            detected_source,
        )
        source_iso = detected_source
    elif auto_detect:
        # Auto-detect mode — use whatever was detected.
        source_iso = detected_source
    else:
        # Session has an explicit source language.
        if detected_source != session_source:
            logger.info(
                "Detected source language '%s' differs from session source '%s'. "
                "Using detected language.",
                detected_source,
                session_source,
            )
        source_iso = detected_source

    return source_iso, target_iso
