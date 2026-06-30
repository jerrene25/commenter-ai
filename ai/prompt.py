"""
prompt.py
---------
Builds the prompt sent to the local LLM. Keeping prompt construction in its
own module makes it easy to tune wording, add comment-style variants
(beginner/intermediate/advanced), or swap models later without touching
the calling code.
"""

from __future__ import annotations

import re

SYSTEM_INSTRUCTIONS = """You are a code-commenting engine, not a chat assistant. You never speak
to the user, never explain yourself, and never acknowledge requests in words.

Your ONLY function: take the Python code you are given and output the EXACT same
code with helpful comments inserted above relevant lines or logical blocks
(imports, functions, classes, loops, conditionals, try/except blocks, list
comprehensions, lambdas, decorators, generators, recursive calls, pandas/numpy
operations, and OOP constructs).

Rules you must follow exactly:
1. Do NOT change any code, logic, variable names, or formatting.
2. Do NOT remove existing code.
3. Comments must explain WHY the code exists and WHAT it accomplishes -
   never simply restate the syntax (e.g. never write "# assign value to x").
4. Comments must be concise (ideally one line, rarely two).
5. Do NOT repeat the same comment twice.
6. Do NOT wrap the output in markdown or code fences (no ``` characters).
7. Output ONLY raw Python source code. No greetings, no sign-offs, no
   "Here is your code", no questions, no notes after the code, nothing in
   natural language at all - not even a single word.
8. Stop generating the instant the last line of code is written.
"""

COMMENT_STYLE_HINTS = {
    "beginner": "Write comments simple enough for someone new to programming.",
    "intermediate": "Write comments for someone comfortable with Python basics but new to this codebase.",
    "advanced": "Write concise comments focused on intent, edge cases, and design decisions.",
}

# A single worked example shown as a fake prior turn. This does more to
# suppress chatty preamble/postamble than instruction text alone, since the
# model is pattern-matching the shape of the conversation, not parsing rules.
FEW_SHOT_USER = "Add comments to the following Python code:\n\ndef add(a, b):\n    return a + b\n"
FEW_SHOT_ASSISTANT = (
    "# Simple addition helper used wherever two numeric inputs need combining\n"
    "def add(a, b):\n"
    "    return a + b"
)

# Patterns for stripping stray conversational text the model adds despite
# instructions (small/local models rarely hit 100% compliance on this).
_PREAMBLE_PATTERNS = [
    r"^\s*(sure|okay|ok|here(?:'s| is)|certainly|of course|i'd be happy)[^\n]*\n+",
]
_POSTAMBLE_PATTERNS = [
    r"\n+\s*(i hope this helps|let me know|hope this helps|do you want|feel free)[^\n]*\.?\s*$",
]


def build_comment_prompt(source_code: str, style: str = "intermediate") -> str:
    """
    Builds the full prompt string for the chat-style Llama-2 model.

    Parameters
    ----------
    source_code: the raw Python source submitted by the user
    style: one of "beginner" | "intermediate" | "advanced" - reserved for
           future scalability as described in the project spec.
    """
    style_hint = COMMENT_STYLE_HINTS.get(style, COMMENT_STYLE_HINTS["intermediate"])

    # Llama-2-chat models expect a [INST] ... [/INST] instruction format.
    # The few-shot pair is embedded as a fake prior turn so the model
    # continues the *pattern* (code in, code out) instead of starting a
    # fresh conversational reply.
    prompt = (
        "[INST] <<SYS>>\n"
        f"{SYSTEM_INSTRUCTIONS}\n{style_hint}\n"
        "<</SYS>>\n\n"
        f"{FEW_SHOT_USER}"
        "[/INST] "
        f"{FEW_SHOT_ASSISTANT} </s>"
        "<s>[INST] Add comments to the following Python code:\n\n"
        f"{source_code}\n"
        "[/INST] "
        # Pre-filling the start of the assistant turn with a comment marker
        # makes it structurally impossible for the model to open with prose
        # like "Sure, here's the code" - it's already mid-comment.
        "#"
    )
    return prompt


def clean_model_output(raw_output: str, prefill: str = "#") -> str:
    """
    Strips any stray conversational text the model adds despite instructions.

    Call this on whatever the model returns before showing it to the user
    or writing it to a file. The prefill character used in build_comment_prompt
    is re-attached here since most inference servers don't echo it back.
    """
    text = raw_output.strip()

    # Re-attach the prefill character if the server doesn't echo it back.
    if prefill and not text.startswith(prefill):
        text = prefill + text

    # Strip markdown code fences if the model added them anyway.
    text = re.sub(r"^\s*```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)

    # Strip leading conversational preamble (case-insensitive, multiline).
    for pattern in _PREAMBLE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Strip trailing conversational sign-off.
    for pattern in _POSTAMBLE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip("\n")