from __future__ import annotations

from typing import Any

from app.rag.constraint_extractor import has_hard_dietary_constraints
from app.rag.content_grounding import format_grounded_recommendation_content
from app.rag.conversation_policy import ConversationPolicy, enforce_suggestion_policy
from app.rag.party_menu_ranking import party_recommendation_intro


def try_budget_recommendation_fast_path(
    constraints: dict[str, Any],
    policy: ConversationPolicy,
    candidate_menu_items: list[dict[str, Any]],
    budget_picks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Deterministic budget recommendation without waiting for the LLM."""

    budget_vnd = constraints.get("budget_vnd")
    if not budget_vnd or not policy.wants_recommendations:
        return None
    if has_hard_dietary_constraints(constraints):
        return None
    if not budget_picks and not candidate_menu_items:
        return None

    actions = enforce_suggestion_policy(
        budget_picks,
        candidate_menu_items,
        policy,
    )
    if not actions:
        return None

    party_size = policy.party_size or constraints.get("party_size")
    intro_parts: list[str] = []
    party_intro = party_recommendation_intro(party_size)
    if party_intro:
        intro_parts.append(party_intro)
    if party_size:
        intro_parts.append(
            f"Dưới ngân sách khoảng {int(budget_vnd):,} VND cho {party_size} người, mình gợi ý:"
        )
    else:
        intro_parts.append(f"Dưới ngân sách khoảng {int(budget_vnd):,} VND, mình gợi ý:")

    content = format_grounded_recommendation_content(
        actions,
        intro=" ".join(intro_parts),
    )
    return {
        "content": content,
        "suggested_cart_actions": actions,
        "provider_available": False,
        "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": False,
    }
