"""Tests for utils/session.py"""
from utils.session import get_session, update_session


def test_get_session_defaults():
    s = get_session("test_user_1")
    assert s["source_language"] is None
    assert s["target_language"] is None
    assert s["mode"] == "default"
    assert s["awaiting_feedback"] is False
    assert s["awaiting_custom_feedback"] is False


def test_update_and_get_session():
    update_session("test_user_2", source_language="English", source_language_code="en",
                   target_language="Telugu", target_language_code="te")
    s = get_session("test_user_2")
    assert s["source_language"] == "English"
    assert s["source_language_code"] == "en"
    assert s["target_language"] == "Telugu"
    assert s["target_language_code"] == "te"


def test_session_mode_roundtrip():
    update_session("test_user_3", mode="simpler")
    assert get_session("test_user_3")["mode"] == "simpler"
    update_session("test_user_3", mode="custom:use very simple words")
    assert get_session("test_user_3")["mode"] == "custom:use very simple words"


def test_awaiting_feedback_flag():
    update_session("test_user_4", awaiting_feedback=True)
    assert get_session("test_user_4")["awaiting_feedback"] is True
    update_session("test_user_4", awaiting_feedback=False)
    assert get_session("test_user_4")["awaiting_feedback"] is False


def test_last_segments_stored():
    segs = [{"start": 0.0, "end": 5.0, "text": "Hello"}]
    update_session("test_user_5", last_segments=segs)
    assert get_session("test_user_5")["last_segments"] == segs
