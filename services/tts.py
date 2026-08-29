"""
Timestamp-aligned TTS audio synthesis.

For each segment {start, end, text}, generates a TTS clip and fits it
exactly into the [start, end] time window by:
  - Prepending gap-silence (time between previous segment end and this start)
  - Appending trailing silence if TTS clip is shorter than the window
  - Speeding up via ffmpeg atempo filter if TTS clip is longer than the window

All windowed clips are concatenated into one aligned .mp3 matching the video duration.
"""

import os
import subprocess
import tempfile
from gtts import gTTS

_SUPPORTED_LANGS = {"en", "hi", "te", "ta", "kn", "ml"}


def synthesise_aligned(segments: list[dict], target_language_code: str) -> str:
    """
    Synthesise TTS for each segment and align each clip to its timestamp window.

    Args:
        segments:             List of {"start": float, "end": float, "text": str}.
        target_language_code: ISO code for the TTS language (en/hi/te/ta/kn/ml).

    Returns:
        Path to the final aligned .mp3 file. Caller should delete when done.

    Raises:
        ValueError: If target_language_code is not supported.
        RuntimeError: On ffmpeg/gTTS failures.
    """
    if target_language_code not in _SUPPORTED_LANGS:
        raise ValueError(
            f"Unsupported TTS language code '{target_language_code}'. "
            f"Must be one of {_SUPPORTED_LANGS}."
        )

    tmp_dir = tempfile.mkdtemp()
    windowed_clips: list[str] = []
    prev_end = 0.0

    for i, seg in enumerate(segments):
        start: float = seg["start"]
        end: float = seg["end"]
        text: str = seg["text"].strip()
        window: float = end - start
        gap: float = start - prev_end  # silence before this segment

        if not text:
            # No speech — fill the whole gap+window with silence
            silence_path = _generate_silence(gap + window, tmp_dir, f"full_silence_{i}")
            windowed_clips.append(silence_path)
            prev_end = end
            continue

        # 1. Generate TTS clip
        tts_path = os.path.join(tmp_dir, f"tts_{i}.mp3")
        _generate_tts(text, target_language_code, tts_path)

        # 2. Measure clip duration
        clip_duration = _get_duration(tts_path)

        # 3. Fit clip into [start, end] window
        windowed_path = _fit_clip(
            tts_path=tts_path,
            clip_duration=clip_duration,
            window=window,
            gap=gap,
            tmp_dir=tmp_dir,
            index=i,
        )
        windowed_clips.append(windowed_path)
        prev_end = end

    # 4. Concatenate all windowed clips into a single aligned .mp3
    aligned_path = os.path.join(tmp_dir, "aligned.mp3")
    _concatenate_clips(windowed_clips, aligned_path, tmp_dir)

    return aligned_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_tts(text: str, lang: str, output_path: str) -> None:
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(output_path)


def _generate_silence(duration: float, tmp_dir: str, name: str) -> str:
    if duration <= 0:
        duration = 0.01  # ffmpeg requires positive duration
    path = os.path.join(tmp_dir, f"{name}.mp3")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration),
        "-acodec", "libmp3lame",
        path,
    ]
    _run(cmd)
    return path


def _get_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _fit_clip(
    tts_path: str,
    clip_duration: float,
    window: float,
    gap: float,
    tmp_dir: str,
    index: int,
) -> str:
    """
    Return a single .mp3 clip that spans exactly gap + window seconds:
      [gap silence] + [tts (possibly sped up)] + [trailing silence]
    """
    parts: list[str] = []

    # Leading gap silence
    if gap > 0:
        gap_silence = _generate_silence(gap, tmp_dir, f"gap_{index}")
        parts.append(gap_silence)

    if clip_duration <= window:
        # TTS fits — append trailing silence
        parts.append(tts_path)
        trailing = window - clip_duration
        if trailing > 0:
            trail_silence = _generate_silence(trailing, tmp_dir, f"trail_{index}")
            parts.append(trail_silence)
    else:
        # TTS overruns — speed it up to fit within window
        speed = clip_duration / window
        speed = min(speed, 2.0)  # cap at 2× per atempo filter range

        sped_path = os.path.join(tmp_dir, f"sped_{index}.mp3")
        if speed > 2.0:
            # Chain two atempo filters for speed > 2.0
            filter_str = f"atempo=2.0,atempo={speed / 2.0:.4f}"
        else:
            filter_str = f"atempo={speed:.4f}"

        cmd = [
            "ffmpeg", "-y",
            "-i", tts_path,
            "-filter:a", filter_str,
            sped_path,
        ]
        _run(cmd)
        parts.append(sped_path)

    # Concatenate parts into one windowed clip
    if len(parts) == 1:
        return parts[0]

    windowed_path = os.path.join(tmp_dir, f"windowed_{index}.mp3")
    _concatenate_clips(parts, windowed_path, tmp_dir)
    return windowed_path


def _concatenate_clips(clips: list[str], output_path: str, tmp_dir: str) -> None:
    """Concatenate a list of .mp3 files into output_path using ffmpeg concat."""
    list_file = os.path.join(tmp_dir, f"concat_{os.path.basename(output_path)}.txt")
    with open(list_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-acodec", "libmp3lame",
        output_path,
    ]
    _run(cmd)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg command failed: {' '.join(cmd)}\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )
