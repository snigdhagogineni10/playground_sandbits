"""Tests for services/translator.py — mocks OpenAI API."""
from unittest.mock import MagicMock, patch


def _make_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "A variable stores a value."},
    {"start": 6.0, "end": 12.0, "text": "A loop repeats an action."},
]


@patch("services.translator.openai.chat.completions.create")
def test_translate_segments_preserves_timestamps(mock_create):
    # First call: translation; second call: back-translation; third call: meaning check
    mock_create.side_effect = [
        _make_response("1. ఒక వేరియబుల్ (variable) విలువను నిల్వ చేస్తుంది.\n2. ఒక లూప్ (loop) పదే పదే పని చేస్తుంది."),
        _make_response("1. A variable stores a value.\n2. A loop repeats an action."),
        _make_response("YES"),
    ]
    from services.translator import translate_segments
    result = translate_segments(SEGMENTS, "English", "Telugu")
    assert len(result) == 2
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 5.0
    assert result[1]["start"] == 6.0
    assert result[1]["end"] == 12.0
    assert isinstance(result[0]["text"], str)


@patch("services.translator.openai.chat.completions.create")
def test_translate_text_en_to_te_terminology_format(mock_create):
    mock_create.side_effect = [
        _make_response("లూప్ (loop) లో వేరియబుల్ (variable) ని డిక్లేర్ (declare) చేయండి."),
        _make_response("Declare a variable inside a loop."),
        _make_response("YES"),
    ]
    from services.translator import translate_text
    result = translate_text("Declare a variable inside a loop.", "English", "Telugu")
    assert "(loop)" in result or "లూప్" in result


@patch("services.translator.openai.chat.completions.create")
def test_translate_text_to_english_no_parens(mock_create):
    mock_create.side_effect = [
        _make_response("Declare a variable inside a loop."),
        _make_response("ఒక లూప్ లో వేరియబుల్ ని డిక్లేర్ చేయండి."),
        _make_response("YES"),
    ]
    from services.translator import translate_text
    result = translate_text("ఒక లూప్ లో వేరియబుల్ ని డిక్లేర్ చేయండి.", "Telugu", "English")
    # When target is English, no parenthetical annotations
    system_prompt = mock_create.call_args_list[0].kwargs["messages"][0]["content"]
    assert "parenthetical" not in system_prompt or "clean English" in system_prompt


@patch("services.translator.openai.chat.completions.create")
def test_back_translation_retry_triggered(mock_create):
    """If meaning check returns NO, translator should retry once."""
    mock_create.side_effect = [
        _make_response("1. Translation attempt 1."),   # first translate
        _make_response("1. Completely different meaning."),  # back-translate
        _make_response("NO"),                           # meaning check → fail
        _make_response("1. Translation attempt 2."),   # retry translate
    ]
    from services.translator import translate_segments
    segs = [{"start": 0.0, "end": 5.0, "text": "A variable stores a value."}]
    result = translate_segments(segs, "English", "Telugu")
    # Retry should have been called (4 total OpenAI calls)
    assert mock_create.call_count == 4
    assert len(result) == 1


@patch("services.translator.openai.chat.completions.create")
def test_translate_segments_te_to_ta(mock_create):
    mock_create.side_effect = [
        _make_response("1. ஒரு மாறி மதிப்பை சேமிக்கிறது."),
        _make_response("1. ఒక వేరియబుల్ విలువను నిల్వ చేస్తుంది."),
        _make_response("YES"),
    ]
    from services.translator import translate_segments
    segs = [{"start": 0.0, "end": 5.0, "text": "ఒక వేరియబుల్ విలువను నిల్వ చేస్తుంది."}]
    result = translate_segments(segs, "Telugu", "Tamil")
    assert result[0]["start"] == 0.0
    assert result[0]["end"] == 5.0
    assert isinstance(result[0]["text"], str)
