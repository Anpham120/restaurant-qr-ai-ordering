from __future__ import annotations

from typing import Any

from app.rag.content_grounding import format_grounded_recommendation_content
from app.rag.conversation_policy import ConversationPolicy, enforce_suggestion_policy
from app.rag.vietnamese_normalizer import normalize_query_text


_PAIRING_TERMS = ("pair", "hop", "uong gi", "do uong", "kem", "nuoc")


def _is_drink_item(item: dict[str, Any]) -> bool:
    category = normalize_query_text(str(item.get("category_name") or ""))
    tags = normalize_query_text(" ".join(str(tag) for tag in (item.get("tags") or [])))
    blob = f"{category} {tags} {normalize_query_text(str(item.get('name') or ''))}"
    return any(
        token in blob
        for token in ("nuoc", "do uong", "tra", "ca phe", "sinh to", "bia", "drink", "beverage")
    )


def try_pairing_recommendation_fast_path(
    message: str,
    *,
    intent: str,
    policy: ConversationPolicy,
    menu_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Suggest concrete drinks from live menu for food pairing queries."""

    if not policy.wants_recommendations or not menu_items:
        return None
    if intent not in {"beverage_pairing", "combo_pairing"}:
        return None

    normalized = normalize_query_text(message)
    if not any(term in normalized for term in _PAIRING_TERMS):
        return None

    drinks = [item for item in menu_items if bool(item.get("is_available", True)) and _is_drink_item(item)]
    if not drinks:
        return None

    actions = enforce_suggestion_policy([], drinks[:6], policy)
    if not actions:
        return None

    intro = "Dựa trên thực đơn hiện tại, mình gợi ý các đồ uống sau để ăn kèm:"
    content = format_grounded_recommendation_content(actions, intro=intro)
    return {
        "content": content,
        "suggested_cart_actions": actions,
        "provider_available": False,
        "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
        "follow_up": {"can_show_more": len(drinks) > len(actions), "remaining_count": max(len(drinks) - len(actions), 0)},
        "suggest_staff_handoff": False,
    }
