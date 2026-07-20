from __future__ import annotations

from typing import Any

from app.rag.constraint_extractor import has_hard_dietary_constraints
from app.rag.content_grounding import format_grounded_recommendation_content
from app.rag.conversation_policy import ConversationPolicy, enforce_suggestion_policy
from app.rag.party_menu_ranking import party_recommendation_intro


def try_party_recommendation_fast_path(
    constraints: dict[str, Any],
    policy: ConversationPolicy,
    candidate_menu_items: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Deterministic group/solo recommendation without waiting for the LLM."""

    party_size = policy.party_size or constraints.get("party_size")
    if not party_size or not policy.wants_recommendations:
        return None
    if constraints.get("is_catalog_only"):
        return None
    if has_hard_dietary_constraints(constraints):
        return None
    if not candidate_menu_items:
        return None

    actions = enforce_suggestion_policy([], candidate_menu_items, policy)
    if not actions:
        return None

    intro = party_recommendation_intro(party_size) or (
        f"Với nhóm {party_size} người, mình gợi ý:"
        if party_size > 1
        else "Bạn đi một mình thì mình gợi ý vài món phần vừa ăn:"
    )
    content = format_grounded_recommendation_content(actions, intro=intro)
    return {
        "content": content,
        "suggested_cart_actions": actions,
        "provider_available": False,
        "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": False,
    }
