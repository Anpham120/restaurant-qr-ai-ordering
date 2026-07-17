from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.config import load_config
from app.schemas import ChatRequest, RagSearchRequest
from app.services.assistant import AiAssistantService


logger = logging.getLogger(__name__)
config = load_config()
_http_client: httpx.AsyncClient | None = None
assistant: AiAssistantService | None = None


def _configure_threading() -> None:
    thread_count = int(os.getenv("OMP_NUM_THREADS", "4"))
    os.environ.setdefault("OMP_NUM_THREADS", str(thread_count))
    try:
        import torch

        torch.set_num_threads(thread_count)
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client, assistant

    _configure_threading()
    _http_client = httpx.AsyncClient(
        timeout=config.llm_timeout_seconds,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    assistant = AiAssistantService(config, http_client=_http_client)
    assistant.prewarm()
    logger.info("AI service ready retrieval=%s model=%s", assistant.retrieval_method, config.model)
    yield
    await _http_client.aclose()
    _http_client = None


app = FastAPI(title="CMC Restaurant Python AI Service", version="0.2.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {
        "status": "Healthy",
        "service": "cmc-restaurant-ai",
        "provider": config.provider,
        "model": config.model,
        "llm_enabled": config.llm_enabled,
        "retrieval_method": assistant.retrieval_method if assistant else "starting",
        "ready": assistant.is_ready if assistant else False,
    }


@app.get("/ready")
def ready() -> dict:
    if assistant is None or not assistant.is_ready:
        return {"status": "starting", "ready": False}
    return {"status": "ready", "ready": True}


@app.post("/v1/rag/search")
def rag_search(request: RagSearchRequest) -> dict:
    assert assistant is not None
    return {"results": assistant.search(request.query, request.top_k)}


@app.post("/v1/chat")
async def chat(request: ChatRequest) -> dict:
    assert assistant is not None
    try:
        async with asyncio.timeout(config.request_budget_seconds):
            return await assistant.chat(request.model_dump())
    except TimeoutError:
        return {
            "content": "Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé.",
            "provider_available": False,
            "model": config.model,
            "guardrail_flags": ["AI_PROVIDER_UNAVAILABLE"],
            "suggested_cart_actions": [],
            "follow_up": {"can_show_more": False, "remaining_count": 0},
            "suggest_staff_handoff": True,
            "latency_ms": {"total": config.request_budget_seconds * 1000, "path": "budget_exceeded"},
        }


@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    assert assistant is not None

    async def event_generator():
        try:
            async with asyncio.timeout(config.request_budget_seconds):
                async for event in assistant.chat_stream(request.model_dump()):
                    yield (
                        f"event: {event['type']}\n"
                        f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                    )
        except TimeoutError:
            payload = {
                "content": "Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé.",
                "provider_available": False,
                "model": config.model,
                "guardrail_flags": ["AI_PROVIDER_UNAVAILABLE"],
                "suggested_cart_actions": [],
                "follow_up": {"can_show_more": False, "remaining_count": 0},
                "suggest_staff_handoff": True,
            }
            yield f"event: token\ndata: {json.dumps({'text': payload['content']}, ensure_ascii=False)}\n\n"
            yield f"event: final\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps({'ok': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/v1/cache/invalidate")
def invalidate_cache() -> dict:
    assert assistant is not None
    assistant.invalidate_cache()
    return {"status": "ok", "cache": assistant.cache_stats}
