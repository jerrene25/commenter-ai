FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn huggingface_hub

COPY . .

# Download the model at build time so it's baked into the Space
RUN python -c "from huggingface_hub import hf_hub_download; \
    hf_hub_download(repo_id='TheBloke/Llama-2-7B-Chat-GGUF', \
    filename='llama-2-7b-chat.Q4_K_M.gguf', \
    local_dir='llama_weights', local_dir_use_symlinks=False)"

EXPOSE 7860

CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:7860", "--timeout", "300", "app:app"]