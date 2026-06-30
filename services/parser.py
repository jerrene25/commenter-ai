"""
parser.py
---------
Small shared helpers for validating and normalizing incoming Python source
code (from pasted text or uploaded files) before it reaches the AI or the
linter. Kept separate from routes so the validation logic is testable and
reusable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

MAX_SOURCE_BYTES = 200_000  # ~200 KB safety cap to keep generation times reasonable
ALLOWED_EXTENSIONS = {".py"}


class InvalidSourceError(ValueError):
    """Raised when submitted code/file fails basic validation."""


def normalize_source(raw_text: Optional[str]) -> str:
    """Normalizes line endings and trims trailing whitespace-only lines."""
    if raw_text is None:
        raise InvalidSourceError("No source code was provided.")
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    if text.strip() == "":
        raise InvalidSourceError("Source code is empty.")
    if len(text.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise InvalidSourceError("Source code is too large (limit is 200KB).")
    return text


def validate_uploaded_filename(filename: Optional[str]) -> str:
    """Ensures the uploaded file looks like a Python file before we touch it."""
    if not filename:
        raise InvalidSourceError("No file was uploaded.")
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise InvalidSourceError(f"Unsupported file type '{suffix}'. Please upload a .py file.")
    return filename
