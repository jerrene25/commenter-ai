"""
commenter.py
------------
Calls the Groq API to generate AI-powered comments for Python code.
Groq provides free, fast inference on open-source LLMs.
"""

from __future__ import annotations

import logging
import os
import re

from groq import Groq

from ai.prompt import SYSTEM_INSTRUCTIONS, COMMENT_STYLE_HINTS

logger = logging.getLogger(__name__)

CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)


class CommenterError(RuntimeError):
    pass


def _strip_code_fences(text: str) -> str:
    return CODE_FENCE_RE.sub("", text).strip("\n")


def _looks_empty_or_invalid(source_code: str) -> bool:
    return source_code is None or source_code.strip() == ""


def generate_commented_code(source_code: str, style: str = "intermediate") -> str:
    if _looks_empty_or_invalid(source_code):
        raise CommenterError("No code was provided to comment on.")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise CommenterError(
            "GROQ_API_KEY is not set. Add it as a secret in your Hugging Face Space settings."
        )

    style_hint = COMMENT_STYLE_HINTS.get(style, COMMENT_STYLE_HINTS["intermediate"])
    user_message = (
        f"{style_hint}\n\nAdd comments to the following Python code:\n\n{source_code}"
    )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4096,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_message},
            ],
        )
        raw_text = response.choices[0].message.content
    except Exception as exc:
        logger.exception("Groq API call failed")
        raise CommenterError(f"AI generation failed: {exc}") from exc

    cleaned = _strip_code_fences(raw_text)

    if _looks_empty_or_invalid(cleaned):
        raise CommenterError("The AI returned an empty response. Please try again.")

    return cleaned