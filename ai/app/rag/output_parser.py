from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedAiResponse:
    content: str
    suggested_cart_actions: list[dict[str, Any]]
    guardrail_flags: list[str]
    claims: list[dict[str, Any]]


def parse_model_response(
    raw_response: str,
    menu_items: list[dict],
    *,
    excluded_menu_item_ids: frozenset[str] = frozenset(),
    max_actions: int = 8,
) -> ParsedAiResponse | None:
    payload = _extract_json(raw_response)
    if payload is None:
        return None

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        return None

    flags = _normalize_flags(payload.get("guardrail_flags"))
    actions, action_flags = _parse_suggested_actions(
        payload.get("suggested_cart_actions"),
        menu_items,
        excluded_menu_item_ids=excluded_menu_item_ids,
        max_actions=max_actions,
    )
    flags = _dedupe([*flags, *action_flags])
    claims, claim_flags = _parse_claims(payload.get("claims"))
    flags = _dedupe([*flags, *claim_flags])

    return ParsedAiResponse(
        content=_dedupe_repeated_sentences(content),
        suggested_cart_actions=actions,
        guardrail_flags=flags,
        claims=claims,
    )


def _parse_claims(value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], ["AI_OUTPUT_SCHEMA_INVALID"]
    claims: list[dict[str, Any]] = []
    invalid = False
    for claim in value:
        if not isinstance(claim, dict):
            invalid = True
            continue
        text = str(claim.get("text") or "").strip()
        evidence_ids = claim.get("evidence_ids")
        if not text or not isinstance(evidence_ids, list):
            invalid = True
            continue
        claims.append(
            {
                "text": text,
                "evidence_ids": [
                    str(value).strip() for value in evidence_ids if str(value).strip()
                ],
            }
        )
    return claims, (["AI_OUTPUT_SCHEMA_INVALID"] if invalid else [])


def _dedupe_repeated_sentences(content: str) -> str:
    """Remove only repeated response segments while preserving first occurrence."""

    segments = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", content) if segment.strip()]
    seen: set[str] = set()
    unique: list[str] = []
    for segment in segments:
        fingerprint = " ".join(re.findall(r"\w+", segment.casefold()))
        if fingerprint and fingerprint in seen:
            continue
        seen.add(fingerprint)
        unique.append(segment)
    return " ".join(unique).strip() or content.strip()


def _extract_json(raw_response: str) -> dict[str, Any] | None:
    text = (raw_response or "").strip()
    if not text:
        return None

    candidates = [text]
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidates.append(text[first : last + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload

    return None


def _parse_suggested_actions(
    value: Any,
    menu_items: list[dict],
    *,
    excluded_menu_item_ids: frozenset[str],
    max_actions: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], ["AI_OUTPUT_SCHEMA_INVALID"]

    available_by_id = {
        str(item.get("id") or item.get("menu_item_id") or "").strip(): item
        for item in menu_items
        if str(item.get("id") or item.get("menu_item_id") or "").strip()
        and bool(item.get("is_available", True))
    }

    actions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    rejected_count = 0
    for item in value:
        if not isinstance(item, dict):
            rejected_count += 1
            continue

        item_id = str(item.get("menu_item_id") or item.get("id") or "").strip()
        menu_item = available_by_id.get(item_id)
        if item_id in seen_ids:
            continue
        if menu_item is None or item_id in excluded_menu_item_ids:
            rejected_count += 1
            continue

        quantity = _parse_quantity(item.get("quantity"))
        actions.append(
            {
                "menu_item_id": item_id,
                "name": str(item.get("name") or menu_item.get("name") or "").strip(),
                "price_vnd": _parse_price(item.get("price_vnd") or menu_item.get("price_vnd") or menu_item.get("price")),
                "quantity": quantity,
                "reason": _clean_optional_string(item.get("reason")),
                "requires_customer_confirmation": True,
            }
        )
        seen_ids.add(item_id)
        if len(actions) == max(0, max_actions):
            break

    flags: list[str] = []
    if actions:
        flags.append("CUSTOMER_CONFIRMATION_REQUIRED")
    if rejected_count:
        flags.append("MENU_FABRICATION_BLOCKED")
    return actions, flags


def _normalize_flags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe(str(flag).strip().upper() for flag in value if str(flag).strip())


def _parse_quantity(value: Any) -> int:
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return 1
    return min(max(quantity, 1), 20)


def _parse_price(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe(values) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
