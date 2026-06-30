"""
prompt.py
---------
Builds the prompt sent to the local LLM. Keeping prompt construction in its
own module makes it easy to tune wording, add comment-style variants
(beginner/intermediate/advanced), or swap models later without touching
the calling code.
"""

from __future__ import annotations

SYSTEM_INSTRUCTIONS = """You are a senior Python software engineer performing a careful code review.

Your ONLY job is to take the Python code you are given and return the EXACT
same code with helpful comments inserted above relevant lines or logical
blocks (imports, functions, classes, loops, conditionals, try/except blocks,
list comprehensions, lambdas, decorators, generators, recursive calls,
pandas/numpy operations, and OOP constructs).

Rules you must follow exactly:
1. Do NOT change any code, logic, variable names, or formatting.
2. Do NOT remove existing code.
3. Comments must explain WHY the code exists and WHAT it accomplishes -
   never simply restate the syntax (e.g. never write "# assign value to x").
4. Comments must be concise (ideally one line, rarely two).
5. Do NOT repeat the same comment twice.
6. Do NOT wrap the output in markdown or code fences (no ``` characters).
7. Do NOT add any explanation, summary, or text outside of the code itself.
8. Return ONLY the fully commented Python code, nothing else.
9. Stop as soon as the commented code is complete. Do not continue generating.
"""

COMMENT_STYLE_HINTS = {
    "beginner": "Write comments simple enough for someone new to programming.",
    "intermediate": "Write comments for someone comfortable with Python basics but new to this codebase.",
    "advanced": "Write concise comments focused on intent, edge cases, and design decisions.",
}


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
    prompt = (
        "[INST] <<SYS>>\n"
        f"{SYSTEM_INSTRUCTIONS}\n{style_hint}\n"
        "<</SYS>>\n\n"
        "Add comments to the following Python code:\n\n"
        f"{source_code}\n"
        "[/INST]"
    )
    return prompt
