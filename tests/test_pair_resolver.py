"""Tests for utils/pair_resolver.py"""
from utils.pair_resolver import resolve_pair


def _session(src_iso, tgt_iso):
    return {
        "source_language_code": src_iso,
        "target_language_code": tgt_iso,
    }


def test_en_to_te_resolves():
    src, tgt = resolve_pair("en", _session("en", "te"))
    assert src == "en"
    assert tgt == "te"


def test_te_to_ta_resolves():
    src, tgt = resolve_pair("te", _session("te", "ta"))
    assert src == "te"
    assert tgt == "ta"


def test_auto_detect_source_uses_detected():
    src, tgt = resolve_pair("hi", _session("auto", "te"))
    assert src == "hi"
    assert tgt == "te"


def test_same_language_still_returns_pair(caplog):
    """Should warn but NOT raise — processing continues."""
    src, tgt = resolve_pair("ta", _session("ta", "ta"))
    assert src == "ta"
    assert tgt == "ta"
    assert any("same" in r.message.lower() for r in caplog.records)


def test_source_matches_session():
    src, tgt = resolve_pair("kn", _session("kn", "ml"))
    assert src == "kn"
    assert tgt == "ml"
