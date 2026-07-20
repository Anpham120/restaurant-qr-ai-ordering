from __future__ import annotations

import re
from typing import Literal

from app.rag.vietnamese_normalizer import normalize_query_text


ItemKind = Literal["food", "drink", "dessert"]

DRINK_CATEGORY_IDS = frozenset({"cat_drink", "cat_juice", "cat_alcohol"})
DESSERT_CATEGORY_IDS = frozenset({"cat_dessert", "cat_fruit"})

DRINK_CATEGORY_ALIASES = frozenset({"ca phe tra", "nuoc ep sinh to", "bia ruou"})
DESSERT_CATEGORY_ALIASES = frozenset({"trang mieng", "trai cay tuoi"})

CATEGORY_ALIAS_TO_KIND: dict[str, ItemKind] = {
    "ca phe tra": "drink",
    "nuoc ep": "drink",
    "bia ruou": "drink",
    "trang mieng": "dessert",
    "trai cay": "dessert",
}

DRINK_QUERY_PHRASES = (
    "do uong",
    "thuc uong",
    "uong gi",
    "nuoc ep",
    "sinh to",
    "ca phe",
    " tra ",
    " tra,",
    "bia ",
    " ruou",
    "cocktail",
    "beer",
    "wine",
    "drink",
    "nuoc mia",
    "nuoc dua",
)

DESSERT_QUERY_PHRASES = (
    "trang mieng",
    " mon che",
    "banh flan",
    "flan",
    "dessert",
    "so co la",
    "sweet",
)

FOOD_QUERY_PHRASES = (
    "mon an",
    "do an",
    "mon chinh",
    "mon phu",
    "mon nhe",
    "mon man",
    "khai vi",
    "an nhau",
    "mon nhau",
    "mon goi",
    "mon de an",
    "food",
    "dish",
    "dishes",
    "meal",
    "main course",
)

GENERIC_FOOD_RECOMMENDATION_PHRASES = (
    "goi y",
    "de xuat",
    "tu van",
    "an gi",
    "mon nao",
    "recommend",
    "suggest",
)

# "trả tiền/trả góp..." normalizes to "tra ..." and false-matches the tea phrase " tra ".
PAYMENT_CONTEXT_PHRASES = (
    "tra tien",
    "tra gop",
    "tra lai tien",
    "hoan tra",
    "chi tra",
    "thanh toan",
    "tien mat",
)


def classify_menu_item_kind(item: dict) -> ItemKind:
    category_id = str(item.get("category_id") or "").strip().casefold()
    if category_id in DRINK_CATEGORY_IDS:
        return "drink"
    if category_id in DESSERT_CATEGORY_IDS:
        return "dessert"

    category_name = _normalize(str(item.get("category_name") or ""))
    if any(alias in category_name for alias in DRINK_CATEGORY_ALIASES):
        return "drink"
    if any(alias in category_name for alias in DESSERT_CATEGORY_ALIASES):
        return "dessert"
    return "food"


def detect_requested_item_kind(
    message: str,
    *,
    category: str | None = None,
) -> ItemKind | None:
    """Return the menu kind the user is asking for, or None when unconstrained."""

    if category:
        mapped = CATEGORY_ALIAS_TO_KIND.get(_normalize(category))
        if mapped is not None:
            return mapped

    normalized = _normalize(message)
    drink_scan_text = normalized
    for phrase in PAYMENT_CONTEXT_PHRASES:
        drink_scan_text = drink_scan_text.replace(phrase, " ")
    wants_drink = _contains_phrase(drink_scan_text, DRINK_QUERY_PHRASES)
    wants_dessert = _contains_phrase(normalized, DESSERT_QUERY_PHRASES)

    if wants_dessert and not wants_drink:
        return "dessert"
    if wants_drink:
        return "drink"

    wants_food = _contains_phrase(normalized, FOOD_QUERY_PHRASES) or bool(
        re.search(r"\bmon\b", normalized)
    )
    wants_generic_food = _contains_phrase(normalized, GENERIC_FOOD_RECOMMENDATION_PHRASES)

    if wants_food or re.search(r"\ban (gi|nhau|trua|toi|sang)\b", normalized):
        return "food"
    if wants_generic_food:
        return "food"
    return None


def filter_items_by_kind(
    items: list[dict],
    requested_kind: ItemKind | None,
) -> list[dict]:
    if requested_kind is None:
        return list(items)
    return [item for item in items if classify_menu_item_kind(item) == requested_kind]


def _contains_phrase(normalized: str, phrases: tuple[str, ...]) -> bool:
    padded = f" {normalized} "
    return any(phrase in padded for phrase in phrases)


def _normalize(value: str) -> str:
    return normalize_query_text(value)
