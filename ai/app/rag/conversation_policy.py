from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from app.rag.menu_exclusions import build_suggestion_reason
from app.rag.party_menu_ranking import (
    is_shared_group_dish,
    rank_candidates_for_party,
)
from app.rag.vietnamese_normalizer import normalize_query_text
from app.rag.menu_item_kind import (
    ItemKind,
    classify_menu_item_kind,
    detect_requested_item_kind,
    filter_items_by_kind,
)
from app.rag.intent_routing_signals import (
    is_allergy_or_avoidance_refinement,
    is_category_listing_query,
    is_concrete_dish_order,
    is_more_dishes_request as is_more_dishes_structural,
    is_open_menu_question,
    is_suggestion_adequacy_follow_up,
    is_ingredient_presence_follow_up,
)
from app.rag.party_size_parser import (
    extract_party_size_from_text,
    is_capacity_info_question,
    is_solo_dining_text,
    is_solo_seating_question,
)


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
    "goi gi",
    "goi mon",
    "suggest",
    "recommend",
    "suggestions",
    "what can i eat",
    "what should i eat",
    "more dishes",
    "more options",
    "options please",
    "food suggestions",
    "nao ngon",
    "best seller",
    "noi bat",
    "cap doi",
)
GROUP_RECOMMENDATION_TERMS = (
    "nhom",
    "gia dinh",
    "dai gia dinh",
    "an chung",
    "nhieu nguoi",
    "dong nguoi",
    "ca nha",
    "ban be",
    "an voi",
    "mon khac",
    "mon phu hop",
)
MORE_DISHES_TERMS = (
    "mon khac",
    "con mon",
    "them mon",
    "goi y them",
    "de xuat them",
    "goi y mon khac",
    "nao khac",
    "khac di",
    "mon nua",
)
CONTEXT_ONLY_FOLLOW_UP_TERMS = (
    "du khong",
    "du cho",
    "co du",
    "mon do",
    "mon ay",
    "mon vua",
    "da goi y",
    "vua goi y",
    "nhac lai",
    "la gi",
    "la sao",
    "co ngon",
    "ngon khong",
    "cam on",
    "hieu roi",
    "duoc chua",
    "on chua",
    "bao nhieu",
    "gia bao",
    "thanh toan",
    "thi sao",
    "the con",
    "sao nua",
)
FOLLOW_UP_TERMS = MORE_DISHES_TERMS
ELLIPTICAL_INFO_FOLLOW_UP_TERMS = (
    "thi sao",
    "the con",
    "con gi ve",
    "ve thanh toan",
    "thanh toan thi sao",
)
REJECTION_TERMS = (
    "bo qua",
    "dung goi y",
    "khong chon",
    "khong lay",
    "khong muon mon",
    "khong thich",
    "skip",
    "no thanks",
    "something else",
)
NON_RECOMMENDATION_INFO_TERMS = (
    "tra bang the",
    "thanh toan",
    "wifi",
    "mat khau",
    "dia chi",
    "hotline",
    "lien he",
    "gui xe",
    "mo cua",
    "dat ban truoc",
    "suc chua",
    "cho ngoi",
    "phong vip",
    "giao hang",
    "ship do",
    "faq",
)
CATALOG_BROWSE_TERMS = (
    "xem menu",
    "thuc don",
    "trong menu",
    "list menu",
    "show menu",
    "browse",
    "danh sach mon",
    "menu please",
)
DIETARY_REFINE_TERMS = (
    "cay vua",
    "khong cay",
    "it cay",
    "it hon cay",
    "hon cay",
    "it calo",
    "it dam",
    "keto",
    "an chay",
    "healthy",
    "low carb",
    "mon chay",
    "diet menu",
)
ALLERGY_RECOMMEND_TERMS = (
    "di ung",
    "allergy",
    "allergic",
    "khong an duoc",
    "khong an ",
    "tranh ",
)
INFORMATION_TERMS = (
    "gia bao nhieu",
    "bao nhieu tien",
    "het hang",
    "con khong",
    "co khong",
    "co ban khong",
)
MENU_BROWSE_TERMS = (
    "co mon gi",
    "mon gi",
    "co gi an",
    "an nhe",
    "mon nhe",
    "nhung mon",
    "loai mon",
    "co nhung mon",
    "ban co mon",
    "o day co mon",
)


@dataclass(frozen=True)
class ConversationPolicy:
    requested_count: int | None
    wants_recommendations: bool
    previously_suggested_ids: frozenset[str]
    rejected_ids: frozenset[str]
    requested_item_kind: ItemKind | None = None
    variation_seed: str = ""
    surface_prior_suggestion_cards: bool = False
    party_size: int | None = None

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
    *,
    category: str | None = None,
    variation_seed: str = "",
) -> ConversationPolicy:
    """Resolve recommendation routing with explicit precedence:

    rejection/order/info/seating > catalog browse > recommendation signals >
    thread refinement/adequacy follow-ups.
    """
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
    requested_item_kind = detect_requested_item_kind(message, category=category)
    is_menu_browse = any(_contains_term(normalized_message, term) for term in MENU_BROWSE_TERMS)
    recommendation_thread = _was_recommendation_thread(history, session_memory)
    catalog_browse = any(
        _contains_term(normalized_message, term) for term in CATALOG_BROWSE_TERMS
    ) and not any(_contains_term(normalized_message, term) for term in RECOMMENDATION_TERMS)

    if _is_rejection(message):
        wants_recommendations = False
    elif _is_explicit_order(normalized_message):
        wants_recommendations = False
    elif _is_negated_recommendation(normalized_message):
        wants_recommendations = False
    elif is_solo_seating_question(normalized_message):
        wants_recommendations = False
    elif catalog_browse:
        wants_recommendations = False
    elif (
        category
        and is_category_listing_query(normalized_message)
        and not _is_explicit_order(normalized_message)
    ):
        wants_recommendations = False
    elif _is_non_recommendation_info(normalized_message):
        wants_recommendations = False
    else:
        wants_recommendations = (
            requested_count is not None
            or (
                _has_party_size(normalized_message)
                and not _is_context_only_follow_up(normalized_message, recommendation_thread)
            )
            or is_open_menu_question(normalized_message)
            or any(_contains_term(normalized_message, term) for term in RECOMMENDATION_TERMS)
            or any(_contains_term(normalized_message, term) for term in GROUP_RECOMMENDATION_TERMS)
            or is_solo_dining_text(normalized_message)
            or any(_contains_term(normalized_message, term) for term in DIETARY_REFINE_TERMS)
            or _is_allergy_or_diet_recommendation(normalized_message)
            or (
                not _is_information_question(normalized_message)
                and not _is_context_only_follow_up(normalized_message, recommendation_thread)
                and (
                    requested_item_kind in ("drink", "dessert")
                    or (requested_item_kind == "food" and is_menu_browse)
                )
            )
        )
    if recommendation_thread and _is_recommendation_refinement(normalized_message):
        wants_recommendations = True
    if (
        recommendation_thread
        and is_suggestion_adequacy_follow_up(normalized_message)
        and not _is_prior_dish_context_question(normalized_message)
    ):
        wants_recommendations = True
    if recommendation_thread and is_ingredient_presence_follow_up(normalized_message):
        wants_recommendations = True
    if is_solo_seating_question(normalized_message):
        wants_recommendations = False
        party_size = extract_party_size_from_text(normalized_message)
    elif is_solo_dining_text(normalized_message) and not _is_rejection(message):
        wants_recommendations = True
    if (
        recommendation_thread
        and _is_more_dishes_request(normalized_message)
        and not _is_context_only_follow_up(normalized_message, recommendation_thread)
    ):
        wants_recommendations = True
    if (
        recommendation_thread
        and _is_prior_dish_context_question(normalized_message)
        and not _is_more_dishes_request(normalized_message)
    ):
        wants_recommendations = False
    surface_prior_suggestion_cards = (
        recommendation_thread
        and not wants_recommendations
        and _is_prior_dish_context_question(normalized_message)
        and bool(suggested_ids)
    )
    party_size = resolve_party_size(message, history)
    if is_solo_seating_question(normalized_message):
        party_size = extract_party_size_from_text(normalized_message)
    elif (
        is_solo_dining_text(normalized_message)
        and party_size is None
        and not is_solo_seating_question(normalized_message)
    ):
        party_size = 1
    return ConversationPolicy(
        requested_count=requested_count,
        wants_recommendations=wants_recommendations,
        previously_suggested_ids=frozenset(suggested_ids),
        rejected_ids=frozenset(rejected_ids),
        requested_item_kind=requested_item_kind,
        variation_seed=variation_seed,
        surface_prior_suggestion_cards=surface_prior_suggestion_cards,
        party_size=party_size,
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
        if policy.requested_item_kind is not None:
            matching = next(
                (item for item in candidate_menu_items if _item_id(item) == item_id),
                None,
            )
            if matching is not None and classify_menu_item_kind(matching) != policy.requested_item_kind:
                continue
        seen.add(item_id)
        result.append(action)
        if len(result) == policy.max_suggestions:
            return _finalize_party_suggestions(result, candidate_menu_items, policy)

    if not policy.wants_recommendations:
        return result

    fill_target = policy.requested_count if policy.requested_count is not None else policy.max_suggestions
    if len(result) >= fill_target:
        return _finalize_party_suggestions(result[:fill_target], candidate_menu_items, policy)

    kind_filtered_candidates = rank_candidates_for_party(
        filter_items_by_kind(
            candidate_menu_items,
            policy.requested_item_kind,
        ),
        policy.party_size,
    )
    for item in kind_filtered_candidates:
        item_id = _item_id(item)
        if not item_id or item_id in seen or item_id in policy.excluded_menu_item_ids:
            continue
        result.append(_build_suggestion_action(item, policy))
        seen.add(item_id)
        if len(result) == fill_target:
            break

    return _finalize_party_suggestions(result, candidate_menu_items, policy)


def build_prior_suggestion_actions(
    menu_items: list[dict[str, Any]],
    policy: ConversationPolicy,
) -> list[dict[str, Any]]:
    """Re-surface cart cards for dishes already suggested in this thread."""

    if not policy.previously_suggested_ids:
        return []

    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in menu_items:
        item_id = _item_id(item)
        if (
            not item_id
            or item_id in seen
            or item_id not in policy.previously_suggested_ids
            or item_id in policy.rejected_ids
            or not bool(item.get("is_available", True))
        ):
            continue
        seen.add(item_id)
        actions.append(
            {
                "menu_item_id": item_id,
                "name": str(item.get("name") or "").strip(),
                "price_vnd": item.get("price_vnd") or item.get("price"),
                "quantity": 1,
                "reason": build_suggestion_reason(item, seed=policy.variation_seed or item_id),
                "requires_customer_confirmation": True,
            }
        )
    return actions


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
    match = re.search(
        r"\b(\d{1,2})\s+(?:mon\b|(?:more\s+)?(?:dish(?:es)?|item|option)s?\b)",
        normalized_message,
    )
    if not match:
        return None
    return min(max(int(match.group(1)), 1), MAX_SUGGESTIONS)


def _contains_term(normalized_message: str, term: str) -> bool:
    if " " in term:
        return term in normalized_message
    return re.search(rf"\b{re.escape(term)}\b", normalized_message) is not None


def _is_explicit_order(normalized_message: str) -> bool:
    return is_concrete_dish_order(normalized_message)


def _is_negated_recommendation(normalized_message: str) -> bool:
    if re.search(r"\bkhong phai goi y\b", normalized_message):
        return True
    if "chi hoi gia" in normalized_message:
        return True
    return False


def _is_allergy_or_diet_recommendation(normalized_message: str) -> bool:
    if not any(_contains_term(normalized_message, term) for term in ALLERGY_RECOMMEND_TERMS):
        return False
    if _is_non_recommendation_info(normalized_message):
        return False
    return True


def _is_non_recommendation_info(normalized_message: str) -> bool:
    if is_capacity_info_question(normalized_message):
        return True
    if not any(_contains_term(normalized_message, term) for term in NON_RECOMMENDATION_INFO_TERMS):
        return False
    return not any(_contains_term(normalized_message, term) for term in RECOMMENDATION_TERMS)


def _is_recommendation_refinement(normalized_message: str) -> bool:
    if any(_contains_term(normalized_message, term) for term in DIETARY_REFINE_TERMS):
        return True
    if is_more_dishes_structural(normalized_message):
        return True
    if is_allergy_or_avoidance_refinement(normalized_message):
        return True
    return False


def _has_party_size(normalized_message: str) -> bool:
    return _party_size_from_text(normalized_message) is not None


def _party_size_from_text(normalized_message: str) -> int | None:
    return extract_party_size_from_text(normalized_message)


def resolve_party_size(message: str, history: list[dict[str, Any]]) -> int | None:
    return _party_size_from_text(_normalize(message)) or _party_size_from_history(history)


def _party_size_from_history(history: list[dict[str, Any]]) -> int | None:
    for turn in reversed(history):
        if str(turn.get("role") or "").casefold() != "user":
            continue
        party_size = _party_size_from_text(_normalize(str(turn.get("content") or "")))
        if party_size is not None:
            return party_size
    return None


def _was_recommendation_thread(
    history: list[dict[str, Any]],
    session_memory: str,
) -> bool:
    suggested_ids, _ = _parse_structured_memory(session_memory)
    if suggested_ids:
        return True

    recommendation_signals = (*RECOMMENDATION_TERMS, *GROUP_RECOMMENDATION_TERMS)
    for turn in history:
        role = str(turn.get("role") or "").casefold()
        if role == "assistant" and turn.get("suggested_cart_actions"):
            return True
        if role != "user":
            continue
        normalized = _normalize(str(turn.get("content") or ""))
        if _has_party_size(normalized):
            return True
        if any(_contains_term(normalized, term) for term in recommendation_signals):
            return True
    return False


def _is_follow_up_request(normalized_message: str) -> bool:
    return _is_more_dishes_request(normalized_message)


def _is_more_dishes_request(normalized_message: str) -> bool:
    return is_more_dishes_structural(normalized_message) or any(
        term in normalized_message for term in MORE_DISHES_TERMS
    )


def _is_context_only_follow_up(
    normalized_message: str,
    recommendation_thread: bool = False,
) -> bool:
    if recommendation_thread and _is_recommendation_refinement(normalized_message):
        return False
    if _is_information_question(normalized_message):
        return True
    if _is_elliptical_info_follow_up(normalized_message):
        return True
    if any(term in normalized_message for term in CONTEXT_ONLY_FOLLOW_UP_TERMS):
        if recommendation_thread and _has_party_size(normalized_message):
            if any(term in normalized_message for term in ("du cho", "du khong", "co du", "du tien")):
                return False
        return True
    if "con gi" in normalized_message and "mon" not in normalized_message:
        return True
    return False


PRIOR_DISH_CONTEXT_TERMS = (
    "mon do",
    "mon ay",
    "mon vua",
    "da goi y",
    "vua goi y",
    "nhac lai",
    "may mon",
    "cac mon",
    "nhung mon",
    "du cho",
    "du khong",
    "du chua",
    "on chua",
    "co ngon",
    "ngon khong",
)


def _is_prior_dish_context_question(normalized_message: str) -> bool:
    if not any(term in normalized_message for term in PRIOR_DISH_CONTEXT_TERMS):
        return False
    payment_terms = ("thanh toan", "tinh tien", "hoa don", "vietqr", "tra tien")
    if any(term in normalized_message for term in payment_terms) and "mon" not in normalized_message:
        return False
    return True


def _is_elliptical_info_follow_up(normalized_message: str) -> bool:
    return any(term in normalized_message for term in ELLIPTICAL_INFO_FOLLOW_UP_TERMS)


def infer_suggested_actions_from_content(
    content: str,
    menu_items: list[dict[str, Any]],
    policy: ConversationPolicy,
) -> list[dict[str, Any]]:
    """Build cart cards when LLM prose names menu items but JSON actions are empty."""

    if not policy.wants_recommendations or not content.strip():
        return []

    normalized_content = _normalize(content)
    matches: list[tuple[int, str, dict[str, Any]]] = []
    for item in menu_items:
        item_id = _item_id(item)
        if not item_id or item_id in policy.excluded_menu_item_ids:
            continue
        if not bool(item.get("is_available", True)):
            continue
        name = str(item.get("name") or "").strip()
        normalized_name = _normalize(name)
        if len(normalized_name) < 4:
            continue
        index = normalized_content.find(normalized_name)
        if index < 0:
            continue
        matches.append((index, normalized_name, item))

    if not matches:
        return []

    matches.sort(key=lambda row: (-len(row[1]), row[0]))
    actions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for _, _, item in matches:
        item_id = _item_id(item)
        if not item_id or item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        actions.append(
            {
                "menu_item_id": item_id,
                "name": str(item.get("name") or "").strip(),
                "price_vnd": item.get("price_vnd") or item.get("price"),
                "quantity": 1,
                "reason": build_suggestion_reason(item, seed=policy.variation_seed or item_id),
                "requires_customer_confirmation": True,
            }
        )
        if len(actions) == policy.max_suggestions:
            break
    return actions


def _is_rejection(value: str) -> bool:
    normalized = _normalize(value)
    return any(term in normalized for term in REJECTION_TERMS)


def _is_information_question(normalized_message: str) -> bool:
    return any(term in normalized_message for term in INFORMATION_TERMS)


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("menu_item_id") or item.get("id") or "").strip()


def _normalize(value: str) -> str:
    return normalize_query_text(value)


def _action_is_shared(
    action: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> bool:
    item_id = _item_id(action)
    if not item_id:
        return False
    for item in candidates:
        if _item_id(item) == item_id:
            return is_shared_group_dish(item)
    return False


def _build_suggestion_action(
    item: dict[str, Any],
    policy: ConversationPolicy,
) -> dict[str, Any]:
    item_id = _item_id(item)
    return {
        "menu_item_id": item_id,
        "name": str(item.get("name") or "").strip(),
        "price_vnd": item.get("price_vnd") or item.get("price"),
        "quantity": 1,
        "reason": build_suggestion_reason(item, seed=policy.variation_seed or item_id),
        "requires_customer_confirmation": True,
    }


def _rebalance_party_suggestions(
    actions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    policy: ConversationPolicy,
    fill_target: int,
) -> list[dict[str, Any]]:
    party_size = policy.party_size
    if not party_size or party_size < 4:
        return actions[:fill_target]

    min_shared = fill_target if party_size >= 6 else (2 if party_size >= 4 else 1)
    min_shared = min(min_shared, fill_target)
    shared_actions = [action for action in actions if _action_is_shared(action, candidates)]
    other_actions = [action for action in actions if not _action_is_shared(action, candidates)]
    seen = {_item_id(action) for action in actions if _item_id(action)}

    ranked_shared = [
        item
        for item in rank_candidates_for_party(candidates, party_size)
        if is_shared_group_dish(item)
        and _item_id(item) not in policy.excluded_menu_item_ids
        and bool(item.get("is_available", True))
    ]
    needed = max(0, min_shared - len(shared_actions))
    for item in ranked_shared:
        if needed <= 0:
            break
        item_id = _item_id(item)
        if not item_id or item_id in seen:
            continue
        shared_actions.append(_build_suggestion_action(item, policy))
        seen.add(item_id)
        needed -= 1

    combined = shared_actions + other_actions
    return combined[:fill_target]


def _finalize_party_suggestions(
    actions: list[dict[str, Any]],
    candidate_menu_items: list[dict[str, Any]],
    policy: ConversationPolicy,
) -> list[dict[str, Any]]:
    if not policy.wants_recommendations or not policy.party_size or policy.party_size < 4:
        return actions

    fill_target = policy.requested_count if policy.requested_count is not None else policy.max_suggestions
    kind_filtered_candidates = rank_candidates_for_party(
        filter_items_by_kind(
            candidate_menu_items,
            policy.requested_item_kind,
        ),
        policy.party_size,
    )
    result = _rebalance_party_suggestions(
        actions,
        kind_filtered_candidates,
        policy,
        fill_target,
    )
    return result
