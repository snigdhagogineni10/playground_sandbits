"""
utils/language_detector.py — Fast language detection using ``langdetect``,
with a GPT-4 confirmation fallback for low-confidence or ambiguous results.
"""

from __future__ import annotations

import logging

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException
from openai import OpenAI

import config
from utils.language_map import SUPPORTED_LANGUAGES

# ── reproducibility ───────────────────────────────────────────────────────────
DetectorFactory.seed = 0

_SUPPORTED_ISOS: frozenset[str] = frozenset(SUPPORTED_LANGUAGES.values())
_CONFIDENCE_THRESHOLD: float = 0.80

logger = logging.getLogger(__name__)
_openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


def _confirm_with_gpt4(text: str) -> str | None:
    """Ask GPT-4 for the ISO 639-1 code of *text*. Returns the code or None."""
    try:
        response = _openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a language identification assistant. "
                        "Reply with the ISO 639-1 language code only — "
                        "two lowercase letters, nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"What language is this text written in?\n\n{text[:500]}"
                    ),
                },
            ],
            max_tokens=5,
            temperature=0,
        )
        code = response.choices[0].message.content.strip().lower()
        return code if len(code) == 2 else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("GPT-4 language confirmation failed: %s", exc)
        return None


def detect_language(text: str) -> str:
    """
    Detect the language of *text* and return an ISO 639-1 code.

    Strategy:
    1. Run ``langdetect`` (seeded for determinism).
    2. If the top result has confidence >= ``_CONFIDENCE_THRESHOLD`` and its
       code is among the six supported languages, return it immediately.
    3. Otherwise, confirm with a GPT-4 call and return that result.
    4. If GPT-4 also fails, fall back to the raw ``langdetect`` best guess.
    """
    try:
        results = detect_langs(text)
    except LangDetectException as exc:
        logger.warning("langdetect failed (%s); falling back to GPT-4.", exc)
        return _confirm_with_gpt4(text) or "en"

    top = results[0]  # highest-probability result
    iso = top.lang
    confidence = top.prob

    # High-confidence hit for a supported language — done.
    if confidence >= _CONFIDENCE_THRESHOLD and iso in _SUPPORTED_ISOS:
        return iso

    # Low confidence or unsupported / ambiguous code — confirm with GPT-4.
    logger.debug(
        "langdetect low confidence (%.2f, %s); confirming with GPT-4.",
        confidence,
        iso,
    )
    gpt_code = _confirm_with_gpt4(text)
    if gpt_code:
        return gpt_code

    # Last resort: use whatever langdetect returned.
    return iso
