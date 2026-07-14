from __future__ import annotations

import logging

from app.clients.gemini import GeminiClient
from app.config import AiServiceConfig
from app.rag.confidence import compute_retrieval_confidence
from app.rag.conversation_policy import (
    build_conversation_policy,
    enforce_suggestion_policy,
)
from app.rag.embedding_retriever import EmbeddingEncoder
from app.rag.guardrails import detect_guardrail_flags
from app.rag.knowledge_base import load_markdown_knowledge_base
from app.rag.menu_grounding import MenuCandidateRetriever
from app.rag.output_parser import parse_model_response
from app.rag.prompts import build_fallback_answer, build_messages
from app.rag.query_rewriter import rewrite_query
from app.rag.response_cache import ResponseCache
from app.rag.retrieval_factory import build_retriever_stack
from app.rag.retriever import BM25Retriever, Retriever
from app.schemas import ChatResponse, RetrievedSource


logger = logging.getLogger(__name__)


class AiAssistantService:
    def __init__(
        self,
        config: AiServiceConfig,
        *,
        llm_client: GeminiClient | None = None,
        embedding_encoder: EmbeddingEncoder | None = None,
    ) -> None:
        self._config = config
        self._chunks = load_markdown_knowledge_base(config.knowledge_base_path)
        self._retriever, encoder = self._build_retriever(embedding_encoder)
        self._menu_retriever = MenuCandidateRetriever(
            "bm25" if self._retrieval_method.startswith("bm25") else config.retrieval_method,
            encoder=encoder,
        )
        self._client = llm_client
        if self._client is None and config.llm_enabled:
            self._client = GeminiClient(
                config.base_url,
                config.api_key,
                config.model,
                config.timeout_seconds,
                config.max_retry,
            )
        self._cache = ResponseCache(max_size=500, ttl_seconds=300)

    @property
    def retrieval_method(self) -> str:
        return self._retrieval_method

    def _build_retriever(
        self,
        embedding_encoder: EmbeddingEncoder | None,
    ) -> tuple[Retriever, EmbeddingEncoder | None]:
        try:
            stack = build_retriever_stack(
                self._chunks,
                self._config.retrieval_method,
                encoder=embedding_encoder,
            )
            self._retrieval_method = stack.method
            return stack.retriever, stack.encoder
        except Exception as exception:
            logger.exception(
                "Dense retrieval unavailable; using BM25 fallback requested_method=%s error_type=%s",
                self._config.retrieval_method,
                type(exception).__name__,
            )
            self._retrieval_method = "bm25-fallback"
            return BM25Retriever(self._chunks), None

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

    @property
    def cache_stats(self) -> dict:
        """Return response cache statistics."""
        return self._cache.stats

    async def chat(self, payload: dict) -> dict:
        message = str(payload.get("message") or "").strip()
        history = payload.get("history") or []
        session_memory = str(payload.get("session_memory") or "").strip()
        menu_items = payload.get("menu_items") or []
        policy = build_conversation_policy(message, history, session_memory, menu_items)
        candidate_menu_items = self._menu_retriever.select(
            message,
            menu_items,
            excluded_ids=policy.excluded_menu_item_ids,
        )

        # Query rewriting for better retrieval (includes normalization + intent)
        rewritten = rewrite_query(message, history)
        search_query = rewritten if rewritten != message else message
        logger.debug("Query rewrite: %r -> %r", message, search_query)

        retrieved = self._retriever.search(search_query, self._config.top_k)

        # Intent-based re-ranking: boost results matching intent source hints
        from app.rag.intent_classifier import classify_intent
        intent = classify_intent(message)
        if intent.source_hints and intent.confidence >= 0.1:
            retrieved = _rerank_by_intent(retrieved, intent.source_hints)
            logger.debug(
                "Intent rerank: intent=%s conf=%.2f sources=%s",
                intent.intent, intent.confidence, intent.source_hints,
            )

        chunks = [item.chunk for item in retrieved]
        flags = detect_guardrail_flags(message)

        # Retrieval confidence check
        confidence = compute_retrieval_confidence(retrieved)
        if confidence.guardrail_flag:
            flags = _dedupe([*flags, confidence.guardrail_flag])
        logger.debug(
            "Retrieval confidence: score=%.3f level=%s reason=%s",
            confidence.score, confidence.level, confidence.reason,
        )

        # Response cache check
        source_ids = [item.chunk.source for item in retrieved[:3]]
        cached = self._cache.get(message, source_ids)
        if cached is not None:
            logger.debug("Cache hit for query: %r", message)
            return cached
        provider_available = False
        answer: str | None = None
        suggested_actions: list[dict] = []

        if self._client is not None:
            try:
                raw_answer = await self._client.complete(
                    build_messages(
                        message,
                        chunks,
                        candidate_menu_items,
                        history,
                        table_code=payload.get("table_code"),
                        session_memory=session_memory,
                        max_suggestions=policy.max_suggestions,
                        requested_count=policy.requested_count,
                        excluded_menu_item_ids=policy.excluded_menu_item_ids,
                    )
                )
                parsed = parse_model_response(
                    raw_answer,
                    candidate_menu_items,
                    excluded_menu_item_ids=policy.excluded_menu_item_ids,
                    max_actions=policy.max_suggestions,
                )
                if parsed is None:
                    flags = _dedupe([*flags, "AI_OUTPUT_SCHEMA_INVALID"])
                else:
                    answer = parsed.content
                    suggested_actions = enforce_suggestion_policy(
                        parsed.suggested_cart_actions,
                        candidate_menu_items,
                        policy,
                    )
                    flags = _dedupe([*flags, *parsed.guardrail_flags])
                    if suggested_actions:
                        flags = _dedupe([*flags, "CUSTOMER_CONFIRMATION_REQUIRED"])
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

        response = ChatResponse(
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

        # Cache successful responses
        if provider_available:
            self._cache.put(message, source_ids, response)

        return response


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _rerank_by_intent(
    results: list,
    source_hints: tuple[str, ...],
    boost_factor: float = 2.0,
) -> list:
    """Re-rank retrieval results by boosting scores of intent-matching sources.

    Results from source_hints get their score multiplied by boost_factor,
    then re-sorted. Additionally, ensures at least one hint-source result
    appears in top-3 by promoting it if needed.
    """
    if not source_hints or not results:
        return results

    hint_set = set(source_hints)

    # Separate hint-matching and non-matching results
    hint_results = [r for r in results if r.chunk.source in hint_set]
    other_results = [r for r in results if r.chunk.source not in hint_set]

    if not hint_results:
        return results

    # Strategy: interleave — put best hint result first, then alternate
    # This guarantees at least 1 hint source in top-3
    hint_results.sort(key=lambda r: r.score, reverse=True)
    other_results.sort(key=lambda r: r.score, reverse=True)

    merged = []
    hi, oi = 0, 0
    # First slot: best hint result (guaranteed)
    if hi < len(hint_results):
        merged.append(hint_results[hi])
        hi += 1
    # Remaining slots: alternate other/hint by score
    while hi < len(hint_results) or oi < len(other_results):
        if oi < len(other_results):
            merged.append(other_results[oi])
            oi += 1
        if hi < len(hint_results):
            merged.append(hint_results[hi])
            hi += 1

    return merged
