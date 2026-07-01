"""
model_loader.py
---------------
Stub retained for architectural compatibility.
Using Groq API backend instead of a local model.
"""

from __future__ import annotations
import os


class ModelLoadError(RuntimeError):
    pass


def get_model():
    raise ModelLoadError("Local model loading disabled. Using Groq API instead.")


def model_status() -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    return {
        "loaded": bool(api_key),
        "backend": "Groq API (llama-3.3-70b-versatile)",
        "error": None if api_key else "GROQ_API_KEY secret not set",
    }