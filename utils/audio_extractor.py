"""
Audio extraction utility.
Accepts either a local video file path or a remote URL.
Returns path to a temporary .mp3 audio file.
"""

import os
import subprocess
import tempfile
import ffmpeg


def extract_audio(source: str) -> str:
    """
    Extract audio from a local video file or download and extract from a URL.

    Args:
        source: Local file path or HTTP/HTTPS URL to a video.

    Returns:
        Path to a temporary .mp3 audio file. Caller is responsible for deleting it.

    Raises:
        RuntimeError: If extraction or download fails.
    """
    tmp_dir = tempfile.mkdtemp()

    if _is_url(source):
        return _download_and_extract(source, tmp_dir)
    else:
        return _extract_local(source, tmp_dir)


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _download_and_extract(url: str, tmp_dir: str) -> str:
    """Download full video via yt-dlp, then extract audio with ffmpeg."""
    video_path = os.path.join(tmp_dir, "video.%(ext)s")
    download_cmd = [
        "yt-dlp",
        "--output", video_path,
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        url,
    ]
    result = subprocess.run(download_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    # Find the downloaded file
    downloaded = None
    for fname in os.listdir(tmp_dir):
        if fname.startswith("video."):
            downloaded = os.path.join(tmp_dir, fname)
            break
    if downloaded is None:
        raise RuntimeError("yt-dlp download produced no output file.")

    return _extract_local(downloaded, tmp_dir)


def _extract_local(video_path: str, tmp_dir: str) -> str:
    """Extract audio from a local video file to .mp3 using ffmpeg."""
    audio_path = os.path.join(tmp_dir, "audio.mp3")
    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, format="mp3", acodec="libmp3lame", ac=1, ar="44100")
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg audio extraction failed: {e.stderr.decode()}")
    return audio_path
