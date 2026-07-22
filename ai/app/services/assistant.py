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
from app.rag.budget_recommendation_fast_path import try_budget_recommendation_fast_path
from app.rag.party_recommendation_fast_path import try_party_recommendation_fast_path
from app.rag.confidence import compute_retrieval_confidence
from app.rag.constraint_extractor import extract_constraints
from app.rag.content_grounding import format_grounded_recommendation_content, ground_response_content
from app.rag.conversation_policy import (
    build_conversation_policy,
    build_prior_suggestion_actions,
    enforce_suggestion_policy,
    infer_suggested_actions_from_content,
)
from app.rag.rolling_summary import update_rolling_summary
from app.rag.embedding_retriever import EmbeddingEncoder, create_encoder
from app.rag.guardrails import detect_guardrail_flags
from app.rag.knowledge_base import load_markdown_knowledge_base
from app.rag.pairing_recommendation_fast_path import try_pairing_recommendation_fast_path
from app.rag.menu_exclusions import (
    detect_excluded_category_ids,
    filter_items_by_excluded_categories,
    recommendation_intro,
)
from app.rag.menu_grounding import MenuCandidateRetriever
from app.rag.menu_presence_fast_path import try_menu_presence_fast_path
from app.rag.menu_item_kind import filter_items_by_kind
from app.rag.menu_query_filters import (
    has_allergy_avoidance_context,
    infer_allergen_excluded_menu_item_ids,
)
from app.rag.output_parser import parse_model_response
from app.rag.kb_info_fast_path import try_kb_info_fast_path
from app.rag.llm_intent_classifier import (
    classify_intent_for_message,
    classify_with_llm,
    is_ambiguous,
    merge_llm_signals_into_constraints,
    merge_llm_signals_into_policy,
)
from app.rag.prompts import build_fallback_answer, build_messages
from app.rag.query_rewriter import rewrite_query
from app.rag.response_cache import ResponseCache
from app.rag.retrieval_factory import build_retriever_stack
from app.rag.retriever import BM25Retriever, Retriever
from app.rag.smalltalk import try_smalltalk
from app.rag.vietnamese_normalizer import normalize_query_text
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
                use_gemini_features=config.uses_gemini_native_features,
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
                encoder=embedding_encoder or create_encoder(self._config.embedding_model),
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
            early = dict(context["early_response"])
            early["suggested_cart_actions"] = _finalize_suggested_actions(
                context,
                early.get("suggested_cart_actions") or [],
            )
            early = _finalize_response_payload(early, context)
            yield {"type": "token", "data": {"text": early["content"]}}
            yield {"type": "final", "data": early}
            yield {"type": "done", "data": {"ok": True}}
            return

        if context.get("cached_response") is not None:
            cached = _finalize_response_payload(dict(context["cached_response"]), context)
            yield {"type": "token", "data": {"text": cached["content"]}}
            yield {"type": "final", "data": cached}
            yield {"type": "done", "data": {"ok": True}}
            return

        if self._client is None or not context.get("should_call_llm", True):
            menu_fallback = _build_menu_based_fallback(context)
            if menu_fallback is not None:
                answer, suggested_actions, flags = menu_fallback
            else:
                answer = build_fallback_answer(message, context["chunks"])
                suggested_actions = []
                flags = context["flags"]

            follow_up = _build_follow_up(
                payload.get("menu_items") or [],
                suggested_actions,
                context["excluded_ids"],
                context["max_suggestions"],
            )
            fallback = _build_response_from_parts(
                answer,
                provider_available=False,
                model=self._config.model,
                retrieved=context["retrieved"],
                flags=flags,
                suggested_actions=suggested_actions,
                follow_up=follow_up,
                suggest_staff_handoff=context["suggest_staff_handoff"],
                stages=context["stages"],
                context=context,
            )
            yield {"type": "token", "data": {"text": fallback["content"]}}
            yield {"type": "final", "data": fallback}
            yield {"type": "done", "data": {"ok": True}}
            return

        messages = _build_llm_messages(message, context, payload)

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
            early = context["early_response"]
            early_path = (early.get("latency_ms") or {}).get("path")
            if early_path:
                stages["path"] = early_path
            early["suggested_cart_actions"] = _finalize_suggested_actions(
                context,
                early.get("suggested_cart_actions") or [],
            )
            early["latency_ms"] = {**stages}
            early = _finalize_response_payload(early, context)
            return early, stages
        if context.get("cached_response") is not None:
            stages["total"] = round((time.perf_counter() - started) * 1000, 1)
            stages["path"] = "cache_hit"
            cached = _finalize_response_payload(dict(context["cached_response"]), context)
            cached["latency_ms"] = {**stages}
            return cached, stages

        provider_available = False
        answer: str | None = None
        suggested_actions: list[dict] = []
        flags = list(context["flags"])

        if self._client is not None and context.get("should_call_llm", True):
            llm_started = time.perf_counter()
            try:
                async with asyncio.timeout(self._config.llm_timeout_seconds):
                    raw_answer = await self._client.complete(_build_llm_messages(message, context, payload))
                stages["llm"] = round((time.perf_counter() - llm_started) * 1000, 1)
                parsed = parse_model_response(
                    raw_answer,
                    context["available_menu_items"],
                    excluded_menu_item_ids=context["excluded_ids"],
                    max_actions=context["max_suggestions"],
                )
                if parsed is None:
                    flags = _dedupe([*flags, "AI_OUTPUT_SCHEMA_INVALID"])
                else:
                    answer, suggested_actions, flags = _apply_parsed_response(parsed, context, flags)
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
            menu_fallback = _build_menu_based_fallback(context)
            if menu_fallback is not None:
                answer, suggested_actions, fallback_flags = menu_fallback
                flags = _dedupe([*flags, *fallback_flags])
            else:
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
            context=context,
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
        if provider_available:
            stages["path"] = "llm"
        elif not context.get("should_call_llm", True):
            stages["path"] = "fallback_no_llm"
        else:
            stages["path"] = "fallback"
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
        payload_language = str(payload.get("language") or "").strip()
        if payload_language in {"vi", "en"}:
            constraints = {**constraints, "language": payload_language}
        excluded_category_ids = detect_excluded_category_ids(message, history)
        policy = build_conversation_policy(
            message,
            history,
            session_memory,
            menu_items,
            category=constraints.get("category"),
            variation_seed=session_id or message,
        )
        intent_result = classify_intent_for_message(message, history)
        intent_flags: list[str] = []
        if (
            self._config.llm_intent_classification_enabled
            and self._client is not None
            and is_ambiguous(intent_result, constraints, policy, message=message)
        ):
            intent_llm_started = time.perf_counter()
            llm_signals = await classify_with_llm(
                self._client,
                message,
                history,
                rolling_summary,
                timeout_seconds=self._config.intent_classification_timeout_seconds,
            )
            stages["intent_llm"] = round((time.perf_counter() - intent_llm_started) * 1000, 1)
            if llm_signals is not None:
                constraints = merge_llm_signals_into_constraints(constraints, llm_signals)
                policy = merge_llm_signals_into_policy(policy, llm_signals)
            else:
                intent_flags.append("INTENT_CLASSIFICATION_DEGRADED")
        stages["extract"] = round((time.perf_counter() - extract_started) * 1000, 1)

        payload_excluded = frozenset(
            str(item_id).strip()
            for item_id in (payload.get("excluded_menu_item_ids") or [])
            if str(item_id).strip()
        )
        allergen_context = bool(constraints.get("allergens")) and has_allergy_avoidance_context(
            message
        )
        allergen_excluded = (
            frozenset(
                infer_allergen_excluded_menu_item_ids(constraints["allergens"], menu_items)
            )
            if allergen_context
            else frozenset()
        )
        excluded_ids = policy.excluded_menu_item_ids | payload_excluded | allergen_excluded
        exclusion_list = sorted(excluded_ids)
        available_menu_items = [
            item
            for item in menu_items
            if bool(item.get("is_available", True))
            and _item_id(item)
            and _item_id(item) not in excluded_ids
        ]
        if policy.requested_item_kind is not None:
            available_menu_items = filter_items_by_kind(
                available_menu_items,
                policy.requested_item_kind,
            )
        available_menu_items = filter_items_by_excluded_categories(
            available_menu_items,
            excluded_category_ids,
        )

        menu_started = time.perf_counter()
        candidate_menu_items = self._menu_retriever.select(
            message,
            menu_items,
            excluded_ids=excluded_ids,
            requested_item_kind=policy.requested_item_kind,
            excluded_category_ids=excluded_category_ids,
        )
        party_size = policy.party_size or constraints.get("party_size")
        if party_size and party_size >= 4:
            from app.rag.party_menu_ranking import rank_candidates_for_party

            candidate_menu_items = rank_candidates_for_party(candidate_menu_items, party_size)
            available_menu_items = rank_candidates_for_party(available_menu_items, party_size)
        stages["menu_retrieval"] = round((time.perf_counter() - menu_started) * 1000, 1)

        catalog_response = _try_catalog_fast_path(message, constraints, menu_items, excluded_ids)
        if catalog_response is not None:
            catalog_response["latency_ms"] = {**stages, "path": "catalog_fast_path"}
            return _early_context_response(catalog_response, stages, policy, available_menu_items)

        party_fast_path = try_party_recommendation_fast_path(
            constraints,
            policy,
            # Prefer full menu when party size is known so ranking/policy can work
            # even if sparse text retrieval returns few/no candidates.
            available_menu_items if party_size else candidate_menu_items,
        )
        if party_fast_path is not None:
            party_fast_path["latency_ms"] = {**stages, "path": "party_fast_path"}
            return _early_context_response(party_fast_path, stages, policy, available_menu_items)

        pairing_fast_path = try_pairing_recommendation_fast_path(
            message,
            intent=intent_result.intent,
            policy=policy,
            menu_items=available_menu_items,
        )
        if pairing_fast_path is not None:
            pairing_fast_path["latency_ms"] = {**stages, "path": "pairing_fast_path"}
            return _early_context_response(pairing_fast_path, stages, policy, available_menu_items)

        rewrite_started = time.perf_counter()
        rewritten = rewrite_query(message, history, intent=intent_result)
        search_query = rewritten if rewritten != message else message
        stages["rewrite"] = round((time.perf_counter() - rewrite_started) * 1000, 1)

        intent = intent_result
        rag_top_k = 5 if intent.intent in RECOMMEND_INTENTS or intent.intent in FAQ_POLICY_INTENTS else 3

        retrieval_started = time.perf_counter()
        retrieved = self._retriever.search(search_query, rag_top_k)
        if intent.source_hints and intent.confidence >= 0.1:
            retrieved = _rerank_by_intent(retrieved, intent.source_hints)
        stages["rag_retrieval"] = round((time.perf_counter() - retrieval_started) * 1000, 1)

        chunks = [item.chunk for item in retrieved]
        flags = _dedupe([*detect_guardrail_flags(message), *intent_flags])
        if allergen_context:
            flags = _dedupe([*flags, "ALLERGY_DISCLAIMER"])
        confidence = compute_retrieval_confidence(retrieved, intent=intent.intent)
        if confidence.guardrail_flag:
            flags = _dedupe([*flags, confidence.guardrail_flag])

        # RAG relevance gate: skip KB fast-path for queries that should be
        # answered from menu data + LLM reasoning, not from FAQ/policy RAG chunks.
        # This prevents the AI from blindly using RAG when the user asks about
        # specific menu items, prices, or food attributes.
        _MENU_SPECIFIC_INTENTS = frozenset({"ask_price", "spice_level", "order"})
        _should_skip_kb_fast_path = (
            intent.intent in _MENU_SPECIFIC_INTENTS
            or (
                # Food-related query with low retrieval confidence → let LLM decide
                intent.intent == "browse_menu"
                and confidence.score < 0.5
                and any(
                    constraints.get(field)
                    for field in ("allergens", "diet", "spice")
                    if constraints.get(field) and constraints[field] != "unknown"
                )
            )
        )

        kb_fast_path = None
        if not _should_skip_kb_fast_path:
            kb_fast_path = try_menu_presence_fast_path(
                message,
                available_menu_items,
                wants_recommendations=policy.wants_recommendations,
            )
            if kb_fast_path is None:
                kb_fast_path = try_kb_info_fast_path(
                    message,
                    retrieved,
                    intent=intent.intent,
                    wants_recommendations=policy.wants_recommendations,
                    retriever=self._retriever,
                    history=history,
                    is_solo_dining=bool(constraints.get("is_solo_dining")),
                )
        if kb_fast_path is not None:
            kb_fast_path["latency_ms"] = {**stages, "path": "kb_fast_path"}
            return _early_context_response(kb_fast_path, stages, policy, available_menu_items)

        budget_picks: list[dict[str, Any]] = []
        if constraints.get("budget_vnd"):
            budget_picks = solve_budget(
                menu_items,
                int(constraints["budget_vnd"]),
                constraints.get("party_size"),
                excluded_ids=excluded_ids,
            )

        budget_fast_path = try_budget_recommendation_fast_path(
            constraints,
            policy,
            candidate_menu_items,
            budget_picks,
        )
        if budget_fast_path is not None:
            budget_fast_path["latency_ms"] = {**stages, "path": "budget_fast_path"}
            return _early_context_response(budget_fast_path, stages, policy, available_menu_items)

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
            "wants_recommendations": policy.wants_recommendations,
            "excluded_category_ids": excluded_category_ids,
            "excluded_ids": excluded_ids,
            "exclusion_list": exclusion_list,
            "available_menu_items": available_menu_items,
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
            "should_call_llm": confidence.should_call_llm,
            "confidence_level": confidence.level,
            "intent": intent,
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
            context["available_menu_items"],
            excluded_menu_item_ids=context["excluded_ids"],
            max_actions=context["max_suggestions"],
        )
        if parsed is None:
            flags = _dedupe([*flags, "AI_OUTPUT_SCHEMA_INVALID"])
        else:
            answer, suggested_actions, flags = _apply_parsed_response(parsed, context, flags)
            provider_available = True

    if not answer:
        menu_fallback = _build_menu_based_fallback(context)
        if menu_fallback is not None:
            answer, suggested_actions, flags = menu_fallback
            provider_available = False
        else:
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
        context=context,
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


def _build_menu_based_fallback(
    context: dict[str, Any],
) -> tuple[str, list[dict], list[str]] | None:
    """When Gemini fails, still suggest real menu items for recommendation queries."""

    if not context["policy"].wants_recommendations:
        return None
    if not context["candidate_menu_items"]:
        return None

    seed_actions = list(context.get("budget_picks") or [])
    actions = enforce_suggestion_policy(
        seed_actions,
        context["candidate_menu_items"],
        context["policy"],
    )
    if not actions:
        return None

    content = format_grounded_recommendation_content(
        actions,
        intro=recommendation_intro(
            requested_item_kind=context["policy"].requested_item_kind,
            excluded_category_ids=context.get("excluded_category_ids"),
            seed=context.get("session_id") or context["message"],
        ),
    )
    flags = _dedupe([*context["flags"], "CUSTOMER_CONFIRMATION_REQUIRED"])
    return content, actions, flags


def _build_llm_messages(message: str, context: dict[str, Any], payload: dict) -> list[dict[str, str]]:
    return build_messages(
        message,
        context["chunks"],
        context["candidate_menu_items"],
        context["history"],
        table_code=payload.get("table_code"),
        session_memory=context["session_memory"],
        max_suggestions=context["max_suggestions"],
        requested_count=context["requested_count"],
        excluded_menu_item_ids=context["excluded_ids"],
        catalog_menu_items=context["available_menu_items"],
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
        wants_recommendations=context["policy"].wants_recommendations,
        party_size=context["policy"].party_size or context["constraints"].get("party_size"),
        intent=str(getattr(context.get("intent"), "intent", None) or ""),
    )


def _early_context_response(
    early_response: dict[str, Any],
    stages: dict[str, float],
    policy: Any,
    available_menu_items: list[dict[str, Any]],
) -> dict[str, Any]:
    from app.rag.content_grounding import strip_menu_ids

    if early_response.get("content"):
        early_response["content"] = strip_menu_ids(str(early_response["content"]))
    return {
        "early_response": early_response,
        "stages": stages,
        "policy": policy,
        "available_menu_items": available_menu_items,
    }


def _finalize_suggested_actions(
    context: dict[str, Any],
    suggested_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    policy = context["policy"]
    if policy.wants_recommendations or not policy.surface_prior_suggestion_cards:
        return suggested_actions
    if suggested_actions:
        return suggested_actions
    prior_actions = build_prior_suggestion_actions(
        context["available_menu_items"],
        policy,
    )
    return prior_actions


def _apply_parsed_response(
    parsed,
    context: dict[str, Any],
    flags: list[str],
) -> tuple[str, list[dict], list[str]]:
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
    if context["policy"].wants_recommendations and not suggested_actions:
        suggested_actions = enforce_suggestion_policy(
            [],
            context["candidate_menu_items"],
            context["policy"],
        )
    if context["policy"].wants_recommendations and not suggested_actions:
        suggested_actions = infer_suggested_actions_from_content(
            parsed.content,
            context["available_menu_items"],
            context["policy"],
        )

    suggested_actions = _finalize_suggested_actions(context, suggested_actions)

    content, grounding_flags, suggested_actions = ground_response_content(
        parsed.content,
        suggested_actions,
        context["available_menu_items"],
        wants_recommendations=context["policy"].wants_recommendations,
    )
    merged_flags = _dedupe([*flags, *parsed.guardrail_flags, *grounding_flags])
    if suggested_actions:
        merged_flags = _dedupe([*merged_flags, "CUSTOMER_CONFIRMATION_REQUIRED"])
    return content, suggested_actions, merged_flags


def _attach_rolling_summary(
    response: dict[str, Any],
    context: dict[str, Any],
    *,
    content: str,
    suggested_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = update_rolling_summary(
        str(context.get("rolling_summary") or ""),
        user_message=str(context.get("message") or ""),
        assistant_content=content,
        suggested_actions=suggested_actions,
        constraints=context.get("constraints") or {},
        facts=context.get("facts") or [],
    )
    if updated:
        response["updated_rolling_summary"] = updated
    return response


def _finalize_response_payload(
    response: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    return _attach_rolling_summary(
        response,
        context,
        content=str(response.get("content") or ""),
        suggested_actions=list(response.get("suggested_cart_actions") or []),
    )


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
    context: dict[str, Any] | None = None,
) -> dict:
    from app.rag.content_grounding import strip_menu_ids

    result = ChatResponse(
        content=strip_menu_ids(content),
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
    if context is not None:
        return _finalize_response_payload(result, context)
    return result


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
    if "CUSTOMER_CONFIRMATION_REQUIRED" in detect_guardrail_flags(message):
        return None
    if not constraints.get("is_catalog_only"):
        return None
    if not constraints.get("category"):
        return None
    # Session party_size / prior soft criteria must not block category listing.
    if constraints.get("is_recommendation") or constraints.get("budget_vnd"):
        return None
    from app.rag.constraint_extractor import has_hard_dietary_constraints

    if has_hard_dietary_constraints(constraints):
        return None

    category = str(constraints["category"])
    normalized_message = normalize_query_text(message)
    matched = [
        item
        for item in menu_items
        if bool(item.get("is_available", True))
        and _item_id(item)
        and _item_id(item) not in excluded_ids
        and _matches_category(item, category, normalized_message)
    ]
    if not matched:
        return None

    lines = [
        f"- {item.get('name') or 'Món'} ({item.get('category_name') or category.replace('_', ' ')})"
        for item in matched[:12]
    ]
    display_category = str(matched[0].get("category_name") or category.replace("_", " "))
    content = (
        f"Đây là các món thuộc nhóm {display_category} đang còn phục vụ:\n"
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


def _matches_category(
    item: dict[str, Any],
    category: str,
    message_normalized: str = "",
) -> bool:
    from app.rag.constraint_extractor import CATEGORY_ALIASES

    category_name = normalize_query_text(str(item.get("category_name") or ""))
    category_id = normalize_query_text(str(item.get("category_id") or ""))
    item_name = normalize_query_text(str(item.get("name") or ""))
    aliases = CATEGORY_ALIASES.get(category, (category.replace("_", " "),))
    active_aliases = (
        [alias for alias in aliases if alias in message_normalized]
        if message_normalized
        else list(aliases)
    )
    if not active_aliases:
        active_aliases = list(aliases)
    for alias in active_aliases:
        needle = normalize_query_text(alias)
        if not needle:
            continue
        if needle in item_name:
            return True
        if needle not in category_name and needle not in category_id:
            continue
        combined_category = (
            " & " in category_name
            or " va " in category_name
            or len(aliases) > 1
        )
        if combined_category and needle not in item_name:
            sibling_terms = [
                normalize_query_text(other)
                for other in aliases
                if other != alias and normalize_query_text(other)
            ]
            if any(sibling in item_name for sibling in sibling_terms):
                continue
        return True
    return False


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
    _ = boost_factor
    if not source_hints or not results:
        return results

    hint_set = set(source_hints)
    hint_results = sorted(
        (r for r in results if r.chunk.source in hint_set),
        key=lambda r: r.score,
        reverse=True,
    )
    other_results = sorted(
        (r for r in results if r.chunk.source not in hint_set),
        key=lambda r: r.score,
        reverse=True,
    )
    return [*hint_results, *other_results]
