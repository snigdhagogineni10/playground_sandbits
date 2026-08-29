"""
Link fetcher service.
Fetches 2-3 curated reference links (YouTube videos + articles) for a given topic.

Uses:
  1. A short GPT-4 call to extract the main topic keywords from the content.
  2. googlesearch-python to search for YouTube videos and articles.
"""

import logging
import openai
import config
from googlesearch import search

openai.api_key = config.OPENAI_API_KEY
logger = logging.getLogger(__name__)

_YOUTUBE_DOMAINS = {"youtube.com", "youtu.be"}


def fetch_links(content: str, num_links: int = 3) -> list[dict]:
    """
    Fetch curated reference links related to the main topic of the content.

    Args:
        content:   The concept explanation or transcript text to derive topic from.
        num_links: Total number of links to return (default 3).

    Returns:
        List of {"title": str, "url": str, "type": "video"|"article"}.
        Returns an empty list on any error (best-effort; non-blocking).
    """
    try:
        topic = _extract_topic(content)
        links = _search_links(topic, num_links)
        return links
    except Exception as exc:
        logger.warning("link_fetcher: failed to fetch links: %s", exc)
        return []


def _extract_topic(content: str) -> str:
    """Ask GPT-4 to extract 2-4 topic keywords from the content."""
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "What is the main technical topic of this text? "
                    "Reply with 2–4 English keywords only, separated by spaces. "
                    "No punctuation, no explanation."
                ),
            },
            {"role": "user", "content": content[:1000]},  # limit input length
        ],
        max_tokens=20,
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def _search_links(topic: str, num_links: int) -> list[dict]:
    """
    Search for YouTube videos and articles related to the topic.

    Strategy:
      - Search YouTube first (1-2 results)
      - Search for general articles (1-2 results, excluding YouTube)
      - Combine up to num_links total
    """
    results: list[dict] = []

    # YouTube search
    try:
        yt_query = f"{topic} tutorial site:youtube.com"
        for url in search(yt_query, num_results=5, sleep_interval=1):
            if _is_youtube(url) and len([r for r in results if r["type"] == "video"]) < 2:
                results.append({
                    "title": _title_from_url(url, topic, "video"),
                    "url": url,
                    "type": "video",
                })
            if len(results) >= num_links:
                break
    except Exception as exc:
        logger.warning("link_fetcher: YouTube search failed: %s", exc)

    # Article search (excluding YouTube URLs)
    articles_needed = num_links - len(results)
    if articles_needed > 0:
        try:
            article_query = f"{topic} explained tutorial"
            for url in search(article_query, num_results=10, sleep_interval=1):
                if not _is_youtube(url):
                    results.append({
                        "title": _title_from_url(url, topic, "article"),
                        "url": url,
                        "type": "article",
                    })
                    articles_needed -= 1
                if articles_needed <= 0 or len(results) >= num_links:
                    break
        except Exception as exc:
            logger.warning("link_fetcher: article search failed: %s", exc)

    return results[:num_links]


def _is_youtube(url: str) -> bool:
    return any(domain in url for domain in _YOUTUBE_DOMAINS)


def _title_from_url(url: str, topic: str, link_type: str) -> str:
    """Generate a readable title from the URL and topic keywords."""
    # Try to extract from URL path
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/").replace("-", " ").replace("_", " ")
        if path and len(path) > 4:
            return path.split("/")[-1].title()
    except Exception:
        pass
    # Fallback
    label = "Video" if link_type == "video" else "Article"
    return f"{topic.title()} — {label}"
