"""
config.py — Loads environment variables from .env and exposes them as
module-level constants for use across the project.
"""

import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TWILIO_ACCOUNT_SID: str = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN: str = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_NUMBER: str = os.environ["TWILIO_WHATSAPP_NUMBER"]
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
