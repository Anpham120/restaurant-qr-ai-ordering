"""Shared helpers for golden chat / LLM end-to-end evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import AiServiceConfig, load_config
from app.services.assistant import AiAssistantService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
GOLDEN_PATH = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"
MENU_DATASET_PATH = PROJECT_ROOT / "backend" / "data" / "menu-dataset.json"


def load_golden_cases(
    split: str | None = None,
    *,
    families: set[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with GOLDEN_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if split is not None and case.get("split") != split:
                continue
            if families is not None and case.get("family") not in families:
                continue
            cases.append(case)
            if limit is not None and len(cases) >= limit:
                break
    return cases


def load_menu_items() -> list[dict[str, Any]]:
    payload = json.loads(MENU_DATASET_PATH.read_text(encoding="utf-8-sig"))
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "description": item.get("description") or "",
            "category_id": item.get("categoryId") or "",
            "category_name": item.get("categoryName") or "",
            "price_vnd": item.get("price"),
            "tags": list(item.get("tags") or []),
            "is_available": bool(item.get("isAvailable", True)),
        }
        for item in payload["items"]
    ]


def build_offline_service(retrieval_method: str, embedding_model: str) -> AiAssistantService:
    config = AiServiceConfig(
        provider="none",
        base_url="",
        api_key="",
        model="offline-eval",
        llm_timeout_seconds=1,
        request_budget_seconds=2,
        max_retry=0,
        max_tokens=700,
        reasoning_effort="low",
        knowledge_base_path=AI_ROOT / "knowledge-base",
        top_k=5,
        retrieval_method=retrieval_method,
        embedding_model=embedding_model,
    )
    return AiAssistantService(config, llm_client=None)


def build_llm_service(
    *,
    retrieval_method: str | None = None,
    embedding_model: str | None = None,
    llm_client: Any | None = None,
    max_retry: int | None = None,
) -> AiAssistantService:
    config = load_config()
    if retrieval_method is not None or max_retry is not None:
        config = AiServiceConfig(
            provider=config.provider,
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            llm_timeout_seconds=config.llm_timeout_seconds,
            request_budget_seconds=config.request_budget_seconds,
            max_retry=config.max_retry if max_retry is None else max_retry,
            max_tokens=config.max_tokens,
            reasoning_effort=config.reasoning_effort,
            knowledge_base_path=AI_ROOT / "knowledge-base",
            top_k=config.top_k,
            retrieval_method=retrieval_method or config.retrieval_method,
            embedding_model=embedding_model or config.embedding_model,
        )
    elif embedding_model is not None:
        config = AiServiceConfig(
            provider=config.provider,
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
            llm_timeout_seconds=config.llm_timeout_seconds,
            request_budget_seconds=config.request_budget_seconds,
            max_retry=config.max_retry,
            max_tokens=config.max_tokens,
            reasoning_effort=config.reasoning_effort,
            knowledge_base_path=AI_ROOT / "knowledge-base",
            top_k=config.top_k,
            retrieval_method=config.retrieval_method,
            embedding_model=embedding_model,
        )
    if not config.llm_enabled and llm_client is None:
        raise RuntimeError(
            "LLM evaluation requires GEMINI_API_KEY and AI_MODEL in ai/.env "
            "(or pass a mock llm_client in tests)."
        )
    return AiAssistantService(config, llm_client=llm_client)


def score_pipeline_case(case: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Pipeline metrics shared by offline and LLM golden eval."""

    expected_flags = set(case.get("safety_flags") or [])
    detected_flags = set(response.get("guardrail_flags") or [])
    missing_flags = sorted(expected_flags - detected_flags)

    suggested = response.get("suggested_cart_actions") or []
    suggested_ids = [str(action.get("menu_item_id") or "") for action in suggested]
    forbidden_ids = set(case.get("forbidden_menu_ids") or [])
    forbidden_hits = sorted(set(suggested_ids) & forbidden_ids)

    retrieved = [
        f"{source.get('source')}::{source.get('title')}"
        for source in (response.get("retrieved_sources") or [])
    ]
    retrieved_files = {str(source.get("source")) for source in (response.get("retrieved_sources") or [])}
    expected_chunks = [item for item in (case.get("expected_chunk_ids") or []) if item]
    expected_files = {chunk.split("::", 1)[0] for chunk in expected_chunks}
    chunk_hit = any(chunk in retrieved for chunk in expected_chunks) if expected_chunks else None
    source_hit = bool(expected_files & retrieved_files) if expected_chunks else None

    expected_menu = set(case.get("expected_menu_ids") or [])
    if expected_menu == {"LIVE_MENU"}:
        menu_hit = bool(suggested_ids)
    elif expected_menu:
        menu_hit = bool(expected_menu & set(suggested_ids))
    else:
        menu_hit = None

    return {
        "id": case["id"],
        "family": case.get("family"),
        "intent": case.get("intent"),
        "query": case["query"],
        "safety_flags_expected": sorted(expected_flags),
        "safety_flags_missing": missing_flags,
        "safety_pass": not missing_flags,
        "forbidden_suggestions": forbidden_hits,
        "forbidden_pass": not forbidden_hits,
        "expected_chunk_hit": chunk_hit,
        "expected_source_hit": source_hit,
        "expected_menu_hit": menu_hit,
        "suggested_menu_ids": suggested_ids,
        "content_length": len(response.get("content") or ""),
        "guardrail_flags_detected": sorted(detected_flags),
        "provider_available": bool(response.get("provider_available")),
    }
