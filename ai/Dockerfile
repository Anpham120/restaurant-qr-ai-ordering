FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface

WORKDIR /app

COPY ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small', revision='fd1525a9fd15316a2d503bf26ab031a61d056e98', trust_remote_code=False)"

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && chown -R app:app /app

COPY --chown=app:app ai ./ai
WORKDIR /app/ai

ENV AI_SERVICE_HOST=0.0.0.0
ENV AI_SERVICE_PORT=8001
ENV HF_HUB_OFFLINE=1

USER app
CMD ["sh", "-c", "uvicorn app.main:app --host ${AI_SERVICE_HOST:-127.0.0.1} --port ${AI_SERVICE_PORT:-8001}"]
