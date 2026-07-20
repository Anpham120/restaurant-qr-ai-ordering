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


@dataclass(frozen=True)
class LlmCaseMetrics:
    llm_success: bool
    schema_valid: bool
    grounding_pass: bool
    faithfulness_score: float
    allergy_disclaimer_pass: bool | None
    price_refusal_pass: bool | None
    content_non_empty: bool
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

    llm_success = bool(response.get("provider_available"))
    schema_valid = "AI_OUTPUT_SCHEMA_INVALID" not in flags

    _, grounding_flags, _ = ground_response_content(
        content,
        suggested,
        menu,
        wants_recommendations=bool(suggested),
    )
    grounding_pass = "MENU_FABRICATION_BLOCKED" not in flags and "MENU_FABRICATION_BLOCKED" not in grounding_flags

    context = build_retrieval_context(response, kb_chunks=kb_chunks, menu_items=menu)
    faithfulness = faithfulness_score(content, context)

    expected_flags = set(case.get("safety_flags") or [])
    allergy_pass: bool | None = None
    if "ALLERGY_DISCLAIMER" in expected_flags:
        allergy_pass = "ALLERGY_DISCLAIMER" in flags or _allergy_disclaimer_pass(content)

    price_pass: bool | None = None
    if "PRICE_FABRICATION_BLOCKED" in expected_flags:
        price_pass = "PRICE_FABRICATION_BLOCKED" in flags or _price_refusal_pass(content)

    content_non_empty = len(content.strip()) >= 20

    composite_pass = (
        llm_success
        and schema_valid
        and grounding_pass
        and content_non_empty
        and faithfulness >= 0.08
        and (allergy_pass is not False)
        and (price_pass is not False)
    )

    return LlmCaseMetrics(
        llm_success=llm_success,
        schema_valid=schema_valid,
        grounding_pass=grounding_pass,
        faithfulness_score=round(faithfulness, 4),
        allergy_disclaimer_pass=allergy_pass,
        price_refusal_pass=price_pass,
        content_non_empty=content_non_empty,
        composite_pass=composite_pass,
    )


def summarize_llm_metrics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"evaluated_cases": 0}

    def rate(key: str) -> float | None:
        values = [row[key] for row in rows if row.get(key) is not None]
        return sum(1 for value in values if value) / len(values) if values else None

    faithfulness_values = [row["faithfulness_score"] for row in rows]
    return {
        "evaluated_cases": len(rows),
        "llm_success_rate": rate("llm_success"),
        "schema_valid_rate": rate("schema_valid"),
        "grounding_pass_rate": rate("grounding_pass"),
        "faithfulness_mean": round(sum(faithfulness_values) / len(faithfulness_values), 4)
        if faithfulness_values
        else None,
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
