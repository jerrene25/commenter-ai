"""
lint_service.py
----------------
Performs static analysis on submitted Python code, completely independently
of the AI model. Combines:

- `ast` based syntax validation
- `pyflakes` for undefined names / unused imports / common mistakes
  (pyflakes is fast, has no config overhead, and is a natural fit for a
  lightweight "errors panel").

Results are returned as a structured list of dicts so the frontend can
render them in a dedicated errors panel rather than splicing them into code.
"""

from __future__ import annotations

import ast
import io
from contextlib import redirect_stdout
from typing import List, TypedDict


class LintIssue(TypedDict):
    line: int
    column: int
    message: str
    severity: str  # "error" | "warning"
    source: str  # "syntax" | "pyflakes"


def _check_syntax(source_code: str) -> List[LintIssue]:
    """Uses the ast module to catch hard syntax errors before anything else runs."""
    issues: List[LintIssue] = []
    try:
        ast.parse(source_code)
    except SyntaxError as exc:
        issues.append(
            LintIssue(
                line=exc.lineno or 0,
                column=exc.offset or 0,
                message=f"SyntaxError: {exc.msg}",
                severity="error",
                source="syntax",
            )
        )
    return issues


def _check_pyflakes(source_code: str) -> List[LintIssue]:
    """
    Runs pyflakes against the source and parses its textual report into
    structured issues. Pyflakes catches undefined names, unused imports,
    redefinitions, and several other common mistakes.
    """
    issues: List[LintIssue] = []
    try:
        from pyflakes.api import check
        from pyflakes.reporter import Reporter
    except ImportError:
        # pyflakes is an optional but recommended dependency; degrade gracefully.
        issues.append(
            LintIssue(
                line=0,
                column=0,
                message="pyflakes is not installed; only basic syntax checking is available.",
                severity="warning",
                source="pyflakes",
            )
        )
        return issues

    out, err = io.StringIO(), io.StringIO()
    reporter = Reporter(out, err)

    with redirect_stdout(io.StringIO()):
        check(source_code, "submitted_code.py", reporter)

    for stream, severity in ((out, "warning"), (err, "error")):
        for line in stream.getvalue().splitlines():
            issues.append(_parse_pyflakes_line(line, severity))

    return [i for i in issues if i is not None]


def _parse_pyflakes_line(line: str, severity: str) -> LintIssue:
    """
    Pyflakes lines look like: 'submitted_code.py:12:5 undefined name 'foo''
    We parse out the line/column best-effort; if parsing fails we still
    surface the raw message rather than dropping it silently.
    """
    try:
        _, lineno_str, rest = line.split(":", 2)
        if ":" in rest:
            col_str, message = rest.split(":", 1) if rest.split(":", 1)[0].strip().isdigit() else ("0", rest)
        else:
            col_str, message = "0", rest
        return LintIssue(
            line=int(lineno_str.strip()) if lineno_str.strip().isdigit() else 0,
            column=int(col_str.strip()) if col_str.strip().isdigit() else 0,
            message=message.strip(),
            severity=severity,
            source="pyflakes",
        )
    except Exception:  # noqa: BLE001 - never let a parsing quirk break linting
        return LintIssue(line=0, column=0, message=line.strip(), severity=severity, source="pyflakes")


def lint_code(source_code: str) -> List[LintIssue]:
    """
    Public entry point. Returns a combined, de-duplicated list of issues.
    If there's a hard syntax error, pyflakes is skipped since it can't
    meaningfully parse broken code either.
    """
    if source_code is None or source_code.strip() == "":
        return []

    syntax_issues = _check_syntax(source_code)
    if syntax_issues:
        return syntax_issues

    return _check_pyflakes(source_code)
