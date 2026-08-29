"""Tests for utils/input_classifier.py"""
from utils.input_classifier import classify_text, classify_document, is_url


def test_short_text_is_concept():
    assert classify_text("What is a variable?") == "concept"
    assert classify_text("Explain recursion") == "concept"


def test_long_text_is_transcript():
    long = "This is a line.\n" * 20
    assert classify_text(long) == "transcript"


def test_long_char_text_is_transcript():
    long = "a" * 350
    assert classify_text(long) == "transcript"


def test_summarise_keyword():
    assert classify_text("summarise") == "summarise"
    assert classify_text("Summarize") == "summarise"
    assert classify_text("summary") == "summarise"


def test_document_video():
    assert classify_document("video/mp4", "lecture.mp4") == "video"
    assert classify_document("video/x-matroska", "video.mkv") == "video"


def test_document_txt():
    assert classify_document("text/plain", "notes.txt") == "transcript"


def test_document_by_extension():
    assert classify_document(None, "video.mp4") == "video"
    assert classify_document(None, "transcript.txt") == "transcript"


def test_document_unknown():
    assert classify_document("application/pdf", "doc.pdf") == "unknown"


def test_is_url():
    assert is_url("https://youtube.com/watch?v=abc") is True
    assert is_url("http://example.com/video.mp4") is True
    assert is_url("not a url") is False
    assert is_url("What is a loop?") is False
