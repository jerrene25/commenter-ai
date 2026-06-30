---
title: Commentary AI Code Commenter
emoji: robot_face
colorFrom: blue
colorTo: gray
sdk: docker
app_file: app.py
pinned: false
---

# Commentary - AI Python Code Auto-Commenter

Commentary takes Python source code and returns it with AI-generated comments inserted above relevant lines and logical blocks. It runs entirely on a local LLM via llama-cpp-python.

## Features

- Paste code or upload a .py file
- AI comments explain why code exists, not just what it says
- Separate Errors and Lint panel powered by ast and pyflakes
- Syntax-highlighted input/output editors, dark theme
- Copy or download the commented result

## Project structure

```
project/
│
├── app.py                  # Flask routes only — no business logic here
├── ai/
│   ├── model_loader.py     # Locates + loads the GGUF model once (singleton)
│   ├── prompt.py           # Builds the senior-engineer system prompt
│   └── commenter.py        # Calls the model, cleans up its output
│
├── services/
│   ├── lint_service.py     # ast + pyflakes static analysis
│   └── parser.py           # Input validation / normalization
│
├── templates/index.html
├── static/{style.css, script.js}
├── uploads/                # Scratch space (empty by default)
├── llama_weights/          # Put your .gguf model here
├── requirements.txt
└── .gitignore
```

## Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   `llama-cpp-python` compiles a native extension on install. If you hit
   build errors, see the project's docs for platform-specific wheels
   (CPU-only wheels are usually sufficient for this app).

2. **Download the model.**

   This app expects `llama-2-7b-chat.Q4_K_M.gguf` inside the `llama_weights/`
   folder:

   ```
   project/llama_weights/llama-2-7b-chat.Q4_K_M.gguf
   ```

   You can obtain this GGUF file from a model hub such as Hugging Face
   (search for "llama-2-7b-chat GGUF", quantization `Q4_K_M`). The app
   resolves this path relative to the project root, so it works after
   cloning on any machine — no absolute paths required.

3. **Run the app:**

   ```bash
   python app.py
   ```

   Then open `http://localhost:5000` in your browser.

   The model loads lazily on the first `/comment` request and stays in
   memory afterward (a global singleton), so subsequent requests are fast.
   You can check load status anytime via `GET /health`.

## API

### `GET /health`
Health check. Returns whether the model is loaded.

```json
{ "success": true, "status": "ok", "model": { "loaded": true, "model_path": "...", "error": null } }
```

### `POST /comment`
Body (JSON): `{ "code": "...", "style": "intermediate" }`
or multipart form-data with a `file` field containing a `.py` upload.

```json
{ "success": true, "commented_code": "# ...\nimport os\n..." }
```

### `POST /lint`
Same input shape as `/comment`. Returns static analysis issues, independent
of the AI model.

```json
{
  "success": true,
  "issues": [
    { "line": 4, "column": 1, "message": "undefined name 'foo'", "severity": "error", "source": "pyflakes" }
  ]
}
```

All endpoints return `{"success": false, "error": "..."}` with an
appropriate HTTP status code on failure — empty input, invalid Python,
oversized uploads, or a missing/unloadable model never crash the server.

## Notes on quality

- Generation uses a low temperature (0.2) and a repetition penalty so
  comments stay grounded and don't loop.
- The model is explicitly instructed not to alter code, not to wrap output
  in markdown fences, and to stop once the commented code is complete; the
  backend also strips any stray code fences defensively.
- Static analysis never gets merged into the AI output — it's always
  rendered in its own panel, sourced independently from `ast`/`pyflakes`.

c.
