"""
Entry point for the Multilingual Education Bot.
Starts the Telegram bot in polling mode.
Run the WhatsApp bot separately: `flask --app bot.whatsapp_bot run`
"""

import logging
from bot.telegram_bot import build_application

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)


def main() -> None:
    app = build_application()
    logging.getLogger(__name__).info("Starting Multilingual Education Bot (Telegram polling)…")
    app.run_polling()


if __name__ == "__main__":
    main()
