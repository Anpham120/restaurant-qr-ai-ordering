from __future__ import annotations

from fastapi import FastAPI

from app.config import load_config
from app.schemas import ChatRequest, RagSearchRequest
from app.services.assistant import AiAssistantService


config = load_config()
assistant = AiAssistantService(config)
app = FastAPI(title="CMC Restaurant Python AI Service", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "status": "Healthy",
        "service": "cmc-restaurant-ai",
        "provider": config.provider,
        "model": config.model,
        "llm_enabled": config.llm_enabled,
        "retrieval_method": assistant.retrieval_method,
    }


@app.post("/v1/rag/search")
def rag_search(request: RagSearchRequest) -> dict:
    return {"results": assistant.search(request.query, request.top_k)}


@app.post("/v1/chat")
async def chat(request: ChatRequest) -> dict:
    return await assistant.chat(request.model_dump())


@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest) -> dict:
    """Streaming endpoint stub — currently returns the standard JSON response."""
    return await assistant.chat(request.model_dump())


@app.post("/v1/cache/invalidate")
def invalidate_cache() -> dict:
    assistant.invalidate_cache()
    return {"status": "ok", "cache": assistant.cache_stats}
