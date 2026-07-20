"""Structural intent signals for recommendation routing.

Design principles:
1. Prefer linguistic *shape* (question vs command, inquiry vs statement) over
   memorized phrases tied to individual eval cases.
2. ``cho N nguoi`` is a party-size preposition unless the utterance is clearly
   asking about table/seat availability.
3. ``goi/dat/them mon X`` is an order only when X names a dish; open questions
   (``goi mon gi``, ``an gi``) are recommendation requests.
4. In an active recommendation thread, elliptical adequacy checks (budget, party
   fit) continue the recommendation flow instead of being treated as FAQ.
"""

from __future__ import annotations

import re

OPEN_MENU_QUESTION_PATTERN = re.compile(
    r"\b("
    r"an\s+gi|"
    r"mon\s+nao|"
    r"goi\s+gi|"
    r"nen\s+(?:goi|an)\s+(?:mon\s+)?(?:gi|nao|gi do|gi vay)|"
    r"goi\s+mon\s+(?:gi|nao|gi do|gi vay|gi hay)"
    r")\b"
)

DISH_ORDER_PATTERN = re.compile(r"\b(?:dat|goi|them)\s+mon\s+(\S+)")

SEATING_INQUIRY_PATTERNS = (
    re.compile(r"\b(mot minh|1 minh)\s+co\s+(ban|duoc|cho)\b"),
    re.compile(r"\bco\s+ban\s+cho\b"),
    re.compile(r"\bban\s+cho\s+\d+\s+nguoi(?:\s+(?:khong|duoc|on))?\b"),
    re.compile(r"\bmot\s+minh\s+ngoi\b"),
    re.compile(r"\b1\s+nguoi\s+thoi\s+co\s+ban\b"),
)

BUDGET_ADEQUACY_PATTERN = re.compile(
    r"\b(?:du|co du|du duoc|con du)\s+(?:tien|ngan sach|budget)\b"
)
PARTY_FIT_ADEQUACY_PATTERN = re.compile(r"\b(?:du|co du)\s+cho\b")
BUDGET_INADEQUACY_PATTERN = re.compile(
    r"\b(?:"
    r"(?:het|khong\s+du|khong\s+con)\s+(?:tien|ngan sach|budget)|"
    r"(?:tien|ngan sach|budget)\s+(?:het|khong\s+du|khong\s+con)|"
    r"het\s+tien\s+khong\s+du"
    r")\b"
)

INGREDIENT_AFTER_CO_PATTERN = re.compile(r"\b(\S+(?:\s+\S+)?)\s+co\s+khong\b")
INGREDIENT_CO_PREFIX_PATTERN = re.compile(r"\bco\s+(\S+(?:\s+\S+)?)\s+khong\b")
PRIOR_DISH_INGREDIENT_PATTERN = re.compile(
    r"\bmon\s+(?:do|ay|vua)\s+co\s+\S+(?:\s+\S+)?\s+khong\b"
)
NON_FOOD_PRESENCE_TERMS = (
    "wifi",
    "ban",
    "phong",
    "giao",
    "ship",
    "dat ban",
    "mo cua",
    "hotline",
    "vip",
)

MORE_DISHES_PATTERN = re.compile(
    r"\b("
    r"mon\s+gi\s+nua|"
    r"gi\s+nua|"
    r"mon\s+khac|"
    r"con\s+mon|"
    r"them\s+mon|"
    r"goi\s+y\s+them|"
    r"de\s+xuat\s+them"
    r")\b"
)

ALLERGY_REFINE_PATTERN = re.compile(
    r"\b("
    r"di\s+ung|"
    r"allerg(?:y|ic)|"
    r"khong\s+an(?:\s+duoc|\s+\S+)?|"
    r"tranh\s+\S+"
    r")\b"
)


def is_category_listing_query(normalized: str) -> bool:
    """User asks which menu items exist in a category — not a personalized combo."""

    listing_terms = (
        "co mon",
        "co nhung mon",
        "co gi an",
        "co gi trong",
        "nhung mon",
        "cac mon",
        "mon nao thuoc",
        "lien quan den",
        "thuoc nhom",
        "o day co",
    )
    return any(term in normalized for term in listing_terms)


def is_open_menu_question(normalized: str) -> bool:
    """True when the user asks what to eat/order (recommendation), not a concrete dish."""

    return OPEN_MENU_QUESTION_PATTERN.search(normalized) is not None


def is_concrete_dish_order(normalized: str) -> bool:
    """True when the user names a specific dish to add (``goi mon bun bo``)."""

    if "goi y" in normalized or is_open_menu_question(normalized):
        return False
    match = DISH_ORDER_PATTERN.search(normalized)
    if not match:
        return False
    token = match.group(1)
    if token in {"gi", "nao"} or token.startswith("gi"):
        return False
    return True


def is_seating_inquiry(normalized: str) -> bool:
    """True when asking about table/seating availability — not party-size preposition."""

    return any(pattern.search(normalized) for pattern in SEATING_INQUIRY_PATTERNS)


def is_suggestion_adequacy_follow_up(normalized: str) -> bool:
    """Elliptical checks on whether a prior suggestion fits budget or party size."""

    if BUDGET_ADEQUACY_PATTERN.search(normalized):
        return True
    if BUDGET_INADEQUACY_PATTERN.search(normalized):
        return True
    if PARTY_FIT_ADEQUACY_PATTERN.search(normalized):
        return True
    return False


def _mentions_non_food_presence(normalized: str) -> bool:
    if any(term in normalized for term in NON_FOOD_PRESENCE_TERMS):
        return True
    if re.search(r"\bco\s+ban\b", normalized):
        return True
    return False


def is_ingredient_presence_follow_up(normalized: str) -> bool:
    """Ingredient checks in recommendation threads — multiple Vietnamese word orders."""

    matched = any(
        pattern.search(normalized)
        for pattern in (
            INGREDIENT_AFTER_CO_PATTERN,
            INGREDIENT_CO_PREFIX_PATTERN,
            PRIOR_DISH_INGREDIENT_PATTERN,
        )
    )
    if not matched:
        return False
    return not _mentions_non_food_presence(normalized)


def is_more_dishes_request(normalized: str) -> bool:
    return MORE_DISHES_PATTERN.search(normalized) is not None


def is_allergy_or_avoidance_refinement(normalized: str) -> bool:
    return ALLERGY_REFINE_PATTERN.search(normalized) is not None
