"""Tests for services/video_dubber.py — mocks ffmpeg subprocess."""
from unittest.mock import patch, MagicMock
import os


@patch("services.video_dubber.subprocess.run")
def test_dub_video_returns_path(mock_run):
    mock_run.return_value = MagicMock(returncode=0)

    # Create tiny stub files so the function can reference them
    import tempfile
    tmp = tempfile.mkdtemp()
    video = os.path.join(tmp, "video.mp4")
    audio = os.path.join(tmp, "audio.mp3")
    open(video, "wb").close()
    open(audio, "wb").close()

    from services.video_dubber import dub_video
    result = dub_video(video, audio)
    assert result.endswith(".mp4")
    assert mock_run.called

    # Verify ffmpeg args include -c:v copy and both inputs
    cmd = mock_run.call_args[0][0]
    assert "ffmpeg" in cmd
    assert video in cmd
    assert audio in cmd
    assert "-c:v" in cmd
    assert "copy" in cmd


@patch("services.video_dubber.subprocess.run")
def test_dub_video_raises_on_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr=b"error")

    import tempfile
    tmp = tempfile.mkdtemp()
    video = os.path.join(tmp, "v.mp4")
    audio = os.path.join(tmp, "a.mp3")
    open(video, "wb").close()
    open(audio, "wb").close()

    from services.video_dubber import dub_video
    try:
        dub_video(video, audio)
        assert False, "Should have raised RuntimeError"
    except RuntimeError:
        pass
