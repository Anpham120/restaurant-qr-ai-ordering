from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

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
from app.rag.smalltalk import try_smalltalk
from app.rag.streaming_json import extract_streaming_content
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
RECOMMEND_INTENTS = frozenset({"recommend", "dietary", "budget"})


class AiAssistantService:
    def __init__(
        self,
        config: AiServiceConfig,
        *,
        llm_client: GeminiClient | None = None,
        embedding_encoder: EmbeddingEncoder | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client
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
                config.llm_timeout_seconds,
                config.max_retry,
                http_client=http_client,
                max_tokens=config.max_tokens,
                reasoning_effort=config.reasoning_effort,
            )
        self._cache = ResponseCache(max_size=500, ttl_seconds=300)
        self._ready = False

    @property
    def retrieval_method(self) -> str:
        return self._retrieval_method

    @property
    def is_ready(self) -> bool:
        return self._ready

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

    def prewarm(self) -> None:
        """Load embedding model and encode a dummy query before serving traffic."""

        started = time.perf_counter()
        encoder = getattr(self._menu_retriever, "_encoder", None)
        if encoder is not None and hasattr(encoder, "encode_queries"):
            encoder.encode_queries(["warmup"])
        self._ready = True
        logger.info("AI service prewarm completed in %.0fms", (time.perf_counter() - started) * 1000)

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
        return self._cache.stats

    def invalidate_cache(self) -> None:
        self._cache.invalidate()

    async def chat(self, payload: dict) -> dict:
        response, _stages = await self._process_chat(payload)
        return response

    async def chat_stream(self, payload: dict) -> AsyncIterator[dict[str, Any]]:
        message = str(payload.get("message") or "").strip()
        smalltalk = try_smalltalk(message)
        if smalltalk is not None:
            yield {"type": "token", "data": {"text": smalltalk["content"]}}
            yield {"type": "final", "data": smalltalk}
            yield {"type": "done", "data": {"ok": True}}
            return

        context = await self._prepare_context(payload)
        if context.get("early_response") is not None:
            early = context["early_response"]
            yield {"type": "token", "data": {"text": early["content"]}}
            yield {"type": "final", "data": early}
            yield {"type": "done", "data": {"ok": True}}
            return

        if context.get("cached_response") is not None:
            cached = context["cached_response"]
            yield {"type": "token", "data": {"text": cached["content"]}}
            yield {"type": "final", "data": cached}
            yield {"type": "done", "data": {"ok": True}}
            return

        if self._client is None:
            fallback = _build_response_from_parts(
                build_fallback_answer(message, context["chunks"]),
                provider_available=False,
                model=self._config.model,
                retrieved=context["retrieved"],
                flags=context["flags"],
                suggested_actions=[],
                follow_up=context["follow_up"],
                suggest_staff_handoff=context["suggest_staff_handoff"],
                stages=context["stages"],
            )
            yield {"type": "token", "data": {"text": fallback["content"]}}
            yield {"type": "final", "data": fallback}
            yield {"type": "done", "data": {"ok": True}}
            return

        messages = build_messages(
            message,
            context["chunks"],
            context["candidate_menu_items"],
            context["history"],
            table_code=payload.get("table_code"),
            session_memory=context["session_memory"],
            max_suggestions=context["max_suggestions"],
            requested_count=context["requested_count"],
            excluded_menu_item_ids=context["excluded_ids"],
            facts=context["facts"],
            cart_items=context["cart_items"],
            orders=context["orders"],
            promotions=context["promotions"],
            local_time=context["local_time"],
            meal_period=context["meal_period"],
            budget_picks=context["budget_picks"],
            language=str(context["constraints"].get("language") or "vi"),
            rolling_summary=context["rolling_summary"],
            rag_top_k=context["rag_top_k"],
        )

        accumulated = ""
        last_content = ""
        llm_started = time.perf_counter()
        try:
            async with asyncio.timeout(self._config.llm_timeout_seconds):
                async for delta in self._client.complete_stream(messages):
                    accumulated += delta
                    content = extract_streaming_content(accumulated)
                    if content and content != last_content:
                        new_text = content[len(last_content) :]
                        if new_text:
                            yield {"type": "token", "data": {"text": new_text}}
                        last_content = content
        except TimeoutError:
            context["flags"] = _dedupe([*context["flags"], "AI_PROVIDER_UNAVAILABLE"])
        except Exception as exception:
            logger.exception(
                "AI provider stream failed provider=%s model=%s error_type=%s",
                self._config.provider,
                self._config.model,
                type(exception).__name__,
            )
            context["flags"] = _dedupe([*context["flags"], "AI_PROVIDER_UNAVAILABLE"])
        context["stages"]["llm"] = round((time.perf_counter() - llm_started) * 1000, 1)

        response = _finalize_llm_response(
            self,
            message=message,
            raw_answer=accumulated or None,
            context=context,
            payload=payload,
        )
        if last_content != response["content"]:
            remainder = response["content"][len(last_content) :]
            if remainder:
                yield {"type": "token", "data": {"text": remainder}}
        yield {"type": "final", "data": response}
        yield {"type": "done", "data": {"ok": True}}

    async def _process_chat(self, payload: dict) -> tuple[dict, dict[str, float]]:
        started = time.perf_counter()
        message = str(payload.get("message") or "").strip()

        smalltalk = try_smalltalk(message)
        if smalltalk is not None:
            stages = {"total": round((time.perf_counter() - started) * 1000, 1), "path": "smalltalk"}
            smalltalk["latency_ms"] = stages
            return smalltalk, stages

        context = await self._prepare_context(payload)
        stages = context["stages"]
        if context.get("early_response") is not None:
            stages["total"] = round((time.perf_counter() - started) * 1000, 1)
            context["early_response"]["latency_ms"] = stages
            return context["early_response"], stages
        if context.get("cached_response") is not None:
            stages["total"] = round((time.perf_counter() - started) * 1000, 1)
            context["cached_response"]["latency_ms"] = stages
            return context["cached_response"], stages

        provider_available = False
        answer: str | None = None
        suggested_actions: list[dict] = []
        flags = list(context["flags"])

        if self._client is not None:
            llm_started = time.perf_counter()
            try:
                async with asyncio.timeout(self._config.llm_timeout_seconds):
                    raw_answer = await self._client.complete(
                        build_messages(
                            message,
                            context["chunks"],
                            context["candidate_menu_items"],
                            context["history"],
                            table_code=payload.get("table_code"),
                            session_memory=context["session_memory"],
                            max_suggestions=context["max_suggestions"],
                            requested_count=context["requested_count"],
                            excluded_menu_item_ids=context["excluded_ids"],
                            facts=context["facts"],
                            cart_items=context["cart_items"],
                            orders=context["orders"],
                            promotions=context["promotions"],
                            local_time=context["local_time"],
                            meal_period=context["meal_period"],
                            budget_picks=context["budget_picks"],
                            language=str(context["constraints"].get("language") or "vi"),
                            rolling_summary=context["rolling_summary"],
                            rag_top_k=context["rag_top_k"],
                        )
                    )
                stages["llm"] = round((time.perf_counter() - llm_started) * 1000, 1)
                parsed = parse_model_response(
                    raw_answer,
                    context["candidate_menu_items"],
                    excluded_menu_item_ids=context["excluded_ids"],
                    max_actions=context["max_suggestions"],
                )
                if parsed is None:
                    flags = _dedupe([*flags, "AI_OUTPUT_SCHEMA_INVALID"])
                else:
                    answer = parsed.content
                    suggested_actions = enforce_suggestion_policy(
                        parsed.suggested_cart_actions,
                        context["candidate_menu_items"],
                        context["policy"],
                    )
                    if (
                        context["budget_picks"]
                        and context["constraints"].get("budget_vnd")
                        and not suggested_actions
                    ):
                        suggested_actions = enforce_suggestion_policy(
                            context["budget_picks"],
                            context["candidate_menu_items"],
                            context["policy"],
                        )
                    flags = _dedupe([*flags, *parsed.guardrail_flags])
                    if suggested_actions:
                        flags = _dedupe([*flags, "CUSTOMER_CONFIRMATION_REQUIRED"])
                    provider_available = True
            except TimeoutError:
                stages["llm"] = round((time.perf_counter() - llm_started) * 1000, 1)
                flags = _dedupe([*flags, "AI_PROVIDER_UNAVAILABLE"])
            except Exception as exception:
                stages["llm"] = round((time.perf_counter() - llm_started) * 1000, 1)
                logger.exception(
                    "AI provider request failed provider=%s model=%s error_type=%s",
                    self._config.provider,
                    self._config.model,
                    type(exception).__name__,
                )
                flags = _dedupe([*flags, "AI_PROVIDER_UNAVAILABLE"])

        if not answer:
            answer = build_fallback_answer(message, context["chunks"])

        response = _build_response_from_parts(
            answer,
            provider_available=provider_available,
            model=self._config.model,
            retrieved=context["retrieved"],
            flags=flags,
            suggested_actions=suggested_actions,
            follow_up=context["follow_up"],
            suggest_staff_handoff=context["suggest_staff_handoff"],
            stages=stages,
        )

        if provider_available:
            self._cache.put(
                message,
                context["source_ids"],
                response,
                session_id=context["session_id"],
                exclusion_ids=context["exclusion_list"],
                menu_version=context["menu_version"],
                cacheable=context["cacheable"],
            )

        stages["total"] = round((time.perf_counter() - started) * 1000, 1)
        response["latency_ms"] = stages
        logger.info("chat latency_ms=%s", stages)
        return response, stages

    async def _prepare_context(self, payload: dict) -> dict[str, Any]:
        stages: dict[str, float] = {}
        started = time.perf_counter()

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

        extract_started = time.perf_counter()
        constraints = extract_constraints(message, history)
        policy = build_conversation_policy(message, history, session_memory, menu_items)
        stages["extract"] = round((time.perf_counter() - extract_started) * 1000, 1)

        payload_excluded = frozenset(
            str(item_id).strip()
            for item_id in (payload.get("excluded_menu_item_ids") or [])
            if str(item_id).strip()
        )
        excluded_ids = policy.excluded_menu_item_ids | payload_excluded
        exclusion_list = sorted(excluded_ids)

        menu_started = time.perf_counter()
        candidate_menu_items = self._menu_retriever.select(
            message,
            menu_items,
            excluded_ids=excluded_ids,
        )
        stages["menu_retrieval"] = round((time.perf_counter() - menu_started) * 1000, 1)

        catalog_response = _try_catalog_fast_path(message, constraints, menu_items, excluded_ids)
        if catalog_response is not None:
            catalog_response["latency_ms"] = stages
            return {"early_response": catalog_response, "stages": stages}

        rewrite_started = time.perf_counter()
        rewritten = rewrite_query(message, history)
        search_query = rewritten if rewritten != message else message
        stages["rewrite"] = round((time.perf_counter() - rewrite_started) * 1000, 1)

        from app.rag.intent_classifier import classify_intent

        intent = classify_intent(message)
        rag_top_k = 5 if intent.intent in RECOMMEND_INTENTS else 3

        retrieval_started = time.perf_counter()
        retrieved = self._retriever.search(search_query, rag_top_k)
        if intent.source_hints and intent.confidence >= 0.1:
            retrieved = _rerank_by_intent(retrieved, intent.source_hints)
        stages["rag_retrieval"] = round((time.perf_counter() - retrieval_started) * 1000, 1)

        chunks = [item.chunk for item in retrieved]
        flags = detect_guardrail_flags(message)
        confidence = compute_retrieval_confidence(retrieved)
        if confidence.guardrail_flag:
            flags = _dedupe([*flags, confidence.guardrail_flag])

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
            stages["total"] = round((time.perf_counter() - started) * 1000, 1)
            cached["latency_ms"] = {**stages, "path": "cache_hit"}
            return {"cached_response": cached, "stages": stages}

        requested_count = constraints.get("requested_count") or policy.requested_count
        max_suggestions = requested_count or policy.max_suggestions
        follow_up = _build_follow_up(menu_items, [], excluded_ids, max_suggestions)
        suggest_staff_handoff = _should_suggest_staff_handoff(constraints, confidence.score, flags)

        stages["prepare"] = round((time.perf_counter() - started) * 1000, 1)
        return {
            "stages": stages,
            "message": message,
            "history": history,
            "session_memory": session_memory,
            "rolling_summary": rolling_summary,
            "session_id": session_id,
            "menu_version": menu_version,
            "constraints": constraints,
            "policy": policy,
            "excluded_ids": excluded_ids,
            "exclusion_list": exclusion_list,
            "candidate_menu_items": candidate_menu_items,
            "retrieved": retrieved,
            "chunks": chunks,
            "flags": flags,
            "budget_picks": budget_picks,
            "source_ids": source_ids,
            "cacheable": cacheable,
            "requested_count": requested_count,
            "max_suggestions": max_suggestions,
            "facts": facts,
            "cart_items": cart_items,
            "orders": orders,
            "promotions": promotions,
            "local_time": local_time,
            "meal_period": meal_period,
            "rag_top_k": rag_top_k,
            "follow_up": follow_up,
            "suggest_staff_handoff": suggest_staff_handoff,
            "confidence_score": confidence.score,
        }


def _finalize_llm_response(
    service: AiAssistantService,
    *,
    message: str,
    raw_answer: str | None,
    context: dict[str, Any],
    payload: dict,
) -> dict:
    provider_available = False
    answer: str | None = None
    suggested_actions: list[dict] = []
    flags = list(context["flags"])

    if raw_answer:
        parsed = parse_model_response(
            raw_answer,
            context["candidate_menu_items"],
            excluded_menu_item_ids=context["excluded_ids"],
            max_actions=context["max_suggestions"],
        )
        if parsed is None:
            flags = _dedupe([*flags, "AI_OUTPUT_SCHEMA_INVALID"])
        else:
            answer = parsed.content
            suggested_actions = enforce_suggestion_policy(
                parsed.suggested_cart_actions,
                context["candidate_menu_items"],
                context["policy"],
            )
            if context["budget_picks"] and context["constraints"].get("budget_vnd") and not suggested_actions:
                suggested_actions = enforce_suggestion_policy(
                    context["budget_picks"],
                    context["candidate_menu_items"],
                    context["policy"],
                )
            flags = _dedupe([*flags, *parsed.guardrail_flags])
            if suggested_actions:
                flags = _dedupe([*flags, "CUSTOMER_CONFIRMATION_REQUIRED"])
            provider_available = True

    if not answer:
        answer = build_fallback_answer(message, context["chunks"])

    follow_up = _build_follow_up(
        payload.get("menu_items") or [],
        suggested_actions,
        context["excluded_ids"],
        context["max_suggestions"],
    )

    response = _build_response_from_parts(
        answer,
        provider_available=provider_available,
        model=service._config.model,
        retrieved=context["retrieved"],
        flags=flags,
        suggested_actions=suggested_actions,
        follow_up=follow_up,
        suggest_staff_handoff=context["suggest_staff_handoff"],
        stages=context["stages"],
    )

    if provider_available:
        service._cache.put(
            message,
            context["source_ids"],
            response,
            session_id=context["session_id"],
            exclusion_ids=context["exclusion_list"],
            menu_version=context["menu_version"],
            cacheable=context["cacheable"],
        )
    return response


def _build_response_from_parts(
    content: str,
    *,
    provider_available: bool,
    model: str,
    retrieved: list,
    flags: list[str],
    suggested_actions: list[dict],
    follow_up: FollowUp,
    suggest_staff_handoff: bool,
    stages: dict[str, float],
) -> dict:
    return ChatResponse(
        content=content,
        provider_available=provider_available,
        model=model,
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
        latency_ms=stages,
    ).model_dump()


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
