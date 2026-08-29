"""Tests for services/link_fetcher.py — mocks googlesearch and OpenAI."""
from unittest.mock import MagicMock, patch


def _make_gpt_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("services.link_fetcher.search")
@patch("services.link_fetcher.openai.chat.completions.create")
def test_fetch_links_returns_video_and_article(mock_create, mock_search):
    mock_create.return_value = _make_gpt_response("python loops tutorial")
    mock_search.side_effect = [
        # YouTube search results
        iter(["https://youtube.com/watch?v=abc123", "https://youtube.com/watch?v=def456"]),
        # Article search results
        iter(["https://www.w3schools.com/python/python_for_loops.asp",
              "https://realpython.com/python-for-loop/"]),
    ]

    from services.link_fetcher import fetch_links
    links = fetch_links("A loop repeats an action.")

    assert len(links) <= 3
    types = [l["type"] for l in links]
    assert "video" in types
    assert "article" in types


@patch("services.link_fetcher.search")
@patch("services.link_fetcher.openai.chat.completions.create")
def test_youtube_classified_as_video(mock_create, mock_search):
    mock_create.return_value = _make_gpt_response("arrays data structures")
    mock_search.side_effect = [
        iter(["https://youtu.be/shortlink123"]),
        iter(["https://geeksforgeeks.org/array"]),
    ]

    from services.link_fetcher import fetch_links
    links = fetch_links("An array stores multiple values.")
    yt_links = [l for l in links if l["type"] == "video"]
    assert all("youtube" in l["url"] or "youtu.be" in l["url"] for l in yt_links)


@patch("services.link_fetcher.search")
@patch("services.link_fetcher.openai.chat.completions.create")
def test_fetch_links_returns_empty_on_search_error(mock_create, mock_search):
    mock_create.return_value = _make_gpt_response("loops")
    mock_search.side_effect = Exception("network error")

    from services.link_fetcher import fetch_links
    links = fetch_links("Loops explanation")
    assert links == []
