from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


MAX_SUGGESTIONS = 8
DEFAULT_SUGGESTIONS = 4
STRUCTURED_MEMORY_PATTERN = re.compile(
    r"^(SUGGESTED_MENU_ITEM_IDS|REJECTED_MENU_ITEM_IDS)\s*:\s*(.*)$",
    re.IGNORECASE,
)
RECOMMENDATION_TERMS = (
    "goi y",
    "de xuat",
    "tu van",
    "an gi",
    "mon nao",
)
REJECTION_TERMS = (
    "bo qua",
    "dung goi y",
    "khong chon",
    "khong lay",
    "khong muon mon",
    "khong thich",
)


@dataclass(frozen=True)
class ConversationPolicy:
    requested_count: int | None
    wants_recommendations: bool
    previously_suggested_ids: frozenset[str]
    rejected_ids: frozenset[str]

    @property
    def max_suggestions(self) -> int:
        return self.requested_count or DEFAULT_SUGGESTIONS

    @property
    def excluded_menu_item_ids(self) -> frozenset[str]:
        if not self.wants_recommendations:
            return frozenset()
        return self.previously_suggested_ids | self.rejected_ids


def build_conversation_policy(
    message: str,
    history: list[dict[str, Any]],
    session_memory: str,
    menu_items: list[dict[str, Any]],
) -> ConversationPolicy:
    suggested_ids, rejected_ids = _parse_structured_memory(session_memory)
    menu_names = {
        _normalize(str(item.get("name") or "")): _item_id(item)
        for item in menu_items
        if _item_id(item) and _normalize(str(item.get("name") or ""))
    }

    latest_assistant_ids: set[str] = set()
    for turn in history:
        role = str(turn.get("role") or "").casefold()
        content = str(turn.get("content") or "")
        if role == "assistant":
            latest_assistant_ids = _suggested_ids_from_turn(turn, content, menu_names)
            suggested_ids.update(latest_assistant_ids)
        elif role == "user" and _is_rejection(content):
            rejected_ids.update(latest_assistant_ids)

    if _is_rejection(message):
        rejected_ids.update(latest_assistant_ids)

    normalized_message = _normalize(message)
    requested_count = _requested_count(normalized_message)
    wants_recommendations = requested_count is not None or any(
        term in normalized_message for term in RECOMMENDATION_TERMS
    )
    return ConversationPolicy(
        requested_count=requested_count,
        wants_recommendations=wants_recommendations,
        previously_suggested_ids=frozenset(suggested_ids),
        rejected_ids=frozenset(rejected_ids),
    )


def enforce_suggestion_policy(
    actions: list[dict[str, Any]],
    candidate_menu_items: list[dict[str, Any]],
    policy: ConversationPolicy,
) -> list[dict[str, Any]]:
    """Dedupe, exclude and, for explicit counts, deterministically fill cards."""

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in actions:
        item_id = _item_id(action)
        if not item_id or item_id in seen or item_id in policy.excluded_menu_item_ids:
            continue
        seen.add(item_id)
        result.append(action)
        if len(result) == policy.max_suggestions:
            return result

    if not policy.wants_recommendations or policy.requested_count is None:
        return result

    for item in candidate_menu_items:
        item_id = _item_id(item)
        if not item_id or item_id in seen or item_id in policy.excluded_menu_item_ids:
            continue
        result.append(
            {
                "menu_item_id": item_id,
                "name": str(item.get("name") or "").strip(),
                "price_vnd": item.get("price_vnd") or item.get("price"),
                "quantity": 1,
                "reason": "Món phù hợp với yêu cầu hiện tại và đang còn bán.",
                "requires_customer_confirmation": True,
            }
        )
        seen.add(item_id)
        if len(result) == policy.requested_count:
            break
    return result


def _parse_structured_memory(session_memory: str) -> tuple[set[str], set[str]]:
    suggested_ids: set[str] = set()
    rejected_ids: set[str] = set()
    for line in session_memory.splitlines():
        match = STRUCTURED_MEMORY_PATTERN.match(line.strip())
        if not match:
            continue
        target = rejected_ids if match.group(1).upper().startswith("REJECTED") else suggested_ids
        target.update(value.strip() for value in match.group(2).split(",") if value.strip())
    return suggested_ids, rejected_ids


def _suggested_ids_from_turn(
    turn: dict[str, Any],
    content: str,
    menu_names: dict[str, str],
) -> set[str]:
    ids = {
        _item_id(action)
        for action in turn.get("suggested_cart_actions") or []
        if isinstance(action, dict) and _item_id(action)
    }
    normalized_content = _normalize(content)
    ids.update(
        item_id
        for normalized_name, item_id in menu_names.items()
        if normalized_name and f" {normalized_name} " in f" {normalized_content} "
    )
    return ids


def _requested_count(normalized_message: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s+mon\b", normalized_message)
    if not match:
        return None
    return min(max(int(match.group(1)), 1), MAX_SUGGESTIONS)


def _is_rejection(value: str) -> bool:
    normalized = _normalize(value)
    return any(term in normalized for term in REJECTION_TERMS)


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("menu_item_id") or item.get("id") or "").strip()


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))
