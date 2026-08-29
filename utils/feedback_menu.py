"""
Feedback menu utility.
Sends a post-output feedback menu to the user after every bot response.

Buttons:
  1. Satisfied
  2. Simpler     — label dynamically references target_lang
  3. More English technical terms
  4. Share your feedback (free-text)
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot


async def send_feedback_menu(
    chat_id: int | str,
    bot: Bot,
    target_lang: str,
) -> None:
    """
    Send a feedback inline keyboard to the given Telegram chat.

    Args:
        chat_id:     Telegram chat ID.
        bot:         The Telegram Bot instance.
        target_lang: Full target language name, e.g. "Telugu". Used in button label.
    """
    keyboard = [
        [InlineKeyboardButton("✅ Satisfied", callback_data="fb:satisfied")],
        [InlineKeyboardButton(
            f"🔄 Simpler — use {target_lang} words instead of English terms",
            callback_data="fb:simpler",
        )],
        [InlineKeyboardButton("📘 More English technical terms", callback_data="fb:more_english")],
        [InlineKeyboardButton("✏️ Share your feedback", callback_data="fb:custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.send_message(
        chat_id=chat_id,
        text="How was the output? Let me know so I can improve it:",
        reply_markup=reply_markup,
    )


def whatsapp_feedback_text(target_lang: str) -> str:
    """
    Return a WhatsApp-compatible feedback menu as plain text.

    Args:
        target_lang: Full target language name used in option 2.
    """
    return (
        "How was the output?\n"
        "Reply with a number:\n"
        f"1 — ✅ Satisfied\n"
        f"2 — 🔄 Simpler (use {target_lang} words instead of English terms)\n"
        f"3 — 📘 More English technical terms\n"
        f"4 — ✏️ Share your own feedback"
    )
