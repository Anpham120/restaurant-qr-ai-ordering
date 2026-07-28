from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

import httpx

from app.clients.router import ModelAttempt, RouterClient, capture_model_attempts
from app.config import AiServiceConfig
from app.rag.budget_solver import solve_budget
from app.rag.budget_recommendation_fast_path import try_budget_recommendation_fast_path
from app.rag.party_recommendation_fast_path import try_party_recommendation_fast_path
from app.rag.confidence import compute_retrieval_confidence
from app.rag.claim_verifier import verify_claims
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
    build_suggestion_reason,
    detect_excluded_category_ids,
    filter_items_by_excluded_categories,
    recommendation_intro,
)
from app.rag.menu_grounding import MenuCandidateRetriever
from app.rag.dish_comparison_fast_path import try_dish_comparison_fast_path
from app.rag.menu_presence_fast_path import try_menu_presence_fast_path
from app.rag.menu_item_kind import filter_items_by_kind
from app.rag.menu_query_filters import (
    has_allergy_avoidance_context,
    has_child_dining_context,
    infer_allergen_excluded_menu_item_ids,
    infer_child_unsuitable_menu_item_ids,
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
from app.rag.semantic_planner import apply_semantic_plan, plan_with_llm
from app.rag.retrieval_factory import build_retriever_stack
from app.rag.retriever import BM25Retriever, Retriever
from app.rag.smalltalk import try_smalltalk
from app.rag.vietnamese_normalizer import normalize_query_text
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
MAX_CATALOG_CART_SUGGESTIONS = 4


def _should_use_deterministic_fast_paths(config: AiServiceConfig) -> bool:
    """Legacy KB/party/pairing/budget/catalog paths that bypass the LLM."""

    return not config.llm_first


def _should_use_evidence_first_menu_paths(config: AiServiceConfig) -> bool:
    return (
        config.pipeline_profile in {"evidence_first_v2", "planner_state_v3"}
        or not config.llm_first
    )


def _resolve_should_call_llm(
    config: AiServiceConfig,
    context: dict[str, Any],
    *,
    client_available: bool,
) -> bool:
    if config.llm_first and config.llm_enabled and client_available:
        return True
    return bool(context.get("should_call_llm", True))


def _attach_model_route(
    response: dict,
    attempts: tuple[ModelAttempt, ...],
    config: AiServiceConfig,
) -> dict:
    finalized = dict(response)
    serialized_attempts = [attempt.to_dict() for attempt in attempts]
    successful_attempts = [
        attempt for attempt in attempts if attempt.outcome == "success"
    ]
    fallback_used = any(
        attempt.role == "rate_limit_fallback" for attempt in attempts
    )

    if finalized.get("provider_available") and successful_attempts:
        finalized["model"] = successful_attempts[-1].model
    finalized["primary_model"] = config.model
    finalized["fallback_model"] = (
        config.rate_limit_fallback_model
        if config.rate_limit_fallback_enabled
        else None
    )
    finalized["fallback_used"] = fallback_used
    finalized["fallback_reason"] = "rate_limit_429" if fallback_used else None
    finalized["model_attempts"] = serialized_attempts

    model_route = [
        f"{attempt.model}:{attempt.outcome}"
        for attempt in attempts
    ]
    logger.info(
        "chat completed pipeline_profile=%s model_route=%s "
        "resolved_menu_item_ids=%s verifier_result=%s",
        finalized.get("pipeline_profile") or config.pipeline_profile,
        model_route,
        finalized.get("resolved_menu_item_ids") or [],
        finalized.get("verifier_result") or "not_applicable",
    )
    return finalized


class AiAssistantService:
    def __init__(
        self,
        config: AiServiceConfig,
        *,
        llm_client: RouterClient | None = None,
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
            self._client = RouterClient(
                config.base_url,
                config.api_key,
                config.model,
                config.llm_timeout_seconds,
                config.max_retry,
                http_client=http_client,
                max_tokens=config.max_tokens,
                reasoning_effort=config.reasoning_effort,
                fallback_model=config.rate_limit_fallback_model,
                fallback_enabled=config.rate_limit_fallback_enabled,
            )
        self._cache = ResponseCache(max_size=500, ttl_seconds=300)
        self._ready = False

    @property
    def retrieval_method(self) -> str:
        return self._retrieval_method

    @property
    def retriever_runtime(self) -> dict[str, Any]:
        return dict(self._retriever_runtime)

    @property
    def is_ready(self) -> bool:
        return self._ready

    def _build_retriever(
        self,
        embedding_encoder: EmbeddingEncoder | None,
    ) -> tuple[Retriever, EmbeddingEncoder | None]:
        try:
            resolved_encoder = embedding_encoder
            if self._config.retrieval_method.strip().casefold() != "bm25" and resolved_encoder is None:
                resolved_encoder = create_encoder(self._config.embedding_model)
            stack = build_retriever_stack(
                self._chunks,
                self._config.retrieval_method,
                encoder=resolved_encoder,
            )
            self._retrieval_method = stack.method
            self._retriever_runtime = {
                "requested_method": self._config.retrieval_method,
                "effective_method": stack.method,
                "embedding_model": self._config.embedding_model,
                "fallback_used": False,
                "fallback_error_type": None,
            }
            return stack.retriever, stack.encoder
        except Exception as exception:
            logger.exception(
                "Dense retrieval unavailable; using BM25 fallback requested_method=%s error_type=%s",
                self._config.retrieval_method,
                type(exception).__name__,
            )
            self._retrieval_method = "bm25-fallback"
            self._retriever_runtime = {
                "requested_method": self._config.retrieval_method,
                "effective_method": self._retrieval_method,
                "embedding_model": self._config.embedding_model,
                "fallback_used": True,
                "fallback_error_type": type(exception).__name__,
            }
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
        # Guidance sections must not reach the model as *evidence*: the claim
        # verifier grounds claims against evidence, so a claim quoting brand-voice
        # would verify successfully and be shown to the guest.  The behaviour they
        # describe is already carried by the system prompt.
        results = [
            item for item in results if getattr(item.chunk, "is_customer_facing", True)
        ]
        return [
            {
                "source": item.chunk.source,
                "title": item.chunk.title,
                "content": item.chunk.content,
                "score": item.score,
                "tags": list(item.chunk.tags),
                "chunk_id": item.chunk.chunk_id,
                "document_id": item.chunk.document_id,
                "parent_id": item.chunk.parent_id,
                "section_path": list(item.chunk.section_path),
                "content_hash": item.chunk.content_hash,
                "risk_tier": item.chunk.risk_tier,
                "valid_from": item.chunk.valid_from,
                "valid_to": item.chunk.valid_to,
            }
            for item in results
        ]

    @property
    def cache_stats(self) -> dict:
        return self._cache.stats

    def invalidate_cache(self) -> None:
        self._cache.invalidate()

    async def chat(self, payload: dict) -> dict:
        with capture_model_attempts() as collector:
            response, _stages = await self._process_chat(payload)
        return _attach_model_route(response, collector.snapshot(), self._config)

    async def chat_stream(self, payload: dict) -> AsyncIterator[dict[str, Any]]:
        with capture_model_attempts() as collector:
            async for event in self._chat_stream_untraced(payload):
                if event["type"] == "final":
                    event = {
                        **event,
                        "data": _attach_model_route(
                            event["data"],
                            collector.snapshot(),
                            self._config,
                        ),
                    }
                yield event

    async def _chat_stream_untraced(
        self,
        payload: dict,
    ) -> AsyncIterator[dict[str, Any]]:
        message = str(payload.get("message") or "").strip()
        security_response = _try_security_guardrail_response(
            message,
            pipeline_version=self._config.pipeline_version,
        )
        if security_response is not None:
            security_response = _finalize_response_payload(
                security_response,
                _minimal_context(payload, self._config.pipeline_version, intent="security"),
            )
            yield {"type": "token", "data": {"text": security_response["content"]}}
            yield {"type": "final", "data": security_response}
            yield {"type": "done", "data": {"ok": True}}
            return
        if _should_use_deterministic_fast_paths(self._config):
            smalltalk = try_smalltalk(message)
            if smalltalk is not None:
                stages = {"total": 0.0, "path": "smalltalk"}
                smalltalk["latency_ms"] = stages
                smalltalk = _finalize_response_payload(
                    smalltalk,
                    _minimal_context(payload, self._config.pipeline_version, intent="smalltalk"),
                )
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

        should_call_llm = _resolve_should_call_llm(
            self._config,
            context,
            client_available=self._client is not None,
        )
        if self._client is None or not should_call_llm:
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
        context["generation_input_sha256"] = _generation_input_sha256(messages)

        accumulated = ""
        llm_started = time.perf_counter()
        try:
            async with asyncio.timeout(self._config.llm_timeout_seconds):
                async for delta in self._client.complete_stream(messages):
                    accumulated += delta
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
        if response.get("content"):
            yield {"type": "token", "data": {"text": response["content"]}}
        yield {"type": "final", "data": response}
        yield {"type": "done", "data": {"ok": True}}

    async def _process_chat(self, payload: dict) -> tuple[dict, dict[str, float]]:
        started = time.perf_counter()
        message = str(payload.get("message") or "").strip()

        security_response = _try_security_guardrail_response(
            message,
            pipeline_version=self._config.pipeline_version,
        )
        if security_response is not None:
            stages = {
                "total": round((time.perf_counter() - started) * 1000, 1),
                "path": "guardrail",
            }
            security_response["latency_ms"] = stages
            security_response = _finalize_response_payload(
                security_response,
                _minimal_context(payload, self._config.pipeline_version, intent="security"),
            )
            return security_response, stages

        if _should_use_deterministic_fast_paths(self._config):
            smalltalk = try_smalltalk(message)
            if smalltalk is not None:
                stages = {
                    "total": round((time.perf_counter() - started) * 1000, 1),
                    "path": "smalltalk",
                }
                smalltalk["latency_ms"] = stages
                smalltalk = _finalize_response_payload(
                    smalltalk,
                    _minimal_context(payload, self._config.pipeline_version, intent="smalltalk"),
                )
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

        should_call_llm = _resolve_should_call_llm(
            self._config,
            context,
            client_available=self._client is not None,
        )
        if self._client is not None and should_call_llm:
            messages = _build_llm_messages(message, context, payload)
            context["generation_input_sha256"] = _generation_input_sha256(messages)
            llm_started = time.perf_counter()
            try:
                async with asyncio.timeout(self._config.llm_timeout_seconds):
                    raw_answer = await self._client.complete(messages)
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

        if provider_available and _should_use_deterministic_fast_paths(self._config):
            self._cache.put(
                message,
                context["source_ids"],
                response,
                session_id=context["session_id"],
                exclusion_ids=context["exclusion_list"],
                menu_version=context["menu_version"],
                index_version=self._config.rag_config_id,
                prompt_version=self._config.pipeline_version,
                model_version=self._config.model,
                cacheable=context["cacheable"],
            )

        stages["total"] = round((time.perf_counter() - started) * 1000, 1)
        if provider_available:
            stages["path"] = "llm"
        elif not should_call_llm:
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
        session_state = payload.get("session_state") or {}
        live_context = payload.get("live_context") or {}
        session_memory = _session_memory_with_typed_ledger(
            str(payload.get("session_memory") or "").strip(),
            session_state,
        )
        rolling_summary = str(
            payload.get("rolling_summary") or session_state.get("rolling_summary") or ""
        ).strip()
        menu_items = payload.get("menu_items") or live_context.get("menu_items") or []
        session_id = str(payload.get("session_id") or "").strip()
        menu_version = str(
            payload.get("catalog_version")
            or live_context.get("catalog_version")
            or payload.get("menu_version")
            or ""
        ).strip()
        facts = payload.get("facts") or session_state.get("facts") or []
        cart_items = payload.get("cart_items") or live_context.get("cart_items") or []
        orders = payload.get("orders") or live_context.get("orders") or []
        promotions = payload.get("promotions") or live_context.get("promotions") or []
        local_time = payload.get("local_time") or live_context.get("local_time")
        meal_period = payload.get("meal_period") or live_context.get("meal_period")

        extract_started = time.perf_counter()
        constraints = _merge_typed_constraints(
            session_state.get("constraints") or {},
            extract_constraints(message, history),
        )
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
        if policy.party_size is None and constraints.get("party_size"):
            policy = replace(policy, party_size=int(constraints["party_size"]))
        intent_result = classify_intent_for_message(message, history)
        intent_flags: list[str] = []

        # So sánh món là tra bảng, không phải suy luận. Đặt trước live-data vì
        # live-data chỉ tra được MỘT món và sẽ chiếm câu hỏi hai món trước khi
        # tới đây. Chỉ kích hoạt khi khách đã nêu tên từ hai món trở lên, nên
        # câu một món hoặc câu mơ hồ vẫn đi đúng đường cũ.
        comparison_response = try_dish_comparison_fast_path(message, menu_items)
        if comparison_response is not None:
            comparison_response["latency_ms"] = {**stages, "path": "dish_comparison"}
            available = [item for item in menu_items if bool(item.get("is_available", True))]
            return {
                "early_response": comparison_response,
                "stages": stages,
                "policy": policy,
                "available_menu_items": available,
                "message": message,
                "history": history,
                "rolling_summary": rolling_summary,
                "facts": facts,
                "session_state": session_state,
                "constraints": constraints,
                "intent": intent_result.intent,
                "pipeline_version": self._config.pipeline_version,
                "pipeline_profile": self._config.pipeline_profile,
                "model": self._config.model,
                "retriever_runtime": self.retriever_runtime,
            }

        live_response = _try_live_data_response(
            message,
            history,
            session_state,
            menu_items,
            pipeline_version=self._config.pipeline_version,
        )
        if live_response is not None:
            stages["extract"] = round((time.perf_counter() - extract_started) * 1000, 1)
            available = [item for item in menu_items if bool(item.get("is_available", True))]
            return {
                "early_response": live_response,
                "stages": stages,
                "policy": policy,
                "available_menu_items": available,
                "message": message,
                "history": history,
                "rolling_summary": rolling_summary,
                "facts": facts,
                "session_state": session_state,
                "constraints": constraints,
                "intent": intent_result.intent,
                "pipeline_version": self._config.pipeline_version,
                "pipeline_profile": self._config.pipeline_profile,
                "model": self._config.model,
                "retriever_runtime": self.retriever_runtime,
            }
        if (
            self._config.pipeline_profile == "planner_state_v3"
            and self._client is not None
        ):
            planner_started = time.perf_counter()
            plan = await plan_with_llm(
                self._client,
                message,
                history,
                session_state,
                timeout_seconds=self._config.intent_classification_timeout_seconds,
            )
            stages["semantic_planner"] = round(
                (time.perf_counter() - planner_started) * 1000,
                1,
            )
            if plan is None:
                intent_flags.append("SEMANTIC_PLANNER_DEGRADED")
            else:
                applied = apply_semantic_plan(
                    plan,
                    session_state=session_state,
                    constraints=constraints,
                )
                constraints = applied.constraints
                session_state = {
                    **session_state,
                    "constraints": constraints,
                    "conversation_frame": applied.frame,
                    "memory_version": "v2",
                }
                policy = build_conversation_policy(
                    message,
                    history,
                    _session_memory_with_typed_ledger(session_memory, session_state),
                    menu_items,
                    category=constraints.get("category"),
                    variation_seed=session_id or message,
                )
                if policy.party_size is None and constraints.get("party_size"):
                    policy = replace(policy, party_size=int(constraints["party_size"]))
                intent_result = replace(
                    intent_result,
                    intent=plan.intent,
                    confidence=max(intent_result.confidence, plan.confidence),
                )
                if applied.frame.get("pending_clarification") is not None:
                    clarification = ChatResponse(
                        content=(
                            "Bạn muốn nói tới món nào? Hãy chọn hoặc nói rõ tên món "
                            "để mình tra đúng thông tin."
                        ),
                        provider_available=True,
                        model=self._config.model,
                        pipeline_version=self._config.pipeline_version,
                        pipeline_profile=self._config.pipeline_profile,
                        decision={
                            "intent": plan.intent,
                            "route": "clarify",
                            "confidence": plan.confidence,
                            "evidence_sufficient": False,
                            "abstain_reason": "semantic_plan_needs_clarification",
                        },
                        session_updates={
                            "constraints": constraints,
                            "conversation_frame": applied.frame,
                            "memory_version": "v2",
                        },
                        latency_ms={"path": "clarify"},
                    ).model_dump()
                    stages["extract"] = round(
                        (time.perf_counter() - extract_started) * 1000,
                        1,
                    )
                    return {
                        "early_response": clarification,
                        "stages": stages,
                        "policy": policy,
                        "available_menu_items": [
                            item
                            for item in menu_items
                            if bool(item.get("is_available", True))
                        ],
                        "message": message,
                        "history": history,
                        "rolling_summary": rolling_summary,
                        "facts": facts,
                        "session_state": session_state,
                        "constraints": constraints,
                        "intent": intent_result.intent,
                        "pipeline_version": self._config.pipeline_version,
                        "pipeline_profile": self._config.pipeline_profile,
                        "model": self._config.model,
                        "retriever_runtime": self.retriever_runtime,
                    }
                live_response = _try_live_data_response(
                    message,
                    history,
                    session_state,
                    menu_items,
                    pipeline_version=self._config.pipeline_version,
                )
                if live_response is not None:
                    stages["extract"] = round(
                        (time.perf_counter() - extract_started) * 1000,
                        1,
                    )
                    available = [
                        item
                        for item in menu_items
                        if bool(item.get("is_available", True))
                    ]
                    return {
                        "early_response": live_response,
                        "stages": stages,
                        "policy": policy,
                        "available_menu_items": available,
                        "message": message,
                        "history": history,
                        "rolling_summary": rolling_summary,
                        "facts": facts,
                        "session_state": session_state,
                        "constraints": constraints,
                        "intent": intent_result.intent,
                        "pipeline_version": self._config.pipeline_version,
                        "pipeline_profile": self._config.pipeline_profile,
                        "model": self._config.model,
                        "retriever_runtime": self.retriever_runtime,
                    }
        if (
            self._config.pipeline_profile != "planner_state_v3"
            and
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
            for item_id in (
                list(payload.get("excluded_menu_item_ids") or [])
                + list(session_state.get("rejected_menu_item_ids") or [])
            )
            if str(item_id).strip()
        )
        allergen_context = bool(constraints.get("allergens")) and (
            policy.wants_recommendations
            or has_allergy_avoidance_context(message)
        )
        allergen_excluded = (
            frozenset(
                infer_allergen_excluded_menu_item_ids(constraints["allergens"], menu_items)
            )
            if allergen_context
            else frozenset()
        )
        # Food for a young child: keep only dishes the catalogue marks as
        # child-friendly.  Without this the assistant will happily suggest an
        # adult dish (rare beef, heavy spice) for a toddler.
        child_context = has_child_dining_context(message)
        child_excluded = (
            frozenset(infer_child_unsuitable_menu_item_ids(menu_items))
            if child_context
            else frozenset()
        )
        excluded_ids = (
            policy.excluded_menu_item_ids
            | payload_excluded
            | allergen_excluded
            | child_excluded
        )
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

        fast_path_context = {
            "message": message,
            "history": history,
            "session_memory": session_memory,
            "rolling_summary": rolling_summary,
            "session_id": session_id,
            "menu_version": menu_version,
            "facts": facts,
            "session_state": session_state,
            "constraints": constraints,
            "intent": intent_result.intent,
            "pipeline_version": self._config.pipeline_version,
            "pipeline_profile": self._config.pipeline_profile,
            "model": self._config.model,
            "retriever_runtime": self.retriever_runtime,
            "available_menu_items": available_menu_items,
        }

        menu_presence_response = try_menu_presence_fast_path(
            message,
            available_menu_items,
            wants_recommendations=policy.wants_recommendations,
        )
        if menu_presence_response is not None:
            menu_presence_response["latency_ms"] = {**stages, "path": "menu_presence"}
            return _early_context_response(
                menu_presence_response,
                stages,
                policy,
                available_menu_items,
                context=fast_path_context,
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

        use_deterministic_fast_paths = _should_use_deterministic_fast_paths(self._config)
        if _should_use_evidence_first_menu_paths(self._config):
            catalog_response = _try_catalog_fast_path(message, constraints, menu_items, excluded_ids)
            if catalog_response is not None:
                catalog_response["latency_ms"] = {**stages, "path": "catalog_fast_path"}
                return _early_context_response(
                    catalog_response,
                    stages,
                    policy,
                    available_menu_items,
                    context=fast_path_context,
                )

        if use_deterministic_fast_paths:
            party_fast_path = try_party_recommendation_fast_path(
                constraints,
                policy,
                # Prefer full menu when party size is known so ranking/policy can work
                # even if sparse text retrieval returns few/no candidates.
                available_menu_items if party_size else candidate_menu_items,
            )
            if party_fast_path is not None:
                party_fast_path["latency_ms"] = {**stages, "path": "party_fast_path"}
                return _early_context_response(
                    party_fast_path,
                    stages,
                    policy,
                    available_menu_items,
                    context=fast_path_context,
                )

            pairing_fast_path = try_pairing_recommendation_fast_path(
                message,
                intent=intent_result.intent,
                policy=policy,
                menu_items=available_menu_items,
            )
            if pairing_fast_path is not None:
                pairing_fast_path["latency_ms"] = {**stages, "path": "pairing_fast_path"}
                return _early_context_response(
                    pairing_fast_path,
                    stages,
                    policy,
                    available_menu_items,
                    context=fast_path_context,
                )

        rewrite_started = time.perf_counter()
        rewritten = rewrite_query(
            message,
            history,
            intent=intent_result,
            session_state=session_state,
            rolling_summary=rolling_summary,
        )
        search_query = rewritten if rewritten != message else message
        stages["rewrite"] = round((time.perf_counter() - rewrite_started) * 1000, 1)

        intent = intent_result
        rag_top_k = 5 if intent.intent in RECOMMEND_INTENTS or intent.intent in FAQ_POLICY_INTENTS else 3

        retrieval_started = time.perf_counter()
        # This calls the retriever directly rather than through the wrapper above,
        # so it needs the audience filter of its own.  Without it an allergy
        # question came back with three of five evidence slots filled by guidance
        # ("Lưu Ý Cho AI", brand-voice "Trả lời dị ứng", "Không Được Nói"), leaving
        # the model with instructions instead of facts — it then asked the guest to
        # supply the menu it already had.
        retrieved = [
            item
            for item in self._retriever.search(search_query, rag_top_k)
            # getattr: test doubles supply their own chunk type, and a chunk with
            # no declared audience is a guest-facing fact, not guidance.
            if getattr(item.chunk, "is_customer_facing", True)
        ]
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
            # Deterministic FAQ/policy answers (hours, wifi, parking, payment, ...)
            # are never a hallucination risk and never need cross-turn context, so
            # — like menu_presence_fast_path above — they run regardless of
            # llm_first. Recommendation-type intents are already excluded inside
            # try_kb_info_fast_path, so this does not affect llm_first's context
            # handling for recommendation flows.
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
            return _early_context_response(
                kb_fast_path,
                stages,
                policy,
                available_menu_items,
                context={
                    **fast_path_context,
                    "retrieved": retrieved,
                    "chunks": chunks,
                    "confidence_score": confidence.score,
                },
            )

        budget_picks: list[dict[str, Any]] = []
        if constraints.get("budget_vnd"):
            budget_picks = solve_budget(
                menu_items,
                int(constraints["budget_vnd"]),
                constraints.get("party_size"),
                excluded_ids=excluded_ids,
            )

        if use_deterministic_fast_paths:
            budget_fast_path = try_budget_recommendation_fast_path(
                constraints,
                policy,
                candidate_menu_items,
                budget_picks,
            )
            if budget_fast_path is not None:
                budget_fast_path["latency_ms"] = {**stages, "path": "budget_fast_path"}
                return _early_context_response(
                    budget_fast_path,
                    stages,
                    policy,
                    available_menu_items,
                    context={
                        **fast_path_context,
                        "retrieved": retrieved,
                        "chunks": chunks,
                        "confidence_score": confidence.score,
                    },
                )

        source_ids = [item.chunk.chunk_id for item in retrieved[:3]]
        cacheable = _is_cacheable(constraints)
        cached = None
        if use_deterministic_fast_paths:
            cached = self._cache.get(
                message,
                source_ids,
                session_id=session_id,
                exclusion_ids=exclusion_list,
                menu_version=menu_version,
                index_version=self._config.rag_config_id,
                prompt_version=self._config.pipeline_version,
                model_version=self._config.model,
                cacheable=cacheable,
            )
        if cached is not None:
            stages["total"] = round((time.perf_counter() - started) * 1000, 1)
            cached["latency_ms"] = {**stages, "path": "cache_hit"}
            cached.pop("session_updates", None)
            cached.pop("updated_rolling_summary", None)
            return {
                "cached_response": cached,
                "stages": stages,
                **fast_path_context,
                "retrieved": retrieved,
                "chunks": chunks,
                "confidence_score": confidence.score,
            }

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
            "should_call_llm": (
                True
                if self._config.llm_first and self._config.llm_enabled
                else confidence.should_call_llm
            ),
            "confidence_level": confidence.level,
            "intent": intent.intent,
            "session_state": session_state,
            "pipeline_version": self._config.pipeline_version,
            "pipeline_profile": self._config.pipeline_profile,
            "model": self._config.model,
            "retriever_runtime": self.retriever_runtime,
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
            index_version=service._config.rag_config_id,
            prompt_version=service._config.pipeline_version,
            model_version=service._config.model,
            cacheable=context["cacheable"],
        )
    return response


def _build_menu_based_fallback(
    context: dict[str, Any],
) -> tuple[str, list[dict], list[str]] | None:
    """When 9router fails, still suggest real menu items for recommendation queries."""

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


def _generation_input_sha256(messages: list[dict[str, str]]) -> str:
    """Fingerprint the exact provider input without persisting prompt or user text."""

    canonical = json.dumps(
        messages,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _early_context_response(
    early_response: dict[str, Any],
    stages: dict[str, float],
    policy: Any,
    available_menu_items: list[dict[str, Any]],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from app.rag.content_grounding import strip_menu_ids

    if early_response.get("content"):
        early_response["content"] = strip_menu_ids(str(early_response["content"]))
    result = {
        "early_response": early_response,
        "stages": stages,
        "policy": policy,
        "available_menu_items": available_menu_items,
    }
    if context:
        result.update(context)
    return result


def _finalize_suggested_actions(
    context: dict[str, Any],
    suggested_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    early_response = context.get("early_response") or {}
    decision = early_response.get("decision") or {}
    if decision.get("evidence_sufficient") is False:
        return []
    if decision.get("intent") in {"ask_price", "nutrition_info", "allergy_info"}:
        return suggested_actions
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
            context["candidate_menu_items"],
            context["policy"],
        )

    suggested_actions = _finalize_suggested_actions(context, suggested_actions)
    evidence_menu_items = (
        context["candidate_menu_items"]
        if context["policy"].wants_recommendations
        else context["available_menu_items"]
    )

    content, grounding_flags, suggested_actions = ground_response_content(
        parsed.content,
        suggested_actions,
        evidence_menu_items,
        wants_recommendations=context["policy"].wants_recommendations,
    )
    merged_flags = _dedupe([*flags, *parsed.guardrail_flags, *grounding_flags])
    verified_claims, claims_verified = verify_claims(
        parsed.claims,
        chunks=context["chunks"],
        menu_items=evidence_menu_items,
    )
    context["claims"] = verified_claims
    if not claims_verified and suggested_actions:
        # The model prose/claim can be unsafe even when the returned cards are
        # valid live-menu records. Replace only the unsafe model claim with
        # deterministic menu evidence; do not discard a safe result.
        content = format_grounded_recommendation_content(suggested_actions)
        context["claims"] = _claims_from_menu_actions(suggested_actions)
        merged_flags = _dedupe(
            [*merged_flags, "MODEL_CLAIM_REPLACED_WITH_LIVE_MENU_EVIDENCE"]
        )
    elif not claims_verified:
        content = (
            "Mình chưa đủ bằng chứng để xác nhận câu trả lời đó. "
            "Bạn có thể nói rõ món/thông tin cần kiểm tra, hoặc nhờ nhân viên xác nhận giúp."
        )
        suggested_actions = []
        merged_flags = _dedupe([*merged_flags, "UNSUPPORTED_CLAIM_BLOCKED", "EVIDENCE_INSUFFICIENT"])
        context["abstain_reason"] = "unsupported_claim"
        context["evidence_sufficient"] = False
    if suggested_actions:
        merged_flags = _dedupe([*merged_flags, "CUSTOMER_CONFIRMATION_REQUIRED"])
    return content, suggested_actions, merged_flags


def _minimal_context(payload: dict[str, Any], pipeline_version: str, *, intent: str) -> dict[str, Any]:
    state = payload.get("session_state") or {}
    return {
        "message": str(payload.get("message") or ""),
        "rolling_summary": str(payload.get("rolling_summary") or state.get("rolling_summary") or ""),
        "facts": payload.get("facts") or state.get("facts") or [],
        "session_state": state,
        "constraints": state.get("constraints") or {},
        "intent": intent,
        "pipeline_version": pipeline_version,
        "pipeline_profile": str(payload.get("pipeline_profile") or "llm_first_v1"),
        "available_menu_items": (
            payload.get("menu_items")
            or (payload.get("live_context") or {}).get("menu_items")
            or []
        ),
    }


def _route_from_path(path: str, evidence: list[dict[str, Any]]) -> str:
    if path in {"smalltalk", "guardrail"}:
        return "deterministic"
    if path in {"catalog_fast_path", "party_fast_path", "budget_fast_path", "pairing_fast_path"}:
        return "live_data"
    if path == "kb_fast_path":
        return "kb_rag"
    if path in {"llm", "fallback", "fallback_no_llm", "cache_hit"}:
        sources = {str(item.get("source") or "") for item in evidence}
        return "live_data" if sources and sources <= {"live_menu"} else "kb_rag"
    return "kb_rag" if evidence else "abstain"


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
        updates = dict(response.get("session_updates") or {})
        updates["rolling_summary"] = updated
        response["session_updates"] = updates
    return response


def _finalize_response_payload(
    response: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    response.setdefault("contract_version", "v2")
    response.setdefault("pipeline_version", str(context.get("pipeline_version") or "v2"))
    response["pipeline_profile"] = str(
        context.get("pipeline_profile")
        or response.get("pipeline_profile")
        or "llm_first_v1"
    )
    if context.get("model"):
        response.setdefault("model", str(context["model"]))
    if context.get("retriever_runtime") is not None:
        response["retriever_runtime"] = dict(context["retriever_runtime"])
    if context.get("generation_input_sha256"):
        response.setdefault("generation_input_sha256", str(context["generation_input_sha256"]))
    path = str((response.get("latency_ms") or {}).get("path") or "")
    if response.get("provider_available"):
        response["provider_status"] = "available"
    elif "AI_PROVIDER_UNAVAILABLE" in (response.get("guardrail_flags") or []):
        response["provider_status"] = "unavailable"
    else:
        response["provider_status"] = "not_called"

    claims = list(response.get("claims") or [])
    if not claims and response.get("suggested_cart_actions"):
        claims = _claims_from_menu_actions(response["suggested_cart_actions"])
    response["claims"] = claims

    policy = context.get("policy")
    wants_recommendations_this_turn = bool(getattr(policy, "wants_recommendations", False))
    if wants_recommendations_this_turn and not response.get("suggested_cart_actions"):
        # Only ever backfill on a turn the policy already flagged as wanting a
        # fresh recommendation — never on a follow-up/confirmation turn, where
        # a claim may cite a previously-suggested dish just to verify a fact
        # (e.g. its price) without re-recommending it (would break the
        # duplicate-free-suggestion session guarantee).
        backfilled_actions = _backfill_cart_actions_from_verified_claims(
            claims,
            context.get("available_menu_items") or [],
            excluded_ids=context.get("excluded_ids") or frozenset(),
        )
        if backfilled_actions:
            response["suggested_cart_actions"] = backfilled_actions

    evidence = list(response.get("evidence") or [])
    evidence = _merge_verified_claim_evidence(
        evidence,
        claims,
        context.get("available_menu_items") or [],
    )
    if not evidence:
        for source in response.get("retrieved_sources") or []:
            evidence.append(
                {
                    "source": source.get("source") or "knowledge_base",
                    "title": source.get("title"),
                    "chunk_id": source.get("chunk_id"),
                    "section": " / ".join(source.get("section_path") or []),
                    "score": source.get("score"),
                }
            )
        for action in response.get("suggested_cart_actions") or []:
            evidence.append(
                {
                    "source": "live_menu",
                    "menu_item_id": action.get("menu_item_id"),
                    "title": action.get("name"),
                    "score": 1.0,
                }
            )
        response["evidence"] = evidence
    else:
        response["evidence"] = evidence

    if not response.get("decision"):
        route = _route_from_path(path, evidence)
        response["decision"] = {
            "intent": context.get("intent"),
            "route": route,
            "confidence": context.get("confidence_score"),
            "evidence_sufficient": route == "deterministic" or bool(evidence),
            "abstain_reason": None if route == "deterministic" or evidence else "insufficient_evidence",
        }
    decision = dict(response.get("decision") or {})
    evidence_ids = {
        str(value).strip()
        for item in evidence
        for value in (item.get("chunk_id"), item.get("menu_item_id"))
        if value and str(value).strip()
    }
    live_menu_evidence_ids = {
        str(item.get("menu_item_id")).strip()
        for item in evidence
        if item.get("menu_item_id")
    }
    resolved_menu_item_ids: list[str] = []
    for action in response.get("suggested_cart_actions") or []:
        item_id = str(action.get("menu_item_id") or "").strip()
        if (
            item_id
            and item_id in live_menu_evidence_ids
            and item_id not in resolved_menu_item_ids
        ):
            resolved_menu_item_ids.append(item_id)
    for claim in claims:
        if not claim.get("verified"):
            continue
        for raw_id in claim.get("evidence_ids") or []:
            item_id = str(raw_id).strip()
            if (
                item_id in live_menu_evidence_ids
                and item_id not in resolved_menu_item_ids
            ):
                resolved_menu_item_ids.append(item_id)
    response["resolved_menu_item_ids"] = resolved_menu_item_ids
    claims_valid = all(
        bool(claim.get("verified"))
        and bool(claim.get("evidence_ids"))
        and set(str(value).strip() for value in claim.get("evidence_ids") or [])
        <= evidence_ids
        for claim in claims
    )  # empty claims → all() = True → pass
    if (
        path not in {"smalltalk", "guardrail", "clarify", "fallback", "live_data"}
        and decision.get("evidence_sufficient") is not False
        and claims
        and not claims_valid
    ):
        response["content"] = (
            "Mình chưa đủ bằng chứng đã kiểm chứng để trả lời chắc chắn. "
            "Bạn vui lòng nói rõ thông tin cần kiểm tra hoặc nhờ nhân viên xác nhận giúp."
        )
        response["suggested_cart_actions"] = []
        response["guardrail_flags"] = _dedupe(
            [
                *(response.get("guardrail_flags") or []),
                "UNSUPPORTED_CLAIM_BLOCKED",
                "EVIDENCE_INSUFFICIENT",
            ]
        )
        decision.update(
            {
                "route": "abstain",
                "evidence_sufficient": False,
                "abstain_reason": (
                    "missing_verified_claims" if not claims else "unverified_claims"
                ),
            }
        )
        response["decision"] = decision
    response["verifier_result"] = (
        "passed"
        if claims and all(bool(claim.get("verified")) for claim in claims)
        else ("failed" if claims else "not_applicable")
    )
    if context.get("abstain_reason"):
        decision = dict(response.get("decision") or {})
        decision.update(
            {
                "route": "abstain",
                "evidence_sufficient": False,
                "abstain_reason": context["abstain_reason"],
            }
        )
        response["decision"] = decision

    state = context.get("session_state") or {}
    updates = dict(response.get("session_updates") or {})
    updates.setdefault("facts", list(context.get("facts") or state.get("facts") or []))
    updates["constraints"] = dict(context.get("constraints") or state.get("constraints") or {})
    frame = dict(state.get("conversation_frame") or {})
    # Which dish the conversation is currently about is ordinary conversational
    # state, not a planner feature.  Gating this on planner_state_v3 left the
    # other two profiles with an empty frame, so an ordinal follow-up ("món thứ
    # hai giá bao nhiêu?", then "thêm món đó vào giỏ") answered correctly but
    # resolved "món đó" against nothing on the next turn.  resolved_menu_item_ids
    # is computed above for every profile, so every profile can carry the frame.
    resolved_ids = list(response.get("resolved_menu_item_ids") or [])
    if resolved_ids and frame.get("pending_clarification") is None:
        frame["focus_menu_item_ids"] = resolved_ids
    updates["conversation_frame"] = frame
    updates["referenced_menu_item_ids"] = _merge_id_lists(
        state.get("referenced_menu_item_ids") or [],
        updates.get("referenced_menu_item_ids") or [],
    )
    updates["suggested_menu_item_ids"] = _merge_id_lists(
        state.get("suggested_menu_item_ids") or [],
        updates.get("suggested_menu_item_ids") or [],
        [
            str(action.get("menu_item_id"))
            for action in (response.get("suggested_cart_actions") or [])
            if action.get("menu_item_id")
        ],
    )
    updates["rejected_menu_item_ids"] = _merge_id_lists(
        state.get("rejected_menu_item_ids") or [],
        updates.get("rejected_menu_item_ids") or [],
        list(getattr(context.get("policy"), "rejected_ids", ()) or ()),
    )
    updates["accepted_menu_item_ids"] = _merge_id_lists(
        state.get("accepted_menu_item_ids") or [],
        updates.get("accepted_menu_item_ids") or [],
    )
    updates["added_to_cart_menu_item_ids"] = _merge_id_lists(
        state.get("added_to_cart_menu_item_ids") or [],
        updates.get("added_to_cart_menu_item_ids") or [],
    )
    updates.setdefault(
        "memory_version",
        (
            "v2"
            if response.get("pipeline_profile") == "planner_state_v3"
            else str(state.get("memory_version") or "v1")
        ),
    )
    response["session_updates"] = updates

    return _attach_rolling_summary(
        response,
        context,
        content=str(response.get("content") or ""),
        suggested_actions=list(response.get("suggested_cart_actions") or []),
    )


def _merge_verified_claim_evidence(
    evidence: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    menu_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = list(evidence)
    existing_ids = {
        str(value).strip()
        for item in result
        for value in (item.get("chunk_id"), item.get("menu_item_id"))
        if value and str(value).strip()
    }
    menu_by_id = {
        _item_id(item): item
        for item in menu_items
        if _item_id(item)
    }
    for claim in claims:
        if not claim.get("verified"):
            continue
        for raw_id in claim.get("evidence_ids") or []:
            evidence_id = str(raw_id).strip()
            item = menu_by_id.get(evidence_id)
            if not item or evidence_id in existing_ids:
                continue
            result.append(
                {
                    "source": "live_menu",
                    "menu_item_id": evidence_id,
                    "title": str(item.get("name") or "Món"),
                    "score": 1.0,
                }
            )
            existing_ids.add(evidence_id)
    return result


def _backfill_cart_actions_from_verified_claims(
    claims: list[dict[str, Any]],
    menu_items: list[dict[str, Any]],
    *,
    excluded_ids: frozenset[str] | set[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Attach a cart-suggestion card whenever the model already verified a claim
    about a real, available dish but forgot to add suggested_cart_actions.

    Without this, an LLM answer can name/discuss a specific menu item (e.g. when
    confirming availability or describing a dish) without giving the customer an
    actionable way to add it to the cart — every real-dish mention should be.
    Only called on turns already flagged as wanting a fresh recommendation, and
    skips anything already suggested/rejected (HARD EXCLUSION) this session.
    """
    menu_by_id = {_item_id(item): item for item in menu_items if _item_id(item)}
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for claim in claims:
        if not claim.get("verified"):
            continue
        for raw_id in claim.get("evidence_ids") or []:
            item_id = str(raw_id).strip()
            if not item_id or item_id in seen or item_id in excluded_ids:
                continue
            item = menu_by_id.get(item_id)
            if not item or not bool(item.get("is_available", True)):
                continue
            seen.add(item_id)
            actions.append(
                {
                    "menu_item_id": item_id,
                    "name": str(item.get("name") or "Món"),
                    "price_vnd": item.get("price_vnd") or item.get("price"),
                    "quantity": 1,
                    "reason": "Được nhắc đến trong câu trả lời",
                    "requires_customer_confirmation": True,
                }
            )
    return actions[:MAX_CATALOG_CART_SUGGESTIONS]


def _claims_from_menu_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for action in actions:
        item_id = str(action.get("menu_item_id") or action.get("id") or "").strip()
        name = str(action.get("name") or "").strip()
        if not item_id or not name:
            continue
        price = action.get("price_vnd") or action.get("price")
        text = f"{name} có trong thực đơn hiện tại"
        if isinstance(price, (int, float)):
            text += f" với giá {int(price):,} đồng".replace(",", ".")
        claims.append(
            {
                "text": text + ".",
                "evidence_ids": [item_id],
                "verified": True,
                "reason": None,
            }
        )
    return claims


def _merge_id_lists(*groups: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group or []:
            item_id = str(value).strip()
            if item_id and item_id not in seen:
                seen.add(item_id)
                result.append(item_id)
    return result


def _session_memory_with_typed_ledger(
    session_memory: str,
    session_state: dict[str, Any],
) -> str:
    lines = [session_memory] if session_memory else []
    for label, key in (
        ("SUGGESTED_MENU_ITEM_IDS", "suggested_menu_item_ids"),
        ("REJECTED_MENU_ITEM_IDS", "rejected_menu_item_ids"),
    ):
        values = [
            str(value).strip()
            for value in (session_state.get(key) or [])
            if str(value).strip()
        ]
        if values:
            lines.append(f"{label}: {','.join(values)}")
    return "\n".join(lines)


def _merge_typed_constraints(
    state_constraints: dict[str, Any],
    extracted: dict[str, Any],
) -> dict[str, Any]:
    """Keep durable typed facts when Last-N history no longer contains them."""

    result = dict(extracted)
    for key in ("party_size", "budget_vnd", "category"):
        if result.get(key) is None and state_constraints.get(key) is not None:
            result[key] = state_constraints[key]
    for key in ("allergens", "diet"):
        if not result.get(key) and state_constraints.get(key):
            value = state_constraints[key]
            result[key] = list(value) if isinstance(value, (list, tuple, set)) else value
    if result.get("spice") in (None, "unknown") and state_constraints.get("spice") not in (
        None,
        "unknown",
    ):
        result["spice"] = state_constraints["spice"]
    return result


def _try_security_guardrail_response(
    message: str,
    *,
    pipeline_version: str,
) -> dict[str, Any] | None:
    flags = detect_guardrail_flags(message)
    if "PROMPT_INJECTION_BLOCKED" not in flags:
        return None
    return ChatResponse(
        content=(
            "Mình chỉ hỗ trợ thông tin nhà hàng và thực đơn. "
            "Mình không thể thực hiện yêu cầu thay đổi quy tắc hoặc tiết lộ cấu hình nội bộ."
        ),
        provider_available=False,
        provider_status="not_called",
        model="deterministic-security-guardrail",
        pipeline_version=pipeline_version,
        decision={
            "intent": "security",
            "route": "deterministic",
            "confidence": 1.0,
            "evidence_sufficient": True,
            "abstain_reason": None,
        },
        guardrail_flags=flags,
        latency_ms={"path": "guardrail"},
    ).model_dump()


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
                chunk_id=item.chunk.chunk_id,
                document_id=item.chunk.document_id,
                section_path=list(item.chunk.section_path),
            )
            for item in retrieved
        ],
        guardrail_flags=flags,
        suggested_cart_actions=suggested_actions,
        follow_up=follow_up,
        suggest_staff_handoff=suggest_staff_handoff,
        latency_ms=stages,
        claims=list((context or {}).get("claims") or []),
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


def _try_live_data_response(
    message: str,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
    menu_items: list[dict[str, Any]],
    *,
    pipeline_version: str,
) -> dict[str, Any] | None:
    normalized = normalize_query_text(message)
    nutrition_terms = ("calo", "calorie", "dinh duong", "duong", "sugar", "protein", "chat dam")
    price_terms = ("bao nhieu", "gia bao", "gia tien", "price", "cost")
    allergen_terms = ("di ung", "allerg", "dau phong", "tom", "cua", "hai san", "gluten", "sua", "trung")
    reference_terms = ("mon do", "mon nay", "cai do", "cai nay", "that one")
    names_in_query = any(
        item.get("name") and normalize_query_text(str(item["name"])) in normalized
        for item in menu_items
    )
    is_nutrition = any(term in normalized for term in nutrition_terms)
    is_price = any(term in normalized for term in price_terms) and not is_nutrition
    is_allergy = (
        any(term in normalized for term in allergen_terms)
        and (any(term in normalized for term in reference_terms) or names_in_query)
    )
    if not is_nutrition and not is_price and not is_allergy:
        return None

    item = _resolve_live_menu_item(message, history, session_state, menu_items)
    if item is None:
        return _live_response(
            content="Bạn đang hỏi món nào? Hãy chọn hoặc nói rõ tên món để mình tra dữ liệu trực tiếp.",
            intent="allergy_info" if is_allergy else ("nutrition_info" if is_nutrition else "ask_price"),
            evidence_sufficient=False,
            abstain_reason="unresolved_reference",
            pipeline_version=pipeline_version,
            item=None,
            claims=[],
        )

    item_id = str(item.get("id") or "")
    name = str(item.get("name") or "món này")
    if is_allergy:
        if "allergens" not in item and "ingredients" not in item:
            response = _live_response(
                content=f"Mình chưa có dữ liệu thành phần/dị ứng đáng tin cậy cho {name}. Nếu bạn có dị ứng, vui lòng hỏi nhân viên để xác nhận trực tiếp với bếp trước khi dùng món.",
                intent="allergy_info",
                evidence_sufficient=False,
                abstain_reason="missing_live_allergen_data",
                pipeline_version=pipeline_version,
                item=item,
                claims=[],
            )
            response["guardrail_flags"] = _dedupe(
                [*response["guardrail_flags"], "ALLERGY_DISCLAIMER"]
            )
            return response

        recorded = normalize_query_text(
            " ".join(
                [
                    *[str(value) for value in (item.get("allergens") or [])],
                    *[str(value) for value in (item.get("ingredients") or [])],
                ]
            )
        )
        matched = [term for term in allergen_terms if term in normalized and term in recorded]
        if matched:
            claim = f"Dữ liệu menu ghi nhận {name} có {', '.join(matched)}. Bạn nên tránh món và xác nhận lại với nhân viên/bếp."
            response = _live_response(
                content=claim,
                intent="allergy_info",
                evidence_sufficient=True,
                abstain_reason=None,
                pipeline_version=pipeline_version,
                item=item,
                claims=[{"text": claim, "evidence_ids": [item_id], "verified": True}],
            )
        else:
            response = _live_response(
                content=f"Dữ liệu hiện tại không ghi nhận dị nguyên bạn hỏi cho {name}, nhưng điều này không đủ để xác nhận món an toàn. Vui lòng hỏi nhân viên/bếp.",
                intent="allergy_info",
                evidence_sufficient=False,
                abstain_reason="allergy_requires_staff_confirmation",
                pipeline_version=pipeline_version,
                item=item,
                claims=[],
            )
        response["guardrail_flags"] = _dedupe(
            [*response["guardrail_flags"], "ALLERGY_DISCLAIMER"]
        )
        return response

    if is_price:
        if item.get("price_vnd") is None:
            return _live_response(
                content=f"Mình chưa có dữ liệu giá đáng tin cậy cho {name}. Bạn vui lòng kiểm tra menu hoặc hỏi nhân viên.",
                intent="ask_price",
                evidence_sufficient=False,
                abstain_reason="missing_live_price_data",
                pipeline_version=pipeline_version,
                item=item,
                claims=[],
            )
        price = int(float(item["price_vnd"]))
        availability = "hiện còn bán" if bool(item.get("is_available", True)) else "hiện đang hết"
        claim = f"{name} có giá {price:,} đồng và {availability}.".replace(",", ".")
        return _live_response(
            content=claim,
            intent="ask_price",
            evidence_sufficient=True,
            abstain_reason=None,
            pipeline_version=pipeline_version,
            item=item,
            claims=[{"text": claim, "evidence_ids": [item_id], "verified": True}],
        )

    requested_fields: list[tuple[str, str, str]] = []
    if "calo" in normalized or "calorie" in normalized:
        requested_fields.append(("calories_kcal", "năng lượng", "kcal"))
    if "duong" in normalized or "sugar" in normalized:
        requested_fields.append(("sugar_g", "đường", "g"))
    if "protein" in normalized or "chat dam" in normalized:
        requested_fields.append(("protein_g", "protein", "g"))
    if not requested_fields:
        requested_fields = [
            ("calories_kcal", "năng lượng", "kcal"),
            ("sugar_g", "đường", "g"),
            ("protein_g", "protein", "g"),
        ]
    available_values = [field for field in requested_fields if item.get(field[0]) is not None]
    if len(available_values) != len(requested_fields):
        return _live_response(
            content=f"Mình chưa có dữ liệu dinh dưỡng đáng tin cậy cho {name}; mình không đoán số calo, đường hoặc protein. Bạn vui lòng hỏi nhân viên.",
            intent="nutrition_info",
            evidence_sufficient=False,
            abstain_reason="missing_live_nutrition_data",
            pipeline_version=pipeline_version,
            item=item,
            claims=[],
        )
    facts = [f"{label} {item[key]} {unit}" for key, label, unit in available_values]
    claim = f"Theo dữ liệu menu hiện tại, {name} có " + ", ".join(facts) + "."
    return _live_response(
        content=claim,
        intent="nutrition_info",
        evidence_sufficient=True,
        abstain_reason=None,
        pipeline_version=pipeline_version,
        item=item,
        claims=[{"text": claim, "evidence_ids": [item_id], "verified": True}],
    )


def _resolve_live_menu_item(
    message: str,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
    menu_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    by_id = {str(item.get("id") or ""): item for item in menu_items if item.get("id")}
    normalized = normalize_query_text(message)
    explicit = [
        item
        for item in menu_items
        if item.get("name") and normalize_query_text(str(item["name"])) in normalized
    ]
    if explicit:
        return max(explicit, key=lambda item: len(str(item.get("name") or "")))

    ordinal = _referent_ordinal(normalized)
    if ordinal is not None:
        # The most recent assistant cards are exactly the list the guest saw,
        # unlike the cumulative session ledger.  Preserve their display order
        # so "món thứ hai" cannot silently resolve to the most recent item.
        for turn in reversed(history):
            if str(turn.get("role") or "").casefold() != "assistant":
                continue
            displayed_ids = [
                str(action.get("menu_item_id") or "").strip()
                for action in (turn.get("suggested_cart_actions") or [])
                if isinstance(action, dict)
                and str(action.get("menu_item_id") or "").strip() in by_id
            ]
            if ordinal <= len(displayed_ids):
                return by_id[displayed_ids[ordinal - 1]]
            break

        suggested_ids = [
            str(value).strip()
            for value in (session_state.get("suggested_menu_item_ids") or [])
            if str(value).strip() in by_id
        ]
        if ordinal <= len(suggested_ids):
            return by_id[suggested_ids[ordinal - 1]]

    candidate_ids: list[str] = []
    frame = session_state.get("conversation_frame") or {}
    candidate_ids.extend(
        str(value)
        for value in (frame.get("focus_menu_item_ids") or [])
        if str(value).strip()
    )
    for turn in reversed(history):
        for action in reversed(list(turn.get("suggested_cart_actions") or [])):
            candidate_ids.append(str(action.get("menu_item_id") or ""))
    for key in (
        "referenced_menu_item_ids",
        "accepted_menu_item_ids",
        "suggested_menu_item_ids",
        "added_to_cart_menu_item_ids",
    ):
        candidate_ids.extend(reversed([str(value) for value in (session_state.get(key) or [])]))
    return next((by_id[item_id] for item_id in candidate_ids if item_id in by_id), None)


def _referent_ordinal(normalized_message: str) -> int | None:
    """Return a 1-based ordinal when the guest refers to an earlier item."""

    match = re.search(
        r"\b(?:mon\s+)?(?:thu|so)\s*(\d+|mot|hai|ba|bon|nam|sau|bay|tam)\b",
        normalized_message,
    )
    if not match:
        return None
    raw = match.group(1)
    if raw.isdigit():
        value = int(raw)
        return value if value > 0 else None
    return {
        "mot": 1,
        "hai": 2,
        "ba": 3,
        "bon": 4,
        "nam": 5,
        "sau": 6,
        "bay": 7,
        "tam": 8,
    }.get(raw)


def _live_response(
    *,
    content: str,
    intent: str,
    evidence_sufficient: bool,
    abstain_reason: str | None,
    pipeline_version: str,
    item: dict[str, Any] | None,
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    item_id = str((item or {}).get("id") or "")
    evidence = (
        [
            {
                "source": "live_menu",
                "title": (item or {}).get("name"),
                "menu_item_id": item_id,
                "score": 1.0,
            }
        ]
        if item is not None
        else []
    )
    flags = [] if evidence_sufficient else ["EVIDENCE_INSUFFICIENT"]
    return {
        "contract_version": "v2",
        "content": content,
        "provider_available": False,
        "provider_status": "not_called",
        "model": "deterministic-live-data",
        "pipeline_version": pipeline_version,
        "retrieved_sources": [],
        "decision": {
            "intent": intent,
            "route": "live_data" if item is not None else "clarify",
            "confidence": 1.0 if evidence_sufficient else 0.0,
            "evidence_sufficient": evidence_sufficient,
            "abstain_reason": abstain_reason,
        },
        "evidence": evidence,
        "claims": claims,
        "session_updates": {
            "referenced_menu_item_ids": [item_id] if item_id else [],
        },
        "guardrail_flags": flags,
        "suggested_cart_actions": [],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": not evidence_sufficient,
        "latency_ms": {"path": "live_data" if item is not None else "clarify"},
    }


def _try_catalog_fast_path(
    message: str,
    constraints: dict[str, Any],
    menu_items: list[dict[str, Any]],
    excluded_ids: frozenset[str],
) -> dict[str, Any] | None:
    if "CUSTOMER_CONFIRMATION_REQUIRED" in detect_guardrail_flags(message):
        return None
    if not constraints.get("is_catalog_only"):
        normalized = normalize_query_text(message)
        browse_category = (
            not constraints.get("is_recommendation")
            and any(
                marker in normalized
                # "co gi"/"gom gi" ("what do you have") is one of the most common
                # ways to browse a category and was missing, so those questions
                # fell through to the LLM and came back as a counter-question.
                # Safe to add: a category must still be detected below, so a
                # bare "có gì không?" (no category) never reaches this path.
                for marker in (
                    "xem", "cac mon", "co nhung mon", "menu", "thuc don",
                    "co gi", "gom gi", "gom nhung gi", "danh sach",
                )
            )
        )
        if not browse_category:
            return None
    if not constraints.get("category"):
        return None
    # Session party_size / prior soft criteria must not block category listing.
    if constraints.get("is_recommendation") or constraints.get("budget_vnd"):
        return None
    from app.rag.constraint_extractor import has_hard_dietary_constraints

    effective_constraints = dict(constraints)
    if not has_allergy_avoidance_context(message):
        # Browsing "món hải sản" names a category; it is not an allergy request.
        effective_constraints["allergens"] = []
    if str(constraints.get("category") or "") == "mon chay":
        # Same idea for diet: "món chay có gì" states the category being browsed,
        # it is not an extra filter to apply on top of it.  Listing the Món chay
        # category is exactly what a vegetarian/vegan browse asks for, so these
        # diet tags must not disqualify the deterministic listing.
        effective_constraints["diet"] = [
            value
            for value in (effective_constraints.get("diet") or [])
            if value not in {"vegetarian", "vegan"}
        ]
    if has_hard_dietary_constraints(effective_constraints):
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
    cited_items = matched[:12]
    catalog_suggested_actions = [
        {
            "menu_item_id": _item_id(item),
            "name": str(item.get("name") or "Món").strip(),
            "price_vnd": item.get("price_vnd") or item.get("price"),
            "quantity": 1,
            "reason": build_suggestion_reason(item, seed=_item_id(item)),
            "requires_customer_confirmation": True,
        }
        for item in cited_items[:MAX_CATALOG_CART_SUGGESTIONS]
        if _item_id(item)
    ]
    return ChatResponse(
        content=content,
        provider_available=False,
        model="deterministic-catalog",
        retrieved_sources=[],
        evidence=[
            {
                "source": "live_menu",
                "menu_item_id": _item_id(item),
                "title": str(item.get("name") or "Món"),
                "score": 1.0,
            }
            for item in cited_items
            if _item_id(item)
        ],
        claims=_claims_from_menu_actions(
            [
                {
                    "menu_item_id": _item_id(item),
                    "name": item.get("name") or "Món",
                    "price_vnd": item.get("price_vnd") or item.get("price"),
                }
                for item in cited_items
                if _item_id(item)
            ]
        ),
        guardrail_flags=[],
        suggested_cart_actions=catalog_suggested_actions,
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
    elif category not in active_aliases:
        # The alias that matched the *question* is not necessarily the one that
        # matches the *menu*: a guest writing "chay thuan" or "seafood" still
        # means the "mon chay"/"hai san" category, whose category_name in the
        # live menu is the canonical term.  Keep the matched alias (it decides
        # relevance) but always allow the canonical one for the menu-side match.
        active_aliases = [*active_aliases, category]
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
