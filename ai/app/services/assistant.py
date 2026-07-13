from __future__ import annotations

import logging

from app.clients.gemini import GeminiClient
from app.config import AiServiceConfig
from app.rag.guardrails import detect_guardrail_flags
from app.rag.knowledge_base import load_markdown_knowledge_base
from app.rag.output_parser import parse_model_response
from app.rag.prompts import build_fallback_answer, build_messages
from app.rag.retriever import LexicalRetriever
from app.schemas import ChatResponse, RetrievedSource


logger = logging.getLogger(__name__)


class AiAssistantService:
    def __init__(self, config: AiServiceConfig) -> None:
        self._config = config
        self._chunks = load_markdown_knowledge_base(config.knowledge_base_path)
        self._retriever = LexicalRetriever(self._chunks)

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        results = self._retriever.search(query, top_k or self._config.top_k)
        return [
            {
                "source": item.chunk.source,
                "title": item.chunk.title,
                "content": item.chunk.content,
                "score": item.score,
                "tags": list(item.chunk.tags),
            }
            for item in results
        ]

    async def chat(self, payload: dict) -> dict:
        message = str(payload.get("message") or "").strip()
        history = payload.get("history") or []
        session_memory = str(payload.get("session_memory") or "").strip()
        menu_items = payload.get("menu_items") or []
        retrieved = self._retriever.search(message, self._config.top_k)
        chunks = [item.chunk for item in retrieved]
        flags = detect_guardrail_flags(message)
        provider_available = False
        answer: str | None = None
        suggested_actions: list[dict] = []

        if self._config.llm_enabled:
            client = GeminiClient(
                self._config.base_url,
                self._config.api_key,
                self._config.model,
                self._config.timeout_seconds,
            )
            try:
                raw_answer = await client.complete(
                    build_messages(message, chunks, menu_items, history, session_memory=session_memory)
                )
                parsed = parse_model_response(raw_answer, menu_items)
                if parsed is None:
                    flags = _dedupe([*flags, "AI_OUTPUT_SCHEMA_INVALID"])
                else:
                    answer = parsed.content
                    suggested_actions = parsed.suggested_cart_actions
                    flags = _dedupe([*flags, *parsed.guardrail_flags])
                    provider_available = True
            except Exception as exception:
                logger.exception(
                    "AI provider request failed provider=%s model=%s error_type=%s",
                    self._config.provider,
                    self._config.model,
                    type(exception).__name__,
                )
                flags = _dedupe([*flags, "AI_PROVIDER_UNAVAILABLE"])

        if not answer:
            answer = build_fallback_answer(message, chunks)

        return ChatResponse(
            content=answer,
            provider_available=provider_available,
            model=self._config.model,
            retrieved_sources=[
                RetrievedSource(
                    source=item.chunk.source,
                    title=item.chunk.title,
                    score=item.score,
                )
                for item in retrieved
            ],
            guardrail_flags=flags,
            suggested_cart_actions=suggested_actions,
        ).model_dump()


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
