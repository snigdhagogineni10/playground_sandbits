# Playground — Multilingual Education Bot

A Telegram + WhatsApp bot that translates, simplifies, and dubs educational content across **6 languages** — English, Hindi, Telugu, Tamil, Kannada, and Malayalam — with any-to-any translation across all 30 directional pairs.

## What it does

- **Concept simplification** — explain a technical concept in any target language
- **Smart output by input type**
  - Video (file or URL) → returns a dubbed video with translated, timestamp-aligned audio
  - Text/transcript → returns a translated `.txt` file
- **On-demand summaries** — `/summarise` returns a short structured digest (bullets, key-concept table, 2–3 curated reference links) in the target language
- **Consistent technical terms** — technical vocabulary (variable, array, loop, function, etc.) is always kept in or annotated with English, e.g. `వేరియబుల్ (variable)` for Telugu
- **Feedback loop** — after every output, the user can mark it satisfactory, ask for simpler/more technical language, or leave free-text feedback, and the bot regenerates accordingly

## Tech stack

- Python
- `python-telegram-bot` for Telegram
- Twilio API for WhatsApp
- OpenAI Whisper for speech-to-text
- OpenAI GPT-4 for translation, simplification, and back-translation checks
- `langdetect` for fast language pre-filtering
- `gTTS` for text-to-speech output
- `ffmpeg` / `ffmpeg-python` for audio extraction and video muxing
- `yt-dlp` for downloading video from URLs

## Project structure

```
playground/
├── bot/            # Telegram and WhatsApp bot entry points
├── services/       # Translation, summarisation, TTS, transcription, dubbing
├── utils/          # Session, language detection/mapping, input classification
├── subtitles/       # Subtitle handling
├── tests/          # Unit tests
├── config.py       # Loads environment variables
├── main.py         # Entry point (Telegram polling)
└── requirements.txt
```

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   Required keys: `TELEGRAM_BOT_TOKEN`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`, `OPENAI_API_KEY`

3. Run the Telegram bot:
   ```bash
   python main.py
   ```
4. Run the WhatsApp bot separately:
   ```bash
   flask --app bot.whatsapp_bot run
   ```

## Status

Work in progress — see `multilingual-edu-bot-plan.md` for the full task breakdown and roadmap.
