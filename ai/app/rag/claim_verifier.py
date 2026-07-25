from __future__ import annotations

import re
from typing import Any, Sequence

from app.rag.knowledge_base import KnowledgeChunk
from app.rag.vietnamese_normalizer import normalize_query_text


NUMBER_PATTERN = re.compile(r"\d[\d.,:]*")


def verify_claims(
    claims: Sequence[dict[str, Any]],
    *,
    chunks: Sequence[KnowledgeChunk],
    menu_items: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    evidence = _evidence_map(chunks, menu_items)
    verified_claims: list[dict[str, Any]] = []
    for raw_claim in claims:
        text = str(raw_claim.get("text") or "").strip()
        evidence_ids = [
            str(value).strip()
            for value in (raw_claim.get("evidence_ids") or [])
            if str(value).strip()
        ]
        verified, reason = _verify_one(text, evidence_ids, evidence)
        verified_claims.append(
            {
                "text": text,
                "evidence_ids": evidence_ids,
                "verified": verified,
                "reason": reason,
            }
        )
    return verified_claims, all(
        claim["verified"] for claim in verified_claims
    )  # empty list → all() = True → pass (nothing to verify)


def _evidence_map(
    chunks: Sequence[KnowledgeChunk], menu_items: Sequence[dict[str, Any]]
) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in chunks:
        text = f"{chunk.title}\n{chunk.content}\n{' '.join(chunk.tags)}"
        result[chunk.chunk_id] = text
        result[f"{chunk.source}::{chunk.title}"] = text
    for item in menu_items:
        item_id = str(item.get("id") or item.get("menu_item_id") or "").strip()
        item_name = str(item.get("name") or "").strip()
        fields = [
            item.get("name"),
            item.get("description"),
            item.get("category_name") or item.get("category"),
            item.get("price_vnd") or item.get("price"),
            item.get("is_available"),
            " ".join(str(value) for value in (item.get("tags") or [])),
            " ".join(str(value) for value in (item.get("ingredients") or [])),
            " ".join(str(value) for value in (item.get("allergens") or [])),
            item.get("calories_kcal"),
            item.get("sugar_g"),
            item.get("protein_g"),
        ]
        text = " ".join(str(value) for value in fields if value is not None)
        if item_id:
            result[item_id] = text
        if item_name:
            result[item_name] = text
    return result


def _verify_one(
    text: str, evidence_ids: list[str], evidence: dict[str, str]
) -> tuple[bool, str | None]:
    if not text or not evidence_ids:
        return False, "missing_evidence_id"
    unknown = [evidence_id for evidence_id in evidence_ids if evidence_id not in evidence]
    if unknown:
        return False, "unknown_evidence_id"

    support = " ".join(evidence[evidence_id] for evidence_id in evidence_ids)
    claim_numbers = {_normalize_number(value) for value in NUMBER_PATTERN.findall(text)}
    evidence_numbers = {_normalize_number(value) for value in NUMBER_PATTERN.findall(support)}
    claim_numbers.discard("")
    evidence_numbers.discard("")
    if claim_numbers and not claim_numbers.issubset(evidence_numbers):
        return False, "numeric_value_not_in_evidence"

    claim_tokens = _significant_tokens(text)
    evidence_tokens = _significant_tokens(support)
    if not claim_tokens or len(claim_tokens & evidence_tokens) / len(claim_tokens) < 0.25:
        return False, "insufficient_lexical_support"
    return True, None


def _normalize_number(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return digits.lstrip("0") or ("0" if digits else "")


def _significant_tokens(value: str) -> set[str]:
    stopwords = {"co", "la", "va", "theo", "hien", "tai", "dong", "mon", "nay"}
    return {
        token
        for token in normalize_query_text(value).split()
        if len(token) >= 2 and token not in stopwords
    }
