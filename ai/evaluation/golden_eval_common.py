"""Shared helpers for golden chat / LLM end-to-end evaluation."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.config import AiServiceConfig, load_config
from app.services.assistant import AiAssistantService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
GOLDEN_PATH = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"
MENU_DATASET_PATH = PROJECT_ROOT / "backend" / "data" / "menu-dataset.json"
DEFAULT_STRATIFIED_SAMPLING_SEED = 20260722
SAMPLING_STRATEGIES = frozenset({"head", "stratified"})


def load_golden_cases(
    split: str | None = None,
    *,
    families: set[str] | None = None,
    limit: int | None = None,
    sampling_strategy: str = "head",
    sampling_seed: int = DEFAULT_STRATIFIED_SAMPLING_SEED,
) -> list[dict[str, Any]]:
    """Load filtered golden cases with an optional deterministic sampling policy.

    ``head`` preserves the historical file-order behaviour. ``stratified``
    balances a bounded sample across ``(family, intent)`` strata. Both stratum
    and within-stratum order are derived from SHA-256 ranks so the same seed and
    dataset produce exactly the same case IDs and order on every model run.
    """

    if sampling_strategy not in SAMPLING_STRATEGIES:
        expected = ", ".join(sorted(SAMPLING_STRATEGIES))
        raise ValueError(f"Unknown sampling strategy {sampling_strategy!r}; expected one of: {expected}")

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

    if limit is not None and limit <= 0:
        return []
    if sampling_strategy == "head":
        return cases if limit is None else cases[:limit]
    return _stratified_cases(cases, limit=limit, seed=sampling_seed)


def summarize_case_sample(
    cases: list[dict[str, Any]],
    *,
    sampling_strategy: str,
    sampling_seed: int | None,
) -> dict[str, Any]:
    """Return secret-safe, reproducible provenance for an evaluation sample."""

    case_ids = [str(case.get("id") or "") for case in cases]
    return {
        "strategy": sampling_strategy,
        "seed": sampling_seed,
        "case_count": len(cases),
        "family_distribution": _value_distribution(cases, "family"),
        "intent_distribution": _value_distribution(cases, "intent"),
        "case_set_sha256": _sequence_sha256(sorted(case_ids)),
        "case_order_sha256": _sequence_sha256(case_ids),
    }


def _stratified_cases(
    cases: list[dict[str, Any]],
    *,
    limit: int | None,
    seed: int,
) -> list[dict[str, Any]]:
    strata: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for case in cases:
        key = (
            str(case.get("family") or "unknown"),
            str(case.get("intent") or "unknown"),
        )
        strata.setdefault(key, []).append(case)

    ordered_keys = sorted(
        strata,
        key=lambda key: (_stable_rank(seed, "stratum", *key), key),
    )
    for key, rows in strata.items():
        rows.sort(
            key=lambda case: (
                _stable_rank(seed, "case", *key, str(case.get("id") or "")),
                str(case.get("id") or ""),
            )
        )

    target = len(cases) if limit is None else min(limit, len(cases))
    selected: list[dict[str, Any]] = []
    positions = {key: 0 for key in ordered_keys}
    while len(selected) < target:
        added = False
        for key in ordered_keys:
            position = positions[key]
            if position >= len(strata[key]):
                continue
            selected.append(strata[key][position])
            positions[key] = position + 1
            added = True
            if len(selected) >= target:
                break
        if not added:
            break
    return selected


def _stable_rank(seed: int, *parts: str) -> str:
    payload = "\x1f".join((str(seed), *parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sequence_sha256(values: list[str]) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _value_distribution(cases: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(case.get(key) or "unknown") for case in cases)
    return dict(sorted(counts.items()))


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
    # The provider is stubbed out (this path never calls an LLM), but the
    # pipeline profile must still match the deployment: it decides which
    # deterministic paths run, so leaving it at the dataclass default measured a
    # pipeline shape the service does not actually serve.
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
        pipeline_profile=load_config().pipeline_profile,
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
    # Only override what the caller asked for.  Rebuilding AiServiceConfig
    # field-by-field silently dropped every field not listed, so pipeline_profile
    # and llm_first fell back to their dataclass defaults ("llm_first_v1"/True)
    # and the whole eval measured a pipeline the deployment does not run.
    overrides: dict[str, Any] = {"knowledge_base_path": AI_ROOT / "knowledge-base"}
    if retrieval_method is not None:
        overrides["retrieval_method"] = retrieval_method
    if embedding_model is not None:
        overrides["embedding_model"] = embedding_model
    if max_retry is not None:
        overrides["max_retry"] = max_retry
    config = dataclasses.replace(config, **overrides)
    if not config.llm_enabled and llm_client is None:
        raise RuntimeError(
            "LLM evaluation requires LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL in ai/.env "
            "(9router OpenAI-compatible gateway; or pass a mock llm_client in tests)."
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
        "response_path": (response.get("latency_ms") or {}).get("path"),
    }
