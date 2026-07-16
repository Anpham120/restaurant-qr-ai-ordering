FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ai ./ai
WORKDIR /app/ai

ENV AI_SERVICE_HOST=0.0.0.0
ENV AI_SERVICE_PORT=8001

CMD ["sh", "-c", "uvicorn app.main:app --host ${AI_SERVICE_HOST:-127.0.0.1} --port ${AI_SERVICE_PORT:-8001}"]
