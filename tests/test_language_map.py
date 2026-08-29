"""Tests for utils/language_map.py"""
from utils.language_map import SUPPORTED_LANGUAGES, get_iso, get_name


def test_all_six_languages_present():
    assert len(SUPPORTED_LANGUAGES) == 6
    for name in ["English", "Hindi", "Telugu", "Tamil", "Kannada", "Malayalam"]:
        assert name in SUPPORTED_LANGUAGES


def test_iso_codes_correct():
    assert SUPPORTED_LANGUAGES["English"] == "en"
    assert SUPPORTED_LANGUAGES["Hindi"] == "hi"
    assert SUPPORTED_LANGUAGES["Telugu"] == "te"
    assert SUPPORTED_LANGUAGES["Tamil"] == "ta"
    assert SUPPORTED_LANGUAGES["Kannada"] == "kn"
    assert SUPPORTED_LANGUAGES["Malayalam"] == "ml"


def test_get_iso():
    assert get_iso("Telugu") == "te"
    assert get_iso("English") == "en"
    assert get_iso("Unknown") is None


def test_get_name():
    assert get_name("te") == "Telugu"
    assert get_name("en") == "English"
    assert get_name("xx") is None
