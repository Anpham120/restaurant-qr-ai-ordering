FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && chown -R app:app /app

COPY --chown=app:app ai ./ai
WORKDIR /app/ai

ENV AI_SERVICE_HOST=0.0.0.0
ENV AI_SERVICE_PORT=8001

USER app
CMD ["sh", "-c", "uvicorn app.main:app --host ${AI_SERVICE_HOST:-127.0.0.1} --port ${AI_SERVICE_PORT:-8001}"]
