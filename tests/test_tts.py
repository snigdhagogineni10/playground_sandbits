"""Tests for services/tts.py — mocks gTTS and ffmpeg."""
import os
from unittest.mock import MagicMock, patch, call


SEGMENTS = [
    {"start": 0.0, "end": 5.0, "text": "Hello world"},
    {"start": 6.0, "end": 11.0, "text": "This is a test"},
]


def _mock_gtts_save(path):
    """Write a tiny stub .mp3 file so ffprobe has something to measure."""
    with open(path, "wb") as f:
        f.write(b"\x00" * 100)


@patch("services.tts.subprocess.run")
@patch("services.tts.gTTS")
def test_synthesise_aligned_creates_output(mock_gtts_cls, mock_subprocess):
    mock_gtts_inst = MagicMock()
    mock_gtts_inst.save.side_effect = _mock_gtts_save
    mock_gtts_cls.return_value = mock_gtts_inst

    # Mock ffprobe to return a duration of 3.0 seconds (clip < window of 5s)
    proc_result = MagicMock()
    proc_result.returncode = 0
    proc_result.stdout = "3.0\n"
    mock_subprocess.return_value = proc_result

    from services.tts import synthesise_aligned
    output = synthesise_aligned(SEGMENTS, "te")
    assert output.endswith(".mp3")
    assert os.path.dirname(output)  # output is in a temp directory


@patch("services.tts.subprocess.run")
@patch("services.tts.gTTS")
def test_synthesise_aligned_unsupported_lang(mock_gtts_cls, mock_subprocess):
    from services.tts import synthesise_aligned
    try:
        synthesise_aligned(SEGMENTS, "fr")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "fr" in str(e)


@patch("services.tts.subprocess.run")
@patch("services.tts.gTTS")
def test_synthesise_aligned_atempo_when_clip_overruns(mock_gtts_cls, mock_subprocess):
    mock_gtts_inst = MagicMock()
    mock_gtts_inst.save.side_effect = _mock_gtts_save
    mock_gtts_cls.return_value = mock_gtts_inst

    # Return clip duration longer than window (8s clip in a 5s window)
    proc_result = MagicMock()
    proc_result.returncode = 0
    proc_result.stdout = "8.0\n"
    mock_subprocess.return_value = proc_result

    from services.tts import synthesise_aligned
    output = synthesise_aligned(SEGMENTS[:1], "hi")
    # Verify atempo filter was used (it appears as "-filter:a" in ffmpeg call)
    ffmpeg_calls = [str(c) for c in mock_subprocess.call_args_list]
    assert any("atempo" in c for c in ffmpeg_calls)
