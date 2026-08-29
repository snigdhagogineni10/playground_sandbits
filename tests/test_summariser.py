"""Tests for services/summariser.py — mocks OpenAI API."""
from unittest.mock import MagicMock, patch


def _make_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


SAMPLE_SUMMARY = """లూప్ (loop) అంటే ఒక పని పదే పదే చేయడం.

- లూప్ (loop) repeat చేయడానికి వాడతారు
- for లూప్ (loop) count తెలిసినప్పుడు వాడతారు
- while లూప్ (loop) condition మీద ఆధారపడినప్పుడు వాడతారు
- infinite loop జాగ్రత్తగా avoid చేయాలి

| రకం | ఎప్పుడు వాడాలి |
|-----|----------------|
| for loop | count తెలిసినప్పుడు |
| while loop | condition మీద ఆధారపడినప్పుడు |"""


@patch("services.summariser.openai.chat.completions.create")
def test_summarise_returns_text(mock_create):
    mock_create.return_value = _make_response(SAMPLE_SUMMARY)
    from services.summariser import summarise
    result = summarise("Explain loops in programming", "English", "Telugu")
    assert "summary_text" in result
    assert len(result["summary_text"]) > 0


@patch("services.summariser.openai.chat.completions.create")
def test_summarise_contains_bullets(mock_create):
    mock_create.return_value = _make_response(SAMPLE_SUMMARY)
    from services.summariser import summarise
    result = summarise("Explain loops", "English", "Telugu")
    assert "-" in result["summary_text"]


@patch("services.summariser.openai.chat.completions.create")
def test_summarise_contains_table(mock_create):
    mock_create.return_value = _make_response(SAMPLE_SUMMARY)
    from services.summariser import summarise
    result = summarise("for loop vs while loop", "English", "Telugu")
    assert "|" in result["summary_text"]


@patch("services.summariser.openai.chat.completions.create")
def test_summarise_simpler_mode_prompt(mock_create):
    mock_create.return_value = _make_response("Simple summary without English terms.")
    from services.summariser import summarise
    summarise("Explain arrays", "English", "Telugu", mode="simpler")
    system_msg = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "Avoid English" in system_msg or "everyday" in system_msg


@patch("services.summariser.openai.chat.completions.create")
def test_summarise_target_english(mock_create):
    mock_create.return_value = _make_response("A loop repeats code.")
    from services.summariser import summarise
    summarise("Loops in programming", "Telugu", "English")
    system_msg = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "English" in system_msg
