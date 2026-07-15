from __future__ import annotations

import logging
from typing import Any

from app.clients.gemini import GeminiClient
from app.config import AiServiceConfig
from app.rag.budget_solver import solve_budget
from app.rag.confidence import compute_retrieval_confidence
from app.rag.constraint_extractor import extract_constraints, has_soft_criteria
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
from app.schemas import ChatResponse, FollowUp, RetrievedSource


logger = logging.getLogger(__name__)

FAQ_POLICY_INTENTS = frozenset(
    {
        "payment",
        "restaurant_info",
        "service",
        "promotion",
        "general",
        "ask_price",
    }
)


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

    def invalidate_cache(self) -> None:
        """Clear the response cache."""
        self._cache.invalidate()

    async def chat(self, payload: dict) -> dict:
        message = str(payload.get("message") or "").strip()
        history = payload.get("history") or []
        session_memory = str(payload.get("session_memory") or "").strip()
        rolling_summary = str(payload.get("rolling_summary") or "").strip()
        menu_items = payload.get("menu_items") or []
        session_id = str(payload.get("session_id") or "").strip()
        menu_version = str(payload.get("menu_version") or "").strip()
        facts = payload.get("facts") or []
        cart_items = payload.get("cart_items") or []
        orders = payload.get("orders") or []
        promotions = payload.get("promotions") or []
        local_time = payload.get("local_time")
        meal_period = payload.get("meal_period")

        constraints = extract_constraints(message, history)
        policy = build_conversation_policy(message, history, session_memory, menu_items)
        payload_excluded = frozenset(
            str(item_id).strip()
            for item_id in (payload.get("excluded_menu_item_ids") or [])
            if str(item_id).strip()
        )
        excluded_ids = policy.excluded_menu_item_ids | payload_excluded
        exclusion_list = sorted(excluded_ids)

        candidate_menu_items = self._menu_retriever.select(
            message,
            menu_items,
            excluded_ids=excluded_ids,
        )

        catalog_response = _try_catalog_fast_path(
            message,
            constraints,
            menu_items,
            excluded_ids,
        )
        if catalog_response is not None:
            return catalog_response

        rewritten = rewrite_query(message, history)
        search_query = rewritten if rewritten != message else message
        logger.debug("Query rewrite: %r -> %r", message, search_query)

        retrieved = self._retriever.search(search_query, self._config.top_k)

        from app.rag.intent_classifier import classify_intent

        intent = classify_intent(message)
        if intent.source_hints and intent.confidence >= 0.1:
            retrieved = _rerank_by_intent(retrieved, intent.source_hints)
            logger.debug(
                "Intent rerank: intent=%s conf=%.2f sources=%s",
                intent.intent,
                intent.confidence,
                intent.source_hints,
            )

        chunks = [item.chunk for item in retrieved]
        flags = detect_guardrail_flags(message)

        confidence = compute_retrieval_confidence(retrieved)
        if confidence.guardrail_flag:
            flags = _dedupe([*flags, confidence.guardrail_flag])
        logger.debug(
            "Retrieval confidence: score=%.3f level=%s reason=%s",
            confidence.score,
            confidence.level,
            confidence.reason,
        )

        budget_picks: list[dict[str, Any]] = []
        if constraints.get("budget_vnd"):
            budget_picks = solve_budget(
                menu_items,
                int(constraints["budget_vnd"]),
                constraints.get("party_size"),
                excluded_ids=excluded_ids,
            )

        source_ids = [item.chunk.source for item in retrieved[:3]]
        cacheable = _is_cacheable(constraints)
        cached = self._cache.get(
            message,
            source_ids,
            session_id=session_id,
            exclusion_ids=exclusion_list,
            menu_version=menu_version,
            cacheable=cacheable,
        )
        if cached is not None:
            logger.debug("Cache hit for query: %r", message)
            return cached

        provider_available = False
        answer: str | None = None
        suggested_actions: list[dict] = []
        requested_count = constraints.get("requested_count") or policy.requested_count
        max_suggestions = requested_count or policy.max_suggestions

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
                        max_suggestions=max_suggestions,
                        requested_count=requested_count,
                        excluded_menu_item_ids=excluded_ids,
                        facts=facts,
                        cart_items=cart_items,
                        orders=orders,
                        promotions=promotions,
                        local_time=local_time,
                        meal_period=meal_period,
                        budget_picks=budget_picks,
                        language=str(constraints.get("language") or "vi"),
                        rolling_summary=rolling_summary,
                    )
                )
                parsed = parse_model_response(
                    raw_answer,
                    candidate_menu_items,
                    excluded_menu_item_ids=excluded_ids,
                    max_actions=max_suggestions,
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
                    if budget_picks and constraints.get("budget_vnd") and not suggested_actions:
                        suggested_actions = enforce_suggestion_policy(
                            budget_picks,
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

        follow_up = _build_follow_up(
            menu_items,
            suggested_actions,
            excluded_ids,
            max_suggestions,
        )
        suggest_staff_handoff = _should_suggest_staff_handoff(constraints, confidence.score, flags)

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
            follow_up=follow_up,
            suggest_staff_handoff=suggest_staff_handoff,
        ).model_dump()

        if provider_available:
            self._cache.put(
                message,
                source_ids,
                response,
                session_id=session_id,
                exclusion_ids=exclusion_list,
                menu_version=menu_version,
                cacheable=cacheable,
            )

        return response


def _is_cacheable(constraints: dict[str, Any]) -> bool:
    if constraints.get("is_recommendation"):
        return False
    return constraints.get("intent") in FAQ_POLICY_INTENTS


def _should_suggest_staff_handoff(
    constraints: dict[str, Any],
    confidence_score: float,
    flags: list[str],
) -> bool:
    if constraints.get("allergens"):
        return True
    if constraints.get("intent") == "dietary" and constraints.get("allergens"):
        return True
    if confidence_score < 0.3:
        return True
    return "RETRIEVAL_FAILED" in flags or "LOW_RETRIEVAL_CONFIDENCE" in flags


def _build_follow_up(
    menu_items: list[dict[str, Any]],
    suggested_actions: list[dict[str, Any]],
    excluded_ids: frozenset[str],
    max_suggestions: int,
) -> FollowUp:
    suggested_ids = {
        str(action.get("menu_item_id") or action.get("id") or "").strip()
        for action in suggested_actions
    }
    suggested_ids.discard("")

    eligible = [
        item
        for item in menu_items
        if bool(item.get("is_available", True))
        and _item_id(item)
        and _item_id(item) not in excluded_ids
        and _item_id(item) not in suggested_ids
    ]
    remaining_count = len(eligible)
    can_show_more = remaining_count > 0 and len(suggested_actions) >= max(1, max_suggestions)
    return FollowUp(can_show_more=can_show_more, remaining_count=remaining_count)


def _try_catalog_fast_path(
    message: str,
    constraints: dict[str, Any],
    menu_items: list[dict[str, Any]],
    excluded_ids: frozenset[str],
) -> dict[str, Any] | None:
    if not constraints.get("is_catalog_only"):
        return None
    if not constraints.get("category"):
        return None
    if has_soft_criteria(constraints):
        return None

    category = str(constraints["category"])
    matched = [
        item
        for item in menu_items
        if bool(item.get("is_available", True))
        and _item_id(item)
        and _item_id(item) not in excluded_ids
        and _matches_category(item, category)
    ]
    if not matched:
        return None

    lines = [
        f"- {_item_id(item)}: {item.get('name') or 'Món'} ({item.get('category_name') or category})"
        for item in matched[:12]
    ]
    content = (
        f"Đây là các món thuộc nhóm {category.replace('_', ' ')} đang còn phục vụ:\n"
        + "\n".join(lines)
    )
    return ChatResponse(
        content=content,
        provider_available=False,
        model="deterministic-catalog",
        retrieved_sources=[],
        guardrail_flags=[],
        suggested_cart_actions=[],
        follow_up=FollowUp(
            can_show_more=len(matched) > 12,
            remaining_count=max(len(matched) - 12, 0),
        ),
        suggest_staff_handoff=False,
    ).model_dump()


def _matches_category(item: dict[str, Any], category: str) -> bool:
    category_name = str(item.get("category_name") or "").casefold()
    category_id = str(item.get("category_id") or "").casefold()
    needle = category.replace("_", " ").casefold()
    return needle in category_name or needle in category_id or category.casefold() in category_name


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("menu_item_id") or item.get("id") or "").strip()


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
    """Re-rank retrieval results by boosting scores of intent-matching sources."""
    if not source_hints or not results:
        return results

    hint_set = set(source_hints)
    hint_results = [r for r in results if r.chunk.source in hint_set]
    other_results = [r for r in results if r.chunk.source not in hint_set]

    if not hint_results:
        return results

    hint_results.sort(key=lambda r: r.score, reverse=True)
    other_results.sort(key=lambda r: r.score, reverse=True)

    merged = []
    hi, oi = 0, 0
    if hi < len(hint_results):
        merged.append(hint_results[hi])
        hi += 1
    while hi < len(hint_results) or oi < len(other_results):
        if oi < len(other_results):
            merged.append(other_results[oi])
            oi += 1
        if hi < len(hint_results):
            merged.append(hint_results[hi])
            hi += 1

    return merged
