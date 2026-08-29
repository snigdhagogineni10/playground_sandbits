"""
Summary service.
Generates a concise structured summary of a concept or transcript in the
user's target language, plus 2-3 curated reference links (YouTube + articles).
"""

import openai
import config

openai.api_key = config.OPENAI_API_KEY

_TECH_TERMS = (
    "variable, array, loop, function, class, object, method, string, integer, "
    "boolean, pointer, stack, queue, API, database, algorithm"
)


def summarise(
    content: str,
    source_lang: str,
    target_lang: str,
    mode: str = "default",
) -> dict:
    """
    Generate a short structured summary of the given content in target_lang.

    Args:
        content:     The text to summarise (concept explanation or transcript).
        source_lang: Full source language name, e.g. "English".
        target_lang: Full target language name, e.g. "Telugu".
        mode:        "default" | "simpler" | "more_english" | "custom:<text>"

    Returns:
        {"summary_text": str}
        (links are fetched separately via link_fetcher.fetch_links)
    """
    system_prompt = _build_summary_prompt(target_lang, mode)
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        temperature=0.4,
        max_tokens=800,
    )
    summary_text = response.choices[0].message.content.strip()
    return {"summary_text": summary_text}


def _build_summary_prompt(target_lang: str, mode: str) -> str:
    base = (
        f"You are a study assistant. Given the following content, produce a short "
        f"summary in {target_lang}.\n\n"
        f"Format your response exactly as:\n"
        f"1. One plain-words sentence at the top (max 1 line) explaining the concept simply.\n"
        f"2. 3–5 bullet points (using '-') covering the key ideas.\n"
        f"3. A compact comparison table (max 3 rows, markdown format) ONLY if the topic "
        f"involves comparable items (e.g. for loop vs while loop, list vs array). "
        f"Skip the table if there's nothing meaningful to compare.\n\n"
        f"Keep the summary brief, simple, and easy to understand.\n"
    )

    if target_lang.lower() == "english":
        terminology = "Use standard English technical terminology."
    elif mode == "simpler":
        terminology = (
            f"Avoid English technical terms. Use simple everyday {target_lang} words instead."
        )
    elif mode == "more_english":
        terminology = (
            f"Keep as many English technical terms as possible. "
            f"Translate only the connecting language into {target_lang}."
        )
    elif mode.startswith("custom:"):
        custom = mode[len("custom:"):]
        terminology = (
            f"Keep all technical English terms ({_TECH_TERMS}) in English. "
            f"Additionally: {custom}"
        )
    else:  # default
        terminology = (
            f"Keep all technical English terms ({_TECH_TERMS}) in English. "
            f"For each English term, also write it in {target_lang} script before it "
            f"in parentheses — format: targetscript (English). "
            f"Example for Telugu: లూప్ (loop)."
        )

    return base + terminology
