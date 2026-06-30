"""
model_loader.py
----------------
Responsible for locating and loading the local GGUF model exactly once.

The model is loaded as a module-level singleton so that repeated requests
to the Flask app never trigger a reload of the (large) model weights.
"""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# Name of the GGUF file we expect inside llama_weights/
MODEL_FILENAME = "llama-2-7b-chat.Q4_K_M.gguf"

# Project root is two levels up from this file (project/ai/model_loader.py -> project/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "llama_weights"
MODEL_PATH = MODEL_DIR / MODEL_FILENAME

# Generation / context settings tuned for stable, deterministic-ish output
DEFAULT_N_CTX = 4096
DEFAULT_N_THREADS = None  # let llama.cpp auto-detect
DEFAULT_N_GPU_LAYERS = 0  # CPU-only by default; user can raise this if they have GPU support compiled in


class ModelLoadError(RuntimeError):
    """Raised when the local LLM could not be located or loaded."""


class _ModelSingleton:
    """Thread-safe lazy singleton wrapper around llama_cpp.Llama."""

    _instance = None
    _lock = Lock()

    def __init__(self) -> None:
        self._llm = None
        self._load_error: Optional[str] = None

    @classmethod
    def get(cls) -> "_ModelSingleton":
        with cls._lock:
            if cls._instance is None:
                cls._instance = _ModelSingleton()
        return cls._instance

    def ensure_loaded(self):
        """Loads the model on first call. Subsequent calls are no-ops."""
        if self._llm is not None:
            return self._llm
        if self._load_error is not None:
            # We already tried and failed; don't keep retrying on every request.
            raise ModelLoadError(self._load_error)

        with self._lock:
            if self._llm is not None:
                return self._llm

            if not MODEL_PATH.exists():
                self._load_error = (
                    f"Model file not found at '{MODEL_PATH}'. "
                    f"Please place '{MODEL_FILENAME}' inside the 'llama_weights/' folder."
                )
                raise ModelLoadError(self._load_error)

            try:
                from llama_cpp import Llama
            except ImportError as exc:
                self._load_error = (
                    "llama-cpp-python is not installed. Run 'pip install llama-cpp-python'."
                )
                raise ModelLoadError(self._load_error) from exc

            try:
                logger.info("Loading local LLM from %s ...", MODEL_PATH)
                self._llm = Llama(
                    model_path=str(MODEL_PATH),
                    n_ctx=DEFAULT_N_CTX,
                    n_threads=DEFAULT_N_THREADS,
                    n_gpu_layers=DEFAULT_N_GPU_LAYERS,
                    verbose=False,
                )
                logger.info("Model loaded successfully.")
            except Exception as exc:  # noqa: BLE001 - we want to wrap any backend error
                self._load_error = f"Failed to load model: {exc}"
                self._llm = None
                raise ModelLoadError(self._load_error) from exc

        return self._llm

    @property
    def is_loaded(self) -> bool:
        return self._llm is not None

    @property
    def last_error(self) -> Optional[str]:
        return self._load_error


def get_model():
    """
    Public accessor used by the rest of the application.

    Returns the loaded llama_cpp.Llama instance.
    Raises ModelLoadError if the model is missing or fails to load.
    """
    return _ModelSingleton.get().ensure_loaded()


def model_status() -> dict:
    """Returns a small dict describing whether the model is ready, useful for health checks."""
    singleton = _ModelSingleton.get()
    return {
        "loaded": singleton.is_loaded,
        "model_path": str(MODEL_PATH),
        "error": singleton.last_error,
    }
