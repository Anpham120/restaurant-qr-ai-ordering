from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

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
    logger.info(
        "AI service ready retrieval=%s model=%s pipeline_profile=%s",
        assistant.retrieval_method,
        config.model,
        config.pipeline_profile,
    )
    yield
    await _http_client.aclose()
    _http_client = None


app = FastAPI(title="CMC Restaurant Python AI Service", version="0.2.0", lifespan=lifespan)


def require_internal_token(authorization: str = Header(default="")) -> None:
    if not config.internal_token:
        raise HTTPException(status_code=503, detail="AI internal authentication is not configured")
    expected = f"Bearer {config.internal_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid AI internal token")


@app.get("/health")
def health() -> dict:
    return {
        "status": "Healthy",
        "service": "cmc-restaurant-ai",
        "provider": config.provider,
        "model": config.model,
        "llm_enabled": config.llm_enabled,
        "provider_configured": config.llm_enabled,
        "pipeline": config.pipeline_version,
        "pipeline_profile": config.pipeline_profile,
        "rag_config_id": config.rag_config_id,
        "retrieval_method": assistant.retrieval_method if assistant else "starting",
        "ready": assistant.is_ready if assistant else False,
    }


@app.get("/ready")
def ready() -> JSONResponse:
    dependencies = {
        "retriever": {
            "ready": bool(assistant is not None and assistant.is_ready),
            "method": assistant.retrieval_method if assistant is not None else "starting",
        },
        "provider_config": {
            "ready": config.llm_enabled,
            "provider": config.provider,
            "model": config.model,
        },
        "internal_auth": {"ready": bool(config.internal_token)},
    }
    is_ready = all(item["ready"] for item in dependencies.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "ready": is_ready,
            "dependencies": dependencies,
            "pipeline": config.pipeline_version,
            "pipeline_profile": config.pipeline_profile,
            "model": config.model,
            "rag_config_id": config.rag_config_id,
        },
    )


@app.post("/v1/rag/search", dependencies=[Depends(require_internal_token)])
def rag_search(request: RagSearchRequest) -> dict:
    assert assistant is not None
    return {"results": assistant.search(request.query, request.top_k)}


@app.post("/v1/chat", dependencies=[Depends(require_internal_token)])
async def chat(request: ChatRequest) -> dict:
    assert assistant is not None
    try:
        async with asyncio.timeout(config.request_budget_seconds):
            return await assistant.chat(request.model_dump())
    except TimeoutError:
        return _build_timeout_response(request)


@app.post("/v1/chat/stream", dependencies=[Depends(require_internal_token)])
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
            payload = _build_timeout_response(request)
            yield f"event: token\ndata: {json.dumps({'text': payload['content']}, ensure_ascii=False)}\n\n"
            yield f"event: final\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps({'ok': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _build_timeout_response(request: ChatRequest) -> dict:
    state = request.session_state
    rolling_summary = state.rolling_summary or request.rolling_summary or None
    session_updates = {
        "facts": list(state.facts),
        "constraints": dict(state.constraints),
        "referenced_menu_item_ids": list(state.referenced_menu_item_ids),
        "suggested_menu_item_ids": list(state.suggested_menu_item_ids),
        "rejected_menu_item_ids": list(state.rejected_menu_item_ids),
        "accepted_menu_item_ids": list(state.accepted_menu_item_ids),
        "added_to_cart_menu_item_ids": list(state.added_to_cart_menu_item_ids),
        "rolling_summary": rolling_summary,
        "memory_version": state.memory_version,
        "conversation_frame": state.conversation_frame.model_dump(),
    }
    return {
        "contract_version": "v2",
        "content": "Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé.",
        "provider_available": False,
        "provider_status": "unavailable",
        "model": config.model,
        "pipeline_version": config.pipeline_version,
        "pipeline_profile": config.pipeline_profile,
        "resolved_menu_item_ids": [],
        "verifier_result": "not_applicable",
        "retrieved_sources": [],
        "decision": {
            "intent": None,
            "route": "abstain",
            "confidence": 0.0,
            "evidence_sufficient": False,
            "abstain_reason": "request_budget_exceeded",
        },
        "evidence": [],
        "claims": [],
        "session_updates": session_updates,
        "updated_rolling_summary": rolling_summary,
        "guardrail_flags": ["AI_PROVIDER_UNAVAILABLE", "EVIDENCE_INSUFFICIENT"],
        "suggested_cart_actions": [],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": True,
        "latency_ms": {
            "total": config.request_budget_seconds * 1000,
            "path": "budget_exceeded",
        },
    }


@app.post("/v1/cache/invalidate", dependencies=[Depends(require_internal_token)])
def invalidate_cache() -> dict:
    assert assistant is not None
    assistant.invalidate_cache()
    return {"status": "ok", "cache": assistant.cache_stats}
