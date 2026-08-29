"""
Translation service (any-to-any across 6 languages).

Rules:
- Technical English terms are always kept or rendered in English.
- For text output (non-English target): terms formatted as targetscript (English).
- For video/audio output (segments): terms stay as English words in translated text.
- Every translation batch is verified via a back-translation meaning check.
- mode: "default" | "simpler" | "more_english" | "custom:<instruction>"
"""

import logging
import openai
import config

openai.api_key = config.OPENAI_API_KEY
logger = logging.getLogger(__name__)

_TECH_TERMS = (
    "variable, array, loop, function, class, object, method, string, integer, "
    "boolean, pointer, stack, queue, API, database, algorithm, list, tuple, "
    "dictionary, set, index, iterator, recursion, inheritance, polymorphism, "
    "encapsulation, compiler, interpreter, runtime, exception, null"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate_segments(
    segments: list[dict],
    source_lang: str,
    target_lang: str,
    mode: str = "default",
) -> list[dict]:
    """
    Translate a list of {start, end, text} segments.
    Timestamps are preserved unchanged.

    Args:
        segments:    List of {"start": float, "end": float, "text": str}.
        source_lang: Full language name, e.g. "Telugu".
        target_lang: Full language name, e.g. "Tamil".
        mode:        Translation mode.

    Returns:
        List of {"start": float, "end": float, "text": str} with translated text.
    """
    if not segments:
        return segments

    texts = [seg["text"] for seg in segments]
    translated_texts = _translate_batch(
        texts, source_lang, target_lang, mode, is_text_output=False
    )

    result = []
    for seg, translated in zip(segments, translated_texts):
        result.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": translated,
        })
    return result


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    mode: str = "default",
) -> str:
    """
    Translate a plain text string.
    For non-English targets, technical terms are formatted as targetscript (English).

    Args:
        text:        Input text to translate.
        source_lang: Full source language name.
        target_lang: Full target language name.
        mode:        Translation mode.

    Returns:
        Translated string.
    """
    results = _translate_batch(
        [text], source_lang, target_lang, mode, is_text_output=True
    )
    return results[0]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_prompt(
    source_lang: str,
    target_lang: str,
    mode: str,
    is_text_output: bool,
) -> str:
    """Build the GPT-4 system prompt for translation."""
    base = (
        f"Translate from {source_lang} into {target_lang}. "
        f"Preserve the original meaning fully without adding or removing information. "
    )

    if mode == "default":
        style = (
            f"Keep all technical programming terms ({_TECH_TERMS}, and any other "
            f"domain-specific English terms you detect) in English exactly as written, "
            f"embedded naturally in the {target_lang} translation."
        )
    elif mode == "simpler":
        style = (
            f"Replace all English technical terms with simple everyday {target_lang} "
            f"words. Preserve meaning."
        )
    elif mode == "more_english":
        style = (
            f"Translate into {target_lang} grammar and sentence structure, but keep "
            f"the maximum amount of English technical vocabulary in English. "
            f"Preserve meaning."
        )
    elif mode.startswith("custom:"):
        custom = mode[len("custom:"):]
        style = (
            f"Keep all technical programming terms ({_TECH_TERMS}) in English as "
            f"written. Additionally: {custom}"
        )
    else:
        style = (
            f"Keep all technical programming terms ({_TECH_TERMS}) in English exactly "
            f"as written, embedded naturally in the {target_lang} translation."
        )

    prompt = base + style

    if target_lang.lower() == "english":
        prompt += " Output clean English; do not add any parenthetical annotations."
    elif is_text_output and mode != "simpler":
        prompt += (
            f" For each technical English term embedded in the translation, also write "
            f"it in {target_lang} script immediately before it in parentheses — "
            f"format: targetscript (English). Example for Telugu: లూప్ (loop)."
        )

    return prompt


def _translate_batch(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    mode: str,
    is_text_output: bool,
) -> list[str]:
    """
    Translate a list of strings in one GPT-4 call (numbered for alignment).
    Runs a back-translation check and retries once if meaning diverges.
    """
    if not texts:
        return texts

    system_prompt = _build_prompt(source_lang, target_lang, mode, is_text_output)
    numbered_input = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))

    translated_raw = _call_gpt4(system_prompt, numbered_input)
    translated_texts = _parse_numbered(translated_raw, len(texts))

    # Back-translation check
    passed = _back_translation_check(
        original=numbered_input,
        translated="\n".join(f"{i+1}. {t}" for i, t in enumerate(translated_texts)),
        source_lang=source_lang,
        target_lang=target_lang,
    )

    if not passed:
        logger.warning(
            "Back-translation check failed for %s→%s. Retrying once.", source_lang, target_lang
        )
        retry_prompt = system_prompt + (
            " The previous translation changed the meaning. "
            "Translate again more carefully, preserving all information exactly."
        )
        translated_raw = _call_gpt4(retry_prompt, numbered_input)
        translated_texts = _parse_numbered(translated_raw, len(texts))

    return translated_texts


def _back_translation_check(
    original: str,
    translated: str,
    source_lang: str,
    target_lang: str,
) -> bool:
    """
    Translate `translated` back to source_lang and ask GPT-4 if meanings match.
    Returns True if meanings match, False otherwise.
    """
    back_prompt = (
        f"Translate the following text from {target_lang} back into {source_lang}. "
        f"Translate faithfully without adding or removing anything."
    )
    back_translated = _call_gpt4(back_prompt, translated)

    check_prompt = (
        "Do these two texts convey exactly the same meaning? "
        "Answer YES or NO only."
    )
    comparison = f"Text 1:\n{original}\n\nText 2:\n{back_translated}"
    verdict = _call_gpt4(check_prompt, comparison, max_tokens=5, temperature=0.0)
    return verdict.strip().upper().startswith("YES")


def _call_gpt4(
    system_prompt: str,
    user_content: str,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _parse_numbered(raw: str, expected_count: int) -> list[str]:
    """
    Parse a numbered list response like "1. text\n2. text\n..." into a list.
    Falls back gracefully if GPT-4 returns unnumbered output.
    """
    lines = raw.strip().splitlines()
    results: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Remove leading "1. " or "1) " numbering
        if len(stripped) >= 3 and stripped[0].isdigit() and stripped[1] in ".)" and stripped[2] == " ":
            results.append(stripped[3:].strip())
        elif len(stripped) >= 4 and stripped[:2].isdigit() and stripped[2] in ".)" and stripped[3] == " ":
            results.append(stripped[4:].strip())
        else:
            results.append(stripped)

    # Ensure we always return exactly expected_count items
    if len(results) < expected_count:
        # Pad with empty strings (should not happen in practice)
        results.extend([""] * (expected_count - len(results)))
    return results[:expected_count]
