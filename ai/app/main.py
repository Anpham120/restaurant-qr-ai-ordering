from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request

from app.clients.nine_router import NineRouterClient
from app.config import load_config
from app.domain import MenuItemContext as DomainMenuItemContext
from app.retrieval.service import RetrievalService
from app.schemas import ChatRequest, RagSearchRequest
from app.services.assistant import AiAssistantService


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    timeout = httpx.Timeout(config.timeout_seconds, connect=min(2.0, config.timeout_seconds))
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, trust_env=False) as http_client:
        retrieval = RetrievalService(
            policies_path=config.policies_path,
            production_config_path=config.production_config_path,
            embedding_cache=config.embedding_cache_path,
            embedding_model_path=config.embedding_model_path,
        )
        client = (
            NineRouterClient(
                http_client=http_client,
                base_url=config.base_url,
                api_key=config.api_key,
                model=config.model,
                max_output_tokens=config.max_output_tokens,
            )
            if config.llm_enabled
            else None
        )
        app.state.config = config
        app.state.assistant = AiAssistantService(config, retrieval, client)
        yield


app = FastAPI(title="CMC Restaurant Academic Chatbot Service", version="2.0.0", lifespan=lifespan)


@app.get("/health")
def health(request: Request) -> dict:
    config = request.app.state.config
    assistant = request.app.state.assistant
    return {
        "status": "Healthy",
        "service": "cmc-restaurant-ai",
        "version": "2.0.0",
        "provider": config.provider,
        "model": config.model,
        "llm_enabled": config.llm_enabled,
        "retrieval_method": assistant._retrieval.method,
    }


@app.post("/v1/retrieval/search")
def retrieval_search(request: RagSearchRequest, http_request: Request) -> dict:
    assistant: AiAssistantService = http_request.app.state.assistant
    menu_items = [DomainMenuItemContext.from_mapping(item.model_dump()) for item in request.menu_items]
    return {
        "query": request.query,
        "retrieval_method": assistant._retrieval.method,
        "results": assistant.search(request.query, menu_items, request.top_k),
    }


@app.post("/v1/chat")
async def chat(request: ChatRequest, http_request: Request) -> dict:
    assistant: AiAssistantService = http_request.app.state.assistant
    return await assistant.chat(request.model_dump())
