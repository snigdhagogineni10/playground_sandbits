"""
Input classifier.
Determines what kind of input the user sent so the router can dispatch correctly.

Categories:
  - "video"      : a video file upload or URL pointing to a video
  - "transcript" : a .txt file upload or a long text message (likely a transcript)
  - "concept"    : a short text question or term (triggers concept simplification)
  - "summarise"  : user explicitly asked for a summary
"""

import re
from typing import Optional

# MIME types treated as video
_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/x-matroska",
    "video/webm",
    "video/quicktime",
    "video/avi",
    "video/x-msvideo",
}

# Keywords that trigger the summarise pipeline
_SUMMARISE_KEYWORDS = {"summarise", "summarize", "summary"}

# Heuristics for transcript detection
_TRANSCRIPT_MIN_CHARS = 300
_TRANSCRIPT_MIN_NEWLINES = 3


def classify_text(text: str) -> str:
    """
    Classify a plain text message.

    Returns one of: "summarise", "transcript", "concept".
    """
    stripped = text.strip()

    # Check for explicit summarise request
    if stripped.lower() in _SUMMARISE_KEYWORDS:
        return "summarise"
    if re.match(r"^(summarise|summarize|summary)\b", stripped.lower()):
        return "summarise"

    # Long text or multi-line → treat as transcript
    newline_count = stripped.count("\n")
    if len(stripped) >= _TRANSCRIPT_MIN_CHARS or newline_count >= _TRANSCRIPT_MIN_NEWLINES:
        return "transcript"

    return "concept"


def classify_document(mime_type: Optional[str], file_name: Optional[str]) -> str:
    """
    Classify a document/file upload.

    Args:
        mime_type: The MIME type of the uploaded file (may be None).
        file_name: The original filename (may be None).

    Returns one of: "video", "transcript", "unknown".
    """
    if mime_type in _VIDEO_MIME_TYPES:
        return "video"

    if mime_type == "text/plain":
        return "transcript"

    # Fallback: infer from file extension
    if file_name:
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext in {"mp4", "mkv", "webm", "mov", "avi"}:
            return "video"
        if ext == "txt":
            return "transcript"

    return "unknown"


def is_url(text: str) -> bool:
    """Return True if the text looks like an HTTP/HTTPS URL."""
    return bool(re.match(r"^https?://\S+$", text.strip()))
