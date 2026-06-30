FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Use prebuilt CPU wheels for llama-cpp-python to avoid compiling from source
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
RUN pip install --no-cache-dir Flask gunicorn pyflakes huggingface_hub

COPY . .

EXPOSE 7860

# Download the model at container startup, not at build time
CMD ["/bin/sh", "-c", "python download_model.py && gunicorn -w 1 -b 0.0.0.0:7860 --timeout 300 app:app"]