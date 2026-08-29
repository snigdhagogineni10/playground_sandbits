"""
Audio transcription service using OpenAI Whisper.
Accepts a path to an audio file and returns timestamped segments
plus the auto-detected source language.
"""

import os
import math
import subprocess
import tempfile
from typing import Any

import openai
import config

openai.api_key = config.OPENAI_API_KEY

_WHISPER_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


def transcribe(audio_path: str) -> dict[str, Any]:
    """
    Transcribe an audio file using Whisper with auto language detection.

    Args:
        audio_path: Path to a .mp3 (or other Whisper-supported) audio file.

    Returns:
        {
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "detected_language": "<iso_code>",   # e.g. "te", "en", "hi"
        }
    """
    file_size = os.path.getsize(audio_path)

    if file_size <= _WHISPER_MAX_BYTES:
        return _transcribe_file(audio_path)

    # File too large — chunk and transcribe each piece, then merge
    chunks = _chunk_audio(audio_path)
    all_segments: list[dict] = []
    detected_language = "en"
    time_offset = 0.0

    for chunk_path in chunks:
        result = _transcribe_file(chunk_path)
        detected_language = result["detected_language"]
        for seg in result["segments"]:
            all_segments.append({
                "start": seg["start"] + time_offset,
                "end": seg["end"] + time_offset,
                "text": seg["text"],
            })
        # Estimate chunk duration from last segment end
        if result["segments"]:
            time_offset = all_segments[-1]["end"]
        os.remove(chunk_path)

    return {"segments": all_segments, "detected_language": detected_language}


def _transcribe_file(audio_path: str) -> dict[str, Any]:
    """Transcribe a single audio file (must be <= 25 MB)."""
    with open(audio_path, "rb") as f:
        response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            # No 'language' param — let Whisper auto-detect
        )

    segments = [
        {
            "start": float(seg.start),
            "end": float(seg.end),
            "text": seg.text.strip(),
        }
        for seg in response.segments
    ]
    detected_language = getattr(response, "language", "en") or "en"
    return {"segments": segments, "detected_language": detected_language}


def _chunk_audio(audio_path: str, chunk_duration_sec: int = 600) -> list[str]:
    """
    Split audio into chunks of up to chunk_duration_sec seconds using ffmpeg.
    Returns list of temp chunk file paths.
    """
    tmp_dir = tempfile.mkdtemp()

    # Get total duration
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    total_duration = float(result.stdout.strip())
    num_chunks = math.ceil(total_duration / chunk_duration_sec)

    chunk_paths = []
    for i in range(num_chunks):
        start = i * chunk_duration_sec
        chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.mp3")
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(start),
            "-t", str(chunk_duration_sec),
            "-acodec", "libmp3lame",
            chunk_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        chunk_paths.append(chunk_path)

    return chunk_paths
