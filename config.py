"""
config.py — Loads environment variables from .env and exposes them as
module-level constants for use across the project.
"""

import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "dummy")
GREEN_API_INSTANCE_ID: str = os.environ["GREEN_API_INSTANCE_ID"]
GREEN_API_TOKEN: str = os.environ["GREEN_API_TOKEN"]
OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
