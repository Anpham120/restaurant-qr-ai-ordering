from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any


RESPONSE_MODES = frozenset({"factual", "recommendation", "clarification"})

SEMANTIC_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "response_mode": {
            "type": "string",
            "enum": sorted(RESPONSE_MODES),
        },
        "category": {"type": ["string", "null"]},
        "tags": {"type": "array", "items": {"type": "string"}},
        "referent_ordinal": {"type": ["integer", "null"]},
        "constraint_patch": {"type": "object"},
        "remove_constraints": {
            "type": "array",
            "items": {"type": "string"},
        },
        "needs_clarification": {"type": "boolean"},
        "clarification_slot": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    },
    "required": [
        "intent",
        "response_mode",
        "category",
        "tags",
        "referent_ordinal",
        "constraint_patch",
        "remove_constraints",
        "needs_clarification",
        "clarification_slot",
        "confidence",
    ],
    "additionalProperties": False,
}

_ALLOWED_CONSTRAINTS = frozenset(
    {
        "party_size",
        "budget_vnd",
        "diet",
        "allergens",
        "spice",
        "category",
        "language",
    }
)


@dataclass(frozen=True)
class SemanticPlan:
    intent: str
    response_mode: str
    category: str | None
    tags: tuple[str, ...]
    referent_ordinal: int | None
    constraint_patch: dict[str, Any]
    remove_constraints: tuple[str, ...]
    needs_clarification: bool
    clarification_slot: str | None
    confidence: float


@dataclass(frozen=True)
class AppliedSemanticPlan:
    constraints: dict[str, Any]
    frame: dict[str, Any]


def parse_semantic_plan(raw: str | None) -> SemanticPlan | None:
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

    mode = str(data.get("response_mode") or "").strip()
    if mode not in RESPONSE_MODES:
        return None
    intent = str(data.get("intent") or "general").strip() or "general"
    category_raw = data.get("category")
    category = str(category_raw).strip() if category_raw else None
    tags = tuple(
        dict.fromkeys(
            str(tag).strip()
            for tag in (data.get("tags") or [])
            if str(tag).strip()
        )
    )
    ordinal_raw = data.get("referent_ordinal")
    ordinal: int | None = None
    if ordinal_raw is not None:
        try:
            value = int(ordinal_raw)
            ordinal = value if value > 0 else None
        except (TypeError, ValueError):
            ordinal = None

    patch_raw = data.get("constraint_patch") or {}
    if not isinstance(patch_raw, dict):
        return None
    patch = {
        str(key): value
        for key, value in patch_raw.items()
        if str(key) in _ALLOWED_CONSTRAINTS
    }
    remove = tuple(
        dict.fromkeys(
            str(key)
            for key in (data.get("remove_constraints") or [])
            if str(key) in _ALLOWED_CONSTRAINTS
        )
    )
    try:
        confidence = max(0.0, min(float(data.get("confidence", 0.0)), 1.0))
    except (TypeError, ValueError):
        confidence = 0.0
    clarification_slot_raw = data.get("clarification_slot")
    clarification_slot = (
        str(clarification_slot_raw).strip() if clarification_slot_raw else None
    )
    return SemanticPlan(
        intent=intent,
        response_mode=mode,
        category=category,
        tags=tags,
        referent_ordinal=ordinal,
        constraint_patch=patch,
        remove_constraints=remove,
        needs_clarification=bool(data.get("needs_clarification")),
        clarification_slot=clarification_slot,
        confidence=confidence,
    )


def apply_semantic_plan(
    plan: SemanticPlan,
    *,
    session_state: dict[str, Any],
    constraints: dict[str, Any],
) -> AppliedSemanticPlan:
    merged = dict(constraints)
    for key in plan.remove_constraints:
        merged.pop(key, None)
    merged.update(plan.constraint_patch)
    if plan.category:
        merged["category"] = plan.category

    previous = dict(session_state.get("conversation_frame") or {})
    turn_sequence = int(previous.get("turn_sequence") or 0) + 1
    suggested_ids = [
        str(value).strip()
        for value in (session_state.get("suggested_menu_item_ids") or [])
        if str(value).strip()
    ]
    focus_ids = [
        str(value).strip()
        for value in (previous.get("focus_menu_item_ids") or [])
        if str(value).strip()
    ]
    if plan.referent_ordinal is not None:
        index = plan.referent_ordinal - 1
        focus_ids = [suggested_ids[index]] if index < len(suggested_ids) else []

    unresolved_referent = (
        plan.referent_ordinal is not None and not focus_ids
    )
    needs_clarification = bool(plan.needs_clarification or unresolved_referent)
    clarification_slot = plan.clarification_slot or (
        "menu_item" if unresolved_referent else None
    )
    pending = (
        {
            "slot": clarification_slot or "request",
            "question": "",
            "candidate_menu_item_ids": suggested_ids,
        }
        if needs_clarification
        else None
    )

    provenance = dict(previous.get("constraint_provenance") or {})
    for key in plan.constraint_patch:
        provenance[key] = {
            "turn_sequence": turn_sequence,
            "confidence": plan.confidence,
            "source": "explicit",
        }
    for key in plan.remove_constraints:
        provenance.pop(key, None)

    frame = {
        "active_topic": "menu" if plan.category or plan.tags or focus_ids else plan.intent,
        "active_intent": plan.intent,
        "focus_menu_item_ids": focus_ids,
        "resolved_category": plan.category,
        "resolved_tags": list(plan.tags),
        "turn_sequence": turn_sequence,
        "pending_clarification": pending,
        "constraint_provenance": provenance,
    }
    return AppliedSemanticPlan(constraints=merged, frame=frame)


def build_semantic_plan_messages(
    message: str,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
) -> list[dict[str, str]]:
    frame = session_state.get("conversation_frame") or {}
    state_view = {
        "constraints": session_state.get("constraints") or {},
        "suggested_menu_item_ids": session_state.get("suggested_menu_item_ids") or [],
        "rejected_menu_item_ids": session_state.get("rejected_menu_item_ids") or [],
        "conversation_frame": frame,
    }
    recent = [
        {
            "role": str(turn.get("role") or "user"),
            "content": str(turn.get("content") or "")[:300],
        }
        for turn in history[-6:]
        if str(turn.get("content") or "").strip()
    ]
    system = (
        "Bạn là semantic planner cho trợ lý nhà hàng. Chỉ xuất JSON đúng schema, "
        "không trả lời khách. Xác định intent, factual/recommendation/clarification, "
        "category/tag, số thứ tự món được tham chiếu và thay đổi constraint. "
        "Không tạo menu_item_id. Chỉ xóa dị ứng/ràng buộc an toàn khi khách đính chính "
        "rõ ràng. Nếu đại từ hoặc yêu cầu không đủ rõ, needs_clarification=true."
    )
    user = json.dumps(
        {
            "state": state_view,
            "recent_history": recent,
            "message": message,
        },
        ensure_ascii=False,
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def plan_with_llm(
    client: Any,
    message: str,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
    *,
    timeout_seconds: float,
) -> SemanticPlan | None:
    messages = build_semantic_plan_messages(message, history, session_state)
    try:
        raw = await asyncio.wait_for(
            client.complete_structured(
                messages,
                SEMANTIC_PLAN_SCHEMA,
                "restaurant_semantic_plan",
                max_tokens=320,
                temperature=0.0,
            ),
            timeout=timeout_seconds,
        )
    except (TimeoutError, asyncio.TimeoutError, Exception):
        return None
    return parse_semantic_plan(raw)
