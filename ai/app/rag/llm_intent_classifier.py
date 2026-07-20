"""LLM-based semantic intent classification for ambiguous user messages.

Runs only when rule-based signals are low-confidence; merges into constraints/policy
without overriding explicit regex hits.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.rag.constraint_extractor import CATALOG_TERMS, RECOMMENDATION_TERMS
from app.rag.conversation_policy import ConversationPolicy
from app.rag.intent_classifier import INTENT_RULES, IntentResult, classify_intent_with_history
from app.rag.vietnamese_normalizer import normalize_query_text

AMBIGUITY_CONFIDENCE_THRESHOLD = 0.35

INTENT_NAMES: tuple[str, ...] = tuple(
    dict.fromkeys([name for name, *_ in INTENT_RULES] + ["general"])
)

INFO_MARKER_TERMS = (
    "dia chi",
    "o dau",
    "hotline",
    "lien he",
    "wifi",
    "mo cua",
    "gio",
    "gui xe",
    "vip",
    "thanh toan",
    "hoa don",
    "khuyen mai",
    "faq",
    "bao nhieu",
    "tinh tien",
    "tra tien",
)

EXPLICIT_PARTY_PATTERN = re.compile(
    r"\b(\d{1,2})\s*(?:nguoi|person|people|pax|khach)\b"
)

INTENT_CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "party_size": {"type": ["integer", "null"]},
        "wants_recommendations": {"type": "boolean"},
        "is_solo_dining": {"type": "boolean"},
        "kb_topic": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    "required": [
        "intent",
        "party_size",
        "wants_recommendations",
        "is_solo_dining",
        "kb_topic",
        "confidence",
    ],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class LlmIntentSignals:
    intent: str
    party_size: int | None
    wants_recommendations: bool
    is_solo_dining: bool
    kb_topic: str | None
    confidence: float


def is_ambiguous(
    intent_result: IntentResult,
    constraints: dict[str, Any],
    policy: ConversationPolicy,
    *,
    message: str = "",
) -> bool:
    """Return True when keyword routing is uncertain and LLM classification may help."""

    normalized = normalize_query_text(message)
    if intent_result.confidence >= AMBIGUITY_CONFIDENCE_THRESHOLD and intent_result.intent not in {
        "general",
    }:
        return False
    if policy.wants_recommendations and constraints.get("party_size"):
        return False
    if constraints.get("budget_vnd"):
        return False
    if constraints.get("is_catalog_only"):
        return False
    if any(term in normalized for term in INFO_MARKER_TERMS):
        return False
    if EXPLICIT_PARTY_PATTERN.search(normalized):
        return False
    if any(term in normalized for term in CATALOG_TERMS):
        return False
    if any(term in normalized for term in RECOMMENDATION_TERMS):
        return False
    if intent_result.intent == "general" and intent_result.confidence < AMBIGUITY_CONFIDENCE_THRESHOLD:
        return True
    if not policy.wants_recommendations and constraints.get("party_size") is None:
        return True
    return intent_result.confidence < AMBIGUITY_CONFIDENCE_THRESHOLD


def build_classification_messages(
    message: str,
    history: list[dict[str, Any]] | None,
    rolling_summary: str,
) -> list[dict[str, str]]:
    history = history or []
    recent_lines: list[str] = []
    for turn in history[-6:]:
        role = str(turn.get("role") or "user")
        content = str(turn.get("content") or "").strip()
        if content:
            recent_lines.append(f"{role}: {content}")
    context_block = "\n".join(recent_lines) if recent_lines else "(không có)"
    summary_block = rolling_summary.strip() or "(không có)"
    intent_list = ", ".join(INTENT_NAMES)
    system = (
        "Bạn phân loại ý định khách nhà hàng (tiếng Việt/English). "
        "Trả về JSON đúng schema. "
        f"intent phải là một trong: {intent_list}. "
        "wants_recommendations=true khi khách muốn gợi ý món/ăn gì, kể cả cách nói gián tiếp. "
        "is_solo_dining=true khi khách ăn một mình ('solo', 'một mình', 'alone', 'just me'). "
        "party_size=1 khi solo; số người rõ (kể cả chữ: ba nguoi=3, bon nguoi=4). "
        "wants_recommendations=false khi từ chối gợi ý ('bỏ qua gợi ý', 'no thanks') hoặc hỏi FAQ thuần. "
        "kb_topic chỉ khi hỏi thông tin nhà hàng (wifi, địa chỉ, thanh toán...)."
    )
    user = (
        f"Tóm tắt phiên:\n{summary_block}\n\n"
        f"Lịch sử gần đây:\n{context_block}\n\n"
        f"Tin nhắn hiện tại: {message.strip()}\n\n"
        "Ví dụ: 'di an solo toi nay' -> recommend, party_size=1, wants=true, solo=true.\n"
        "Ví dụ: 'bon nguoi an gi' -> recommend, party_size=4, wants=true, solo=false.\n"
        "Ví dụ: 'bo qua goi y do' -> general, wants=false.\n"
        "Ví dụ: 'wifi mat khau gi' -> restaurant_info, wants=false."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_classification_response(raw: str | None) -> LlmIntentSignals | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        text = match.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    intent = str(data.get("intent") or "general").strip()
    if intent not in INTENT_NAMES:
        intent = "general"

    party_raw = data.get("party_size")
    party_size: int | None = None
    if party_raw is not None:
        try:
            party_size = min(max(int(party_raw), 1), 20)
        except (TypeError, ValueError):
            party_size = None

    wants_recommendations = bool(data.get("wants_recommendations"))
    is_solo_dining = bool(data.get("is_solo_dining"))
    if is_solo_dining and party_size is None:
        party_size = 1
    if party_size == 1:
        is_solo_dining = True

    kb_topic = data.get("kb_topic")
    kb_topic_str = str(kb_topic).strip() if kb_topic else None

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(confidence, 1.0))

    return LlmIntentSignals(
        intent=intent,
        party_size=party_size,
        wants_recommendations=wants_recommendations,
        is_solo_dining=is_solo_dining,
        kb_topic=kb_topic_str,
        confidence=confidence,
    )


async def classify_with_llm(
    client: Any,
    message: str,
    history: list[dict[str, Any]] | None,
    rolling_summary: str,
    *,
    timeout_seconds: float = 2.5,
) -> LlmIntentSignals | None:
    import asyncio

    messages = build_classification_messages(message, history, rolling_summary)
    try:
        raw = await asyncio.wait_for(
            client.complete_structured(
                messages,
                INTENT_CLASSIFICATION_SCHEMA,
                "restaurant_intent_classification",
                max_tokens=180,
                temperature=0.0,
            ),
            timeout=timeout_seconds,
        )
    except (TimeoutError, asyncio.TimeoutError, Exception):
        return None
    return parse_classification_response(raw)


def merge_llm_signals_into_constraints(
    constraints: dict[str, Any],
    signals: LlmIntentSignals,
) -> dict[str, Any]:
    merged = dict(constraints)
    if merged.get("intent") in {None, "", "general"} and signals.intent != "general":
        merged["intent"] = signals.intent
    if merged.get("party_size") is None and signals.party_size is not None:
        merged["party_size"] = signals.party_size
    if signals.wants_recommendations:
        merged["is_recommendation"] = True
    merged["is_solo_dining"] = bool(signals.is_solo_dining or merged.get("is_solo_dining"))
    if signals.kb_topic:
        merged["kb_topic"] = signals.kb_topic
    merged["llm_intent_confidence"] = signals.confidence
    return merged


def merge_llm_signals_into_policy(
    policy: ConversationPolicy,
    signals: LlmIntentSignals,
) -> ConversationPolicy:
    wants = policy.wants_recommendations or signals.wants_recommendations
    party_size = policy.party_size
    if party_size is None and signals.party_size is not None:
        party_size = signals.party_size
    if signals.is_solo_dining and party_size is None:
        party_size = 1
    return ConversationPolicy(
        requested_count=policy.requested_count,
        wants_recommendations=wants,
        previously_suggested_ids=policy.previously_suggested_ids,
        rejected_ids=policy.rejected_ids,
        requested_item_kind=policy.requested_item_kind,
        variation_seed=policy.variation_seed,
        surface_prior_suggestion_cards=policy.surface_prior_suggestion_cards,
        party_size=party_size,
    )


def classify_intent_for_message(
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> IntentResult:
    return classify_intent_with_history(message, history)
