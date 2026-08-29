"""
Video dubbing service.
Replaces the original audio track of a video with a pre-aligned translated audio file.
"""

import os
import subprocess
import tempfile


def dub_video(video_path: str, aligned_audio_path: str) -> str:
    """
    Replace the original audio track of a video with aligned translated audio.

    Args:
        video_path:          Path to the original .mp4 (or other) video file.
        aligned_audio_path:  Path to the aligned translated audio .mp3.

    Returns:
        Path to the dubbed output .mp4 file. Caller should delete when done.

    Raises:
        RuntimeError: If ffmpeg fails.
    """
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "dubbed.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", aligned_audio_path,
        "-c:v", "copy",          # copy video stream as-is (fast, no re-encode)
        "-map", "0:v:0",         # take video from first input
        "-map", "1:a:0",         # take audio from second input
        "-shortest",             # end at the shorter of video/audio
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg dubbing failed:\n{result.stderr.decode(errors='replace')}"
        )

    return output_path
