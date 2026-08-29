"""Tests for utils/feedback_menu.py"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.mark.asyncio
async def test_send_feedback_menu_telegram():
    mock_bot = AsyncMock()
    from utils.feedback_menu import send_feedback_menu
    await send_feedback_menu(chat_id=12345, bot=mock_bot, target_lang="Telugu")
    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == 12345
    # Button 2 label should reference target language
    markup = call_kwargs["reply_markup"]
    all_button_texts = [btn.text for row in markup.inline_keyboard for btn in row]
    assert any("Telugu" in text for text in all_button_texts)


def test_whatsapp_feedback_text_contains_target_lang():
    from utils.feedback_menu import whatsapp_feedback_text
    text = whatsapp_feedback_text("Tamil")
    assert "Tamil" in text
    assert "1" in text
    assert "2" in text
    assert "3" in text
    assert "4" in text


def test_feedback_button_callback_data():
    """Verify callback data values used in feedback buttons."""
    from utils.feedback_menu import send_feedback_menu
    from unittest.mock import AsyncMock
    import asyncio

    mock_bot = AsyncMock()
    asyncio.get_event_loop().run_until_complete(
        send_feedback_menu(12345, mock_bot, "Kannada")
    )
    markup = mock_bot.send_message.call_args.kwargs["reply_markup"]
    callback_data_values = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert "fb:satisfied" in callback_data_values
    assert "fb:simpler" in callback_data_values
    assert "fb:more_english" in callback_data_values
    assert "fb:custom" in callback_data_values
