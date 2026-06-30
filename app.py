"""
app.py
------
Flask application entry point. Exposes the REST API and serves the frontend.
Business logic lives in ai/ and services/; this file only wires routes
together and handles HTTP-level concerns (request parsing, status codes,
error responses).
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from ai.commenter import CommenterError, generate_commented_code
from ai.model_loader import model_status
from services.lint_service import lint_code
from services.parser import InvalidSourceError, normalize_source, validate_uploaded_filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB upload cap


def _error_response(message: str, status_code: int = 400):
    return jsonify({"success": False, "error": message}), status_code


@app.route("/")
def index():
    """Serves the frontend and doubles as a health check when called via API clients."""
    if request.accept_mimetypes.best == "application/json":
        return jsonify({"success": True, "status": "ok", "model": model_status()})
    return render_template("index.html")


@app.route("/health")
def health():
    """Dedicated JSON health check endpoint."""
    return jsonify({"success": True, "status": "ok", "model": model_status()})


@app.route("/comment", methods=["POST"])
def comment_endpoint():
    """
    Accepts either:
      - multipart/form-data with a 'file' field (uploaded .py file), or
      - application/json with a 'code' field (pasted code)
    Returns AI-generated commented code.
    """
    style = request.form.get("style") or (request.json.get("style") if request.is_json else None) or "intermediate"

    try:
        source_code = _extract_source_from_request()
        normalized = normalize_source(source_code)
    except InvalidSourceError as exc:
        return _error_response(str(exc), 400)

    try:
        commented = generate_commented_code(normalized, style=style)
    except CommenterError as exc:
        logger.warning("Commenter error: %s", exc)
        return _error_response(str(exc), 503)
    except Exception as exc:  # noqa: BLE001 - absolute last-resort guard, app must never crash
        logger.exception("Unexpected error in /comment")
        return _error_response(f"Unexpected server error: {exc}", 500)

    return jsonify({"success": True, "commented_code": commented})


@app.route("/lint", methods=["POST"])
def lint_endpoint():
    """Returns static analysis results for the given code, separate from AI commenting."""
    try:
        source_code = _extract_source_from_request()
        normalized = normalize_source(source_code)
    except InvalidSourceError as exc:
        return _error_response(str(exc), 400)

    try:
        issues = lint_code(normalized)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /lint")
        return _error_response(f"Unexpected server error during linting: {exc}", 500)

    return jsonify({"success": True, "issues": issues})


def _extract_source_from_request() -> str:
    """
    Shared helper to pull Python source out of either an uploaded file or
    a JSON body, used by both /comment and /lint.
    """
    if "file" in request.files:
        uploaded = request.files["file"]
        validate_uploaded_filename(uploaded.filename)
        try:
            return uploaded.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidSourceError("Uploaded file is not valid UTF-8 text.") from exc

    if request.is_json:
        data = request.get_json(silent=True) or {}
        return data.get("code", "")

    # Fallback: allow plain form field 'code' too
    return request.form.get("code", "")


@app.errorhandler(413)
def handle_too_large(_exc):
    return _error_response("Uploaded file is too large (limit 2MB).", 413)


@app.errorhandler(404)
def handle_not_found(_exc):
    return _error_response("Not found.", 404)


@app.errorhandler(500)
def handle_server_error(_exc):
    logger.exception("Unhandled server error")
    return _error_response("Internal server error.", 500)


if __name__ == "__main__":
    # Touch the model status at startup (does not force-load; just logs availability)
    status = model_status()
    if not Path(status["model_path"]).exists():
        logger.warning(
            "Model file not found at %s. The /comment endpoint will return an error "
            "until the model is placed there.",
            status["model_path"],
        )
    app.run(host="0.0.0.0", port=5000, debug=True)
