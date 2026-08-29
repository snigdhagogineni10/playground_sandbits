"""Tests for services/simplifier.py — mocks OpenAI API."""
from unittest.mock import MagicMock, patch


def _make_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("services.simplifier.openai.chat.completions.create")
def test_simplify_default_mode(mock_create):
    mock_create.return_value = _make_response("A variable is a box that stores a value.")
    from services.simplifier import simplify
    result = simplify("What is a variable?", "English", "Telugu")
    assert isinstance(result, str)
    assert len(result) > 0
    call_args = mock_create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert "English" in system_msg
    assert "Telugu" in system_msg
    assert "English as-is" in system_msg or "English exactly" in system_msg or "English as written" in system_msg


@patch("services.simplifier.openai.chat.completions.create")
def test_simplify_simpler_mode(mock_create):
    mock_create.return_value = _make_response("చదవడం లాంటిది.")
    from services.simplifier import simplify
    result = simplify("What is a loop?", "English", "Telugu", mode="simpler")
    assert result == "చదవడం లాంటిది."
    system_msg = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "Avoid English terms" in system_msg or "everyday" in system_msg


@patch("services.simplifier.openai.chat.completions.create")
def test_simplify_more_english_mode(mock_create):
    mock_create.return_value = _make_response("A loop iterates over values.")
    from services.simplifier import simplify
    result = simplify("What is a loop?", "Telugu", "English", mode="more_english")
    assert result == "A loop iterates over values."
    system_msg = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "maximum" in system_msg or "as many" in system_msg


@patch("services.simplifier.openai.chat.completions.create")
def test_simplify_custom_mode(mock_create):
    mock_create.return_value = _make_response("Custom result.")
    from services.simplifier import simplify
    result = simplify("Explain recursion", "English", "Hindi", mode="custom:use cooking analogies")
    system_msg = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "cooking analogies" in system_msg


@patch("services.simplifier.openai.chat.completions.create")
def test_simplify_te_to_ta(mock_create):
    mock_create.return_value = _make_response("ஒரு மாறி ஒரு பெட்டி.")
    from services.simplifier import simplify
    result = simplify("వేరియబుల్ అంటే ఏమిటి?", "Telugu", "Tamil")
    assert len(result) > 0
    system_msg = mock_create.call_args.kwargs["messages"][0]["content"]
    assert "Telugu" in system_msg
    assert "Tamil" in system_msg
