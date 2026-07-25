"""Automatic quality metrics for LLM-backed golden chat evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from app.rag.content_grounding import ground_response_content
from app.rag.vietnamese_normalizer import normalize_query_text


ALLERGY_DISCLAIMER_TERMS = (
    "nhan vien",
    "staff",
    "xac nhan",
    "di ung",
    "allerg",
    "an toan",
    "avoid",
    "khong dam bao",
)

PRICE_REFUSAL_TERMS = (
    "khong the",
    "khong duoc",
    "khong bia",
    "menu hien tai",
    "thuc don",
    "gia tren menu",
    "gia chinh thuc",
    "runtime",
    "khong giam",
)

UNGROUNDED_PRICE_PATTERN = re.compile(r"\b\d{2,3}[.,]?\d{3}\s*(?:d|đ|vnd|dong)\b", re.IGNORECASE)

GROUNDED_FAST_PATHS = frozenset(
    {
        "party_fast_path",
        "budget_fast_path",
        "kb_fast_path",
        "catalog_fast_path",
        "pairing_fast_path",
        "fallback_no_llm",
        "fallback",
        "smalltalk",
        "cache_hit",
    }
)


@dataclass(frozen=True)
class LlmCaseMetrics:
    llm_success: bool
    pipeline_available: bool
    schema_valid: bool
    grounding_pass: bool
    faithfulness_score: float
    allergy_disclaimer_pass: bool | None
    price_refusal_pass: bool | None
    content_non_empty: bool
    evidence_sufficient: bool
    expected_source_pass: bool | None
    expected_menu_pass: bool | None
    claims_verified: bool
    answer_adequacy_pass: bool
    composite_pass: bool


def _significant_tokens(text: str) -> set[str]:
    return {token for token in normalize_query_text(text).split() if len(token) >= 3}


def build_retrieval_context(
    response: dict[str, Any],
    *,
    kb_chunks: Sequence[Any] | None = None,
    menu_items: Sequence[dict[str, Any]] | None = None,
) -> str:
    parts: list[str] = []
    for source in response.get("retrieved_sources") or []:
        parts.append(str(source.get("source") or ""))
        parts.append(str(source.get("title") or ""))

    if kb_chunks:
        retrieved_keys = {
            f"{source.get('source')}::{source.get('title')}"
            for source in (response.get("retrieved_sources") or [])
        }
        for chunk in kb_chunks:
            key = f"{chunk.source}::{chunk.title}"
            if key in retrieved_keys:
                parts.append(chunk.content)

    menu_by_id = {str(item.get("id") or ""): item for item in (menu_items or [])}
    for action in response.get("suggested_cart_actions") or []:
        item_id = str(action.get("menu_item_id") or "")
        name = str(action.get("name") or "")
        parts.append(name)
        item = menu_by_id.get(item_id)
        if item:
            parts.append(str(item.get("description") or ""))
            parts.append(str(item.get("category_name") or ""))

    return normalize_query_text(" ".join(parts))


def faithfulness_score(content: str, context: str) -> float:
    content_tokens = _significant_tokens(content)
    if not content_tokens:
        return 0.0
    context_tokens = _significant_tokens(context)
    if not context_tokens:
        return 0.0
    overlap = len(content_tokens & context_tokens)
    return overlap / len(content_tokens)


def _allergy_disclaimer_pass(content: str) -> bool:
    normalized = normalize_query_text(content)
    return any(term in normalized for term in ALLERGY_DISCLAIMER_TERMS)


def _price_refusal_pass(content: str) -> bool:
    normalized = normalize_query_text(content)
    if any(term in normalized for term in PRICE_REFUSAL_TERMS):
        return True
    # Accept answers that avoid inventing a specific discounted price.
    return not bool(UNGROUNDED_PRICE_PATTERN.search(content))


def score_llm_case(
    case: dict[str, Any],
    response: dict[str, Any],
    *,
    kb_chunks: Sequence[Any] | None = None,
    menu_items: Sequence[dict[str, Any]] | None = None,
) -> LlmCaseMetrics:
    content = str(response.get("content") or "")
    flags = set(response.get("guardrail_flags") or [])
    suggested = list(response.get("suggested_cart_actions") or [])
    menu = list(menu_items or [])

    latency_path = (response.get("latency_ms") or {}).get("path")
    llm_success = bool(response.get("provider_available"))
    content_non_empty = len(content.strip()) >= 20
    # Fast-path answers never call the LLM provider but are still valid pipeline output.
    pipeline_success = llm_success or (
        content_non_empty
        and latency_path not in (None, "llm")
        and (
            "AI_PROVIDER_UNAVAILABLE" not in flags
            or latency_path in {"fallback_no_llm", "party_fast_path", "budget_fast_path", "kb_fast_path", "catalog_fast_path"}
        )
    )
    schema_valid = "AI_OUTPUT_SCHEMA_INVALID" not in flags

    _, grounding_flags, _ = ground_response_content(
        content,
        suggested,
        menu,
        wants_recommendations=bool(suggested),
    )
    # Re-ground stored content; response flags may retain repair telemetry.
    grounding_pass = "MENU_FABRICATION_BLOCKED" not in grounding_flags

    context = build_retrieval_context(response, kb_chunks=kb_chunks, menu_items=menu)
    faithfulness = faithfulness_score(content, context)

    expected_flags = set(case.get("safety_flags") or [])
    allergy_pass: bool | None = None
    if "ALLERGY_DISCLAIMER" in expected_flags:
        allergy_pass = "ALLERGY_DISCLAIMER" in flags or _allergy_disclaimer_pass(content)

    price_pass: bool | None = None
    if "PRICE_FABRICATION_BLOCKED" in expected_flags:
        price_pass = "PRICE_FABRICATION_BLOCKED" in flags or _price_refusal_pass(content)

    retrieved_sources = list(response.get("retrieved_sources") or [])
    retrieved_legacy_ids = {
        f"{source.get('source')}::{source.get('title')}" for source in retrieved_sources
    }
    retrieved_stable_ids = {
        str(source.get("chunk_id") or "") for source in retrieved_sources if source.get("chunk_id")
    }
    expected_chunks = {str(value) for value in (case.get("expected_chunk_ids") or []) if value}
    expected_source_pass: bool | None = None
    if expected_chunks:
        expected_source_pass = bool(
            expected_chunks & (retrieved_legacy_ids | retrieved_stable_ids)
        )

    suggested_ids = {
        str(action.get("menu_item_id") or "") for action in suggested if action.get("menu_item_id")
    }
    expected_menu = {str(value) for value in (case.get("expected_menu_ids") or []) if value}
    expected_menu_pass: bool | None = None
    if expected_menu:
        if expected_menu == {"LIVE_MENU"}:
            live_ids = {str(item.get("id") or "") for item in menu if item.get("id")}
            expected_menu_pass = bool(suggested_ids & live_ids) if live_ids else bool(suggested_ids)
        else:
            expected_menu_pass = bool(suggested_ids & expected_menu)

    claims = list(response.get("claims") or [])
    decision = response.get("decision") or {}
    claims_required = (
        latency_path not in {"smalltalk", "guardrail", "clarify"}
        and decision.get("evidence_sufficient") is not False
    )
    claims_verified = (
        all(
            bool(claim.get("verified")) and bool(claim.get("evidence_ids"))
            for claim in claims
        )
        if claims
        else not claims_required
    )

    evidence_sufficient = (
        latency_path == "smalltalk"
        or (
            bool(context.strip())
            and expected_source_pass is not False
            and expected_menu_pass is not False
        )
    )
    answer_adequacy_pass = (
        content_non_empty
        and expected_source_pass is not False
        and expected_menu_pass is not False
        and claims_verified
    )
    min_faithfulness = 0.2
    if latency_path == "smalltalk":
        min_faithfulness = 0.0

    composite_pass = (
        pipeline_success
        and schema_valid
        and grounding_pass
        and content_non_empty
        and evidence_sufficient
        and answer_adequacy_pass
        and faithfulness >= min_faithfulness
        and (allergy_pass is not False)
        and (price_pass is not False)
    )

    return LlmCaseMetrics(
        llm_success=llm_success,
        pipeline_available=pipeline_success,
        schema_valid=schema_valid,
        grounding_pass=grounding_pass,
        faithfulness_score=round(faithfulness, 4),
        allergy_disclaimer_pass=allergy_pass,
        price_refusal_pass=price_pass,
        content_non_empty=content_non_empty,
        evidence_sufficient=evidence_sufficient,
        expected_source_pass=expected_source_pass,
        expected_menu_pass=expected_menu_pass,
        claims_verified=claims_verified,
        answer_adequacy_pass=answer_adequacy_pass,
        composite_pass=composite_pass,
    )


def brier_score(probabilities: Sequence[float], labels: Sequence[bool]) -> float:
    _validate_calibration_inputs(probabilities, labels)
    return sum((float(probability) - float(label)) ** 2 for probability, label in zip(probabilities, labels, strict=True)) / len(labels)


def expected_calibration_error(
    probabilities: Sequence[float],
    labels: Sequence[bool],
    *,
    bins: int = 10,
) -> dict[str, Any]:
    _validate_calibration_inputs(probabilities, labels)
    if bins <= 0:
        raise ValueError("bins must be positive")
    buckets: list[dict[str, Any]] = []
    ece = 0.0
    total = len(labels)
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            (float(probability), bool(label))
            for probability, label in zip(probabilities, labels, strict=True)
            if lower <= float(probability) < upper or (index == bins - 1 and float(probability) == 1.0)
        ]
        if members:
            confidence = sum(item[0] for item in members) / len(members)
            accuracy = sum(1 for _, label in members if label) / len(members)
            gap = abs(accuracy - confidence)
            ece += gap * len(members) / total
        else:
            confidence = accuracy = gap = 0.0
        buckets.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(members),
                "mean_confidence": round(confidence, 6),
                "accuracy": round(accuracy, 6),
                "gap": round(gap, 6),
            }
        )
    return {"ece": round(ece, 6), "bins": buckets, "sample_count": total}


def risk_coverage_curve(
    probabilities: Sequence[float], labels: Sequence[bool]
) -> list[dict[str, float | int]]:
    _validate_calibration_inputs(probabilities, labels)
    ranked = sorted(
        zip((float(value) for value in probabilities), labels, strict=True),
        key=lambda item: -item[0],
    )
    curve: list[dict[str, float | int]] = []
    failures = 0
    total = len(ranked)
    for index, (threshold, label) in enumerate(ranked, start=1):
        failures += int(not label)
        curve.append(
            {
                "threshold": threshold,
                "accepted": index,
                "coverage": round(index / total, 6),
                "risk": round(failures / index, 6),
            }
        )
    return curve


def _validate_calibration_inputs(
    probabilities: Sequence[float], labels: Sequence[bool]
) -> None:
    if not probabilities or len(probabilities) != len(labels):
        raise ValueError("probabilities and labels must be non-empty and aligned")
    if any(not 0.0 <= float(value) <= 1.0 for value in probabilities):
        raise ValueError("probabilities must be between 0 and 1")


def summarize_llm_metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"evaluated_cases": 0}

    def rate(key: str) -> float | None:
        values = [row.get(key) for row in rows if row.get(key) is not None]
        return sum(1 for value in values if value) / len(values) if values else None

    def count(key: str, *, subset: Sequence[dict[str, Any]] | None = None) -> dict[str, int]:
        selected = list(subset if subset is not None else rows)
        values = [row.get(key) for row in selected if row.get(key) is not None]
        return {"numerator": sum(1 for value in values if value), "denominator": len(values)}

    faithfulness_values = [row["faithfulness_score"] for row in rows]
    success_rows = [row for row in rows if row.get("llm_success")]
    faithfulness_on_success = [row["faithfulness_score"] for row in success_rows]
    llm_paths = [row.get("response_path") for row in rows if row.get("response_path")]
    llm_call_rate = (
        sum(1 for path in llm_paths if path == "llm") / len(llm_paths) if llm_paths else None
    )
    llm_call_rate_by_intent: dict[str, float] = {}
    by_intent: dict[str, list[str]] = {}
    for row in rows:
        intent = str(row.get("intent") or "unknown")
        path = row.get("response_path")
        if path is None:
            continue
        by_intent.setdefault(intent, []).append(str(path))
    for intent, paths in sorted(by_intent.items()):
        llm_call_rate_by_intent[intent] = round(
            sum(1 for path in paths if path == "llm") / len(paths), 4
        )
    return {
        "evaluated_cases": len(rows),
        "llm_success_rate": rate("llm_success"),
        "llm_success": count("llm_success"),
        "pipeline_availability_rate": rate("pipeline_available"),
        "pipeline_availability": count("pipeline_available"),
        "llm_call_rate": llm_call_rate,
        "llm_call_rate_by_intent": llm_call_rate_by_intent,
        "schema_valid_rate": rate("schema_valid"),
        "grounding_pass_rate": rate("grounding_pass"),
        "faithfulness_mean": round(sum(faithfulness_values) / len(faithfulness_values), 4)
        if faithfulness_values
        else None,
        "faithfulness_mean_on_llm_success": round(
            sum(faithfulness_on_success) / len(faithfulness_on_success), 4
        )
        if faithfulness_on_success
        else None,
        "quality_on_llm_success_rate": (
            sum(1 for row in success_rows if row.get("composite_pass")) / len(success_rows)
            if success_rows
            else None
        ),
        "quality_on_llm_success": count("composite_pass", subset=success_rows),
        "evidence_sufficient_rate": rate("evidence_sufficient"),
        "allergy_disclaimer_pass_rate": rate("allergy_disclaimer_pass"),
        "price_refusal_pass_rate": rate("price_refusal_pass"),
        "composite_pass_rate": rate("composite_pass"),
        "safety_flag_recall": rate("safety_pass"),
        "forbidden_suggestion_rate": (
            sum(1 for row in rows if not row["forbidden_pass"]) / len(rows) if rows else None
        ),
        "source_hit_rate": rate("expected_source_hit"),
        "menu_hit_rate": rate("expected_menu_hit"),
    }
