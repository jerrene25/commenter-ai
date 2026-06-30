"""
commenter.py
------------
Core business logic for turning raw Python source into AI-commented Python
source. Orchestrates prompt building, model invocation, and output cleanup.
Kept independent of Flask so it can be reused (CLI, tests, future API
versions) without modification.
"""

from __future__ import annotations

import logging
import re

from ai.model_loader import get_model, ModelLoadError
from ai.prompt import build_comment_prompt

logger = logging.getLogger(__name__)

# Generation settings. Conservative temperature keeps comments stable
# and reduces the chance of run-away or repetitive generation.
GENERATION_SETTINGS = {
    "max_tokens": 1536,
    "temperature": 0.2,
    "top_p": 0.9,
    "repeat_penalty": 1.15,
    "stop": ["[INST]", "</s>", "[/INST]"],
}

CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)


class CommenterError(RuntimeError):
    """Raised when commenting fails for a reason the caller should surface to the user."""


def _strip_code_fences(text: str) -> str:
    """Removes any stray markdown code fences the model might add despite instructions."""
    text = CODE_FENCE_RE.sub("", text)
    return text.strip("\n")


def _looks_empty_or_invalid(source_code: str) -> bool:
    return source_code is None or source_code.strip() == ""


def generate_commented_code(source_code: str, style: str = "intermediate") -> str:
    """
    Sends the given Python source to the local LLM and returns a commented
    version. Raises CommenterError on any recoverable failure so the Flask
    route can turn it into a clean JSON error response instead of crashing.
    """
    if _looks_empty_or_invalid(source_code):
        raise CommenterError("No code was provided to comment on.")

    try:
        llm = get_model()
    except ModelLoadError as exc:
        raise CommenterError(str(exc)) from exc

    prompt = build_comment_prompt(source_code, style=style)

    try:
        result = llm(prompt, **GENERATION_SETTINGS)
    except Exception as exc:  # noqa: BLE001 - any backend failure should not crash the app
        logger.exception("Model generation failed")
        raise CommenterError(f"The AI model failed to generate a response: {exc}") from exc

    try:
        raw_text = result["choices"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise CommenterError("The AI model returned an unexpected response format.") from exc

    cleaned = _strip_code_fences(raw_text)

    if _looks_empty_or_invalid(cleaned):
        raise CommenterError("The AI model returned an empty response. Please try again.")

    return cleaned
