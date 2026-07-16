"""Rule-based constraint extraction from user messages and session history.

Fast heuristics run first; CONSTRAINT_SCHEMA documents fields for optional LLM
extraction later.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.rag.intent_classifier import classify_intent


CONSTRAINT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "language": {"type": "string", "enum": ["vi", "en"]},
        "allergens": {"type": "array", "items": {"type": "string"}},
        "diet": {"type": "array", "items": {"type": "string"}},
        "spice": {"type": "string", "enum": ["none", "mild", "medium", "hot", "unknown"]},
        "budget_vnd": {"type": ["integer", "null"]},
        "party_size": {"type": ["integer", "null"]},
        "requested_count": {"type": ["integer", "null"]},
        "rejection_signal": {"type": "boolean"},
        "is_catalog_only": {"type": "boolean"},
        "is_recommendation": {"type": "boolean"},
        "category": {"type": ["string", "null"]},
    },
    "required": [
        "intent",
        "language",
        "allergens",
        "diet",
        "spice",
        "budget_vnd",
        "party_size",
        "requested_count",
        "rejection_signal",
        "is_catalog_only",
        "is_recommendation",
        "category",
    ],
}

ALLERGEN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "seafood": (
        "hai san",
        "tom",
        "cua",
        "muc",
        "oc",
        "ngheu",
        "seafood",
        "shrimp",
        "shellfish",
        "crab",
    ),
    "peanut": ("dau phong", "lac", "peanut", "groundnut"),
    "gluten": ("gluten", "bot mi", "wheat"),
    "egg": ("trung", "egg"),
    "dairy": ("sua", "lactose", "dairy", "milk", "cheese"),
    "soy": ("dau nanh", "soy", "tofu allergy"),
}

DIET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "vegetarian": ("an chay", "mon chay", "thuan chay", "vegetarian"),
    "vegan": ("vegan", "thuan chay", "khong sua", "khong trung"),
    "halal": ("halal", "haram"),
    "keto": ("keto", "low carb", "it carb", "low-carb"),
    "low_calorie": ("it calo", "giam can", "an kieng", "low calorie", "diet"),
}

SPICE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "none": ("khong cay", "mild only", "not spicy", "no spice"),
    "mild": ("cay nhe", "it cay", "mild", "slightly spicy"),
    "medium": ("cay vua", "medium spicy"),
    "hot": ("cay", "rat cay", "spicy", "hot", "cay manh"),
}

CATALOG_TERMS = (
    "xem menu",
    "thuc don",
    "danh sach",
    "co mon gi",
    "co gi trong",
    "list menu",
    "show menu",
    "browse",
    "catalog",
)

RECOMMENDATION_TERMS = (
    "goi y",
    "de xuat",
    "tu van",
    "nen an",
    "recommend",
    "suggest",
    "an gi",
    "mon nao",
    "combo",
)

REJECTION_TERMS = (
    "bo qua",
    "dung goi y",
    "khong chon",
    "khong lay",
    "khong muon",
    "khong thich",
    "skip",
    "no thanks",
    "something else",
)

CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "khai vi": ("khai vi", "appetizer", "starter"),
    "pho bun": ("pho", "bun", "noodle soup"),
    "com viet": ("com", "rice dish", "com viet"),
    "hai san": ("hai san", "seafood"),
    "lau": ("lau", "hot pot"),
    "mon ga": ("mon ga", "chicken"),
    "dac san": ("dac san", "regional"),
    "mon chay": ("mon chay", "vegetarian dish"),
    "ca phe tra": ("ca phe", "tra", "coffee", "tea"),
    "nuoc ep": ("nuoc ep", "sinh to", "smoothie", "juice"),
    "trang mieng": ("trang mieng", "dessert", "che"),
    "trai cay": ("trai cay", "fruit"),
    "bia ruou": ("bia", "ruou", "beer", "wine", "cocktail"),
}

SOFT_CRITERIA_FIELDS = ("budget_vnd", "diet", "allergens", "spice", "party_size")


def extract_constraints(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Extract structured constraints using fast rule-based heuristics."""
    history = history or []
    normalized = _normalize(message)
    combined_text = " ".join(
        [_normalize(str(turn.get("content") or "")) for turn in history[-6:]]
        + [normalized]
    )

    intent_result = classify_intent(message)
    language = _detect_language(message)
    allergens = _match_terms(combined_text, ALLERGEN_KEYWORDS)
    diet = _match_terms(combined_text, DIET_KEYWORDS)
    spice = _detect_spice(combined_text)
    budget_vnd = _extract_budget(normalized)
    party_size = _extract_party_size(normalized)
    requested_count = _extract_requested_count(normalized)
    rejection_signal = _has_any(normalized, REJECTION_TERMS) or any(
        _has_any(_normalize(str(turn.get("content") or "")), REJECTION_TERMS)
        for turn in history
        if str(turn.get("role") or "").casefold() == "user"
    )
    category = _detect_category(normalized)
    is_recommendation = (
        requested_count is not None
        or _has_any(normalized, RECOMMENDATION_TERMS)
        or intent_result.intent in {"recommend", "order"}
        and _has_any(normalized, ("goi y", "de xuat", "tu van", "nen"))
    )
    is_catalog_only = (
        not is_recommendation
        and not budget_vnd
        and not diet
        and not allergens
        and spice == "unknown"
        and party_size is None
        and (
            _has_any(normalized, CATALOG_TERMS)
            or intent_result.intent in {"browse_menu", "ask_price"}
            and category is not None
        )
    )

    return {
        "intent": intent_result.intent,
        "language": language,
        "allergens": allergens,
        "diet": diet,
        "spice": spice,
        "budget_vnd": budget_vnd,
        "party_size": party_size,
        "requested_count": requested_count,
        "rejection_signal": rejection_signal,
        "is_catalog_only": is_catalog_only,
        "is_recommendation": is_recommendation,
        "category": category,
    }


def has_soft_criteria(constraints: dict[str, Any]) -> bool:
    """Return True when constraints include personalization beyond catalog browse."""
    if constraints.get("is_recommendation"):
        return True
    if constraints.get("budget_vnd"):
        return True
    if constraints.get("party_size"):
        return True
    if constraints.get("diet"):
        return True
    if constraints.get("allergens"):
        return True
    spice = constraints.get("spice")
    if spice and spice != "unknown":
        return True
    return False


def _detect_language(message: str) -> str:
    ascii_ratio = sum(1 for char in message if char.isascii()) / max(len(message), 1)
    english_markers = ("what", "how", "menu", "recommend", "allergy", "price", "please", "the")
    normalized = _normalize(message)
    if ascii_ratio > 0.85 and any(marker in normalized for marker in english_markers):
        return "en"
    return "vi"


def _match_terms(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    matched: list[str] = []
    for label, terms in mapping.items():
        if any(term in text for term in terms):
            matched.append(label)
    return matched


def _detect_spice(text: str) -> str:
    for level in ("none", "mild", "medium", "hot"):
        if any(term in text for term in SPICE_KEYWORDS[level]):
            return level
    return "unknown"


def _extract_budget(normalized: str) -> int | None:
    patterns = (
        r"(?:duoi|under|max|toi da|khoang)\s*(\d[\d.,]*)\s*(?:k|nghin|ngan|vnd|dong|d)?",
        r"(\d[\d.,]*)\s*(?:k|nghin|ngan)\b",
        r"budget\s*(\d[\d.,]*)",
        r"(\d{2,3})\s*000\s*(?:vnd|dong|d)?",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        raw = match.group(1).replace(".", "").replace(",", "")
        try:
            value = int(raw)
        except ValueError:
            continue
        if "k" in pattern or "nghin" in pattern or "ngan" in pattern:
            if value < 1000:
                value *= 1000
        elif value < 1000 and re.search(r"\b\d{2,3}\s*000\b", normalized):
            value *= 1000
        return value if value > 0 else None
    return None


def _extract_party_size(normalized: str) -> int | None:
    patterns = (
        r"\b(\d{1,2})\s*(?:nguoi|person|people|pax|khach)\b",
        r"\bcho\s*(\d{1,2})\s*(?:nguoi|person|people|pax)\b",
        r"\bparty\s*of\s*(\d{1,2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return min(max(int(match.group(1)), 1), 20)
    return None


def _extract_requested_count(normalized: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*(?:mon|dishes|items|món)\b", normalized)
    if match:
        return min(max(int(match.group(1)), 1), 8)
    return None


def _detect_category(normalized: str) -> str | None:
    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if alias not in normalized:
                continue
            if _is_negated(normalized, alias):
                continue
            return category
    return None


def _is_negated(text: str, term: str) -> bool:
    index = text.find(term)
    while index != -1:
        window = text[max(0, index - 12) : index]
        if any(neg in window for neg in ("khong ", "bo ", "tranh ", "no ", "without ", "not ")):
            return True
        index = text.find(term, index + 1)
    return False


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))
