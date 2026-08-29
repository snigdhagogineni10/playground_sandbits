"""
Concept simplification service.
Explains a technical concept in any target language using GPT-4.
Supports any-to-any language pair across the 6 supported languages.
"""

import openai
import config

openai.api_key = config.OPENAI_API_KEY


def simplify(
    text: str,
    source_lang: str,
    target_lang: str,
    mode: str = "default",
) -> str:
    """
    Explain a technical concept or term in target_lang.

    Args:
        text:        The concept or question to explain (in source_lang).
        source_lang: Full language name of the input, e.g. "Telugu".
        target_lang: Full language name of the desired explanation, e.g. "Hindi".
        mode:        One of "default", "simpler", "more_english", or "custom:<instruction>".

    Returns:
        Explanation string in target_lang.
    """
    base = (
        f"You are an education assistant. The input is in {source_lang}. "
        f"Explain the concept simply in {target_lang}."
    )

    if target_lang.lower() == "english":
        system_prompt = base + " Explain in clear, simple English."
    elif mode == "default":
        system_prompt = (
            base
            + " Keep all technical programming terms (variable, array, loop, function,"
            " class, object, etc.) in English as-is, embedded naturally within the"
            f" {target_lang} explanation."
        )
    elif mode == "simpler":
        system_prompt = (
            base
            + f" Replace English technical terms with simple everyday {target_lang}"
            " words or phrases. Avoid English terms entirely."
        )
    elif mode == "more_english":
        system_prompt = (
            base
            + " Keep as many technical English terms as possible in English."
            f" Only translate the connecting/structural language into {target_lang}."
        )
    elif mode.startswith("custom:"):
        custom_instruction = mode[len("custom:"):]
        system_prompt = base + " " + custom_instruction
    else:
        # Unrecognised mode — fall back to default behaviour
        system_prompt = (
            base
            + " Keep all technical programming terms (variable, array, loop, function,"
            " class, object, etc.) in English as-is, embedded naturally within the"
            f" {target_lang} explanation."
        )

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )

    return response.choices[0].message.content.strip()
