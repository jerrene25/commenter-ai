"""
download_model.py
------------------
Runs once at container startup (not build time) to fetch the GGUF model
if it isn't already present on disk. Keeps the Docker build itself fast
and avoids hitting Hugging Face Spaces' build timeout.
"""
from pathlib import Path
from huggingface_hub import hf_hub_download

MODEL_DIR = Path("llama_weights")
MODEL_FILENAME = "llama-2-7b-chat.Q4_K_M.gguf"
MODEL_PATH = MODEL_DIR / MODEL_FILENAME

MODEL_DIR.mkdir(exist_ok=True)

if MODEL_PATH.exists():
    print(f"Model already present at {MODEL_PATH}, skipping download.")
else:
    print("Downloading model, this may take a few minutes...")
    hf_hub_download(
        repo_id="TheBloke/Llama-2-7B-Chat-GGUF",
        filename=MODEL_FILENAME,
        local_dir=str(MODEL_DIR),
        local_dir_use_symlinks=False,
    )
    print("Model download complete.")