"""Rule-based constraint extraction from user messages and session history.

Fast heuristics run first; CONSTRAINT_SCHEMA documents fields for optional LLM
extraction later.
"""
from __future__ import annotations

import re
from typing import Any

from app.rag.conversation_policy import (
    _is_context_only_follow_up,
    _is_more_dishes_request,
    _was_recommendation_thread,
)
from app.rag.guardrails import detect_guardrail_flags
from app.rag.intent_classifier import classify_intent_with_history
from app.rag.party_size_parser import (
    extract_party_size_from_text,
    is_solo_dining_text,
    is_solo_seating_question,
)
from app.rag.vietnamese_normalizer import normalize_query_text


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

# "cua" and "muc" are diacritic-stripped ASCII forms shared by real seafood
# words ("cua" = crab, "mực" = squid) AND extremely common unrelated words
# ("cửa" = door/store as in "mở cửa"/"đóng cửa", "của" = possessive "of",
# "mức" = level/degree as in "mức giá"). Word-boundary matching alone cannot
# tell these apart once diacritics are stripped, so any question mentioning
# opening hours or using "của" would otherwise be wrongly tagged as a seafood
# allergy. These are matched against diacritic-preserving text instead (see
# _term_matches / _match_terms), using the pattern below rather than the bare
# term: "cua" (crab) has no correct diacritics of its own, so requiring the
# literal unaccented spelling is enough to exclude "cửa"/"của". "mực" (squid)
# DOES have its own correct diacritics, so its pattern also accepts that exact
# accented spelling — otherwise a customer who correctly typed "dị ứng mực"
# would be missed — while still excluding "mức" (a different accent).
_DIACRITIC_SENSITIVE_PATTERNS: dict[str, str] = {
    "cua": r"\bcua\b",
    "muc": r"\b(?:muc|mực)\b",
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
    # "chay thuan" is the same request as "thuan chay" with the words swapped —
    # both orders occur naturally in Vietnamese, so list both.
    "vegetarian": ("an chay", "mon chay", "thuan chay", "chay thuan", "vegetarian"),
    "vegan": ("vegan", "thuan chay", "chay thuan", "khong sua", "khong trung"),
    "halal": ("halal", "haram"),
    "keto": ("keto", "low carb", "it carb", "low-carb"),
    # Bare "diet" is NOT a low-calorie signal: Vietnamese customers write it for
    # any dietary requirement at all ("diet chay thuan" = vegan diet), so it used
    # to tag vegan/halal/keto questions as calorie-restricted. Only the explicit
    # weight-loss phrasings below count.
    "low_calorie": ("it calo", "giam can", "an kieng", "low calorie", "low-calorie", "diet food"),
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
    "cac mon",
    "nhung mon",
    "lien quan",
    "thuoc nhom",
    "mon nao thuoc",
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
    "other dishes",
    "different items",
    "more options",
    "more dishes",
    "not mentioned",
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
    # "chay thuan"/"thuan chay" (vegan) name the same menu category as "mon chay".
    "mon chay": ("mon chay", "chay thuan", "thuan chay", "vegetarian dish", "vegan dish"),
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
    # Only user turns: assistant replies mention dish names/pronouns ("cua" in
    # "của", "oc" in "duoc") that falsely trigger allergen/diet keywords.
    user_turn_texts = [
        _normalize(str(turn.get("content") or ""))
        for turn in history[-6:]
        if str(turn.get("role") or "").casefold() == "user"
    ]
    combined_text = " ".join(user_turn_texts + [normalized])
    # Diacritic-preserving counterpart, used only for _DIACRITIC_SENSITIVE_TERMS:
    # "cua"/"muc" must appear literally unaccented to count as the seafood
    # word, not as the accented "cửa"/"của"/"mức" that collide with it once
    # diacritics are stripped. normalize_vietnamese() also strips diacritics
    # internally (only restoring a fixed domain list that doesn't cover these
    # words), so it cannot be reused here — this needs the user's literal
    # original characters, untouched.
    accented_user_turns = [
        _casefold_preserve_diacritics(str(turn.get("content") or ""))
        for turn in history[-6:]
        if str(turn.get("role") or "").casefold() == "user"
    ]
    combined_text_accented = " ".join(accented_user_turns + [_casefold_preserve_diacritics(message)])

    intent_result = classify_intent_with_history(message, history)
    language = _detect_language(message)
    allergens = (
        _match_terms(combined_text, ALLERGEN_KEYWORDS, accented_text=combined_text_accented)
        if _has_allergy_context(combined_text)
        else []
    )
    diet = _match_terms(combined_text, DIET_KEYWORDS, accented_text=combined_text_accented)
    spice = _detect_spice(combined_text)
    budget_vnd = _extract_budget(normalized)
    party_size = _extract_party_size(combined_text)
    requested_count = _extract_requested_count(normalized)
    rejection_signal = _has_any(normalized, REJECTION_TERMS) or any(
        _has_any(_normalize(str(turn.get("content") or "")), REJECTION_TERMS)
        for turn in history
        if str(turn.get("role") or "").casefold() == "user"
    )
    category = _detect_category(normalized)
    # A category the guest is allergic to is not a category they are asking for.
    # "Tôi dị ứng hải sản, món nào an toàn?" set allergens=['seafood'] *and*
    # category='hai san', and the two then cancelled out: filtering the menu to
    # seafood while excluding every seafood dish left nothing, so the model was
    # handed no dishes at all and asked the guest to supply the menu it already
    # had — on a safety-critical question.  _is_negated does not catch this
    # because "dị ứng" is a statement of harm, not a negation word.
    if category is not None and category in _ALLERGEN_CATEGORIES_TO_DROP:
        if _ALLERGEN_CATEGORIES_TO_DROP[category] in allergens:
            category = None
    recommendation_thread = _was_recommendation_thread(history, "")
    wants_more_dishes = _is_more_dishes_request(normalized) and not _is_context_only_follow_up(normalized)
    is_recommendation = (
        requested_count is not None
        or _has_any(normalized, RECOMMENDATION_TERMS)
        or (recommendation_thread and wants_more_dishes)
        or intent_result.intent in {"recommend", "order"}
        and _has_any(normalized, ("goi y", "de xuat", "tu van", "nen"))
    )
    # Party size remembered from earlier turns must not block a clear category
    # browse on the current message (e.g. "cac mon lien quan den lau").
    party_size_in_message = _extract_party_size(normalized)
    catalog_browse = category is not None and (
        _has_any(normalized, CATALOG_TERMS)
        or intent_result.intent in {"browse_menu", "ask_price"}
    )
    blocks_catalog = "CUSTOMER_CONFIRMATION_REQUIRED" in detect_guardrail_flags(message)
    is_catalog_only = (
        not is_recommendation
        and not budget_vnd
        and not diet
        and not allergens
        and spice == "unknown"
        and party_size_in_message is None
        and catalog_browse
        and not blocks_catalog
    )

    is_solo_dining = not is_solo_seating_question(normalized) and (
        is_solo_dining_text(combined_text)
        or (party_size == 1 and is_solo_dining_text(normalized))
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
        "is_solo_dining": is_solo_dining,
        "category": category,
    }


def has_hard_dietary_constraints(constraints: dict[str, Any]) -> bool:
    allergens = constraints.get("allergens") or []
    if allergens:
        return True
    diet = constraints.get("diet")
    if isinstance(diet, list):
        return bool(diet)
    return bool(diet and diet not in ("unknown",))


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


# Nhắc tên một món không phải là lời khai dị ứng. Không có cổng này thì
# "Cho xem menu hải sản" đặt allergens=['seafood'] và loại đúng cả 24 món hải sản
# — khách xin xem menu hải sản thì hệ thống xóa sạch món hải sản.
# Danh sách lấy từ 13 câu họ `allergy` trong tập đánh giá; cả 13 đều khớp, còn
# "Cho xem menu hai san" / "Browse seafood menu" thì không khớp dấu nào.
ALLERGY_CONTEXT_TERMS: tuple[str, ...] = (
    "di ung",
    "allergic",
    "allergy",
    "khong an duoc",
    "khong the an",
    "khong an",
    "tranh",
    "khong co",
    "bo qua",
    "khong goi",
    "loai bo",
    "avoid",
    "without",
    "free of",
    "intolerant",
)


def _has_allergy_context(text: str) -> bool:
    return any(term in text for term in ALLERGY_CONTEXT_TERMS)


def _match_terms(
    text: str,
    mapping: dict[str, tuple[str, ...]],
    *,
    accented_text: str | None = None,
) -> list[str]:
    matched: list[str] = []
    for label, terms in mapping.items():
        if any(
            _term_matches(
                accented_text if term in _DIACRITIC_SENSITIVE_PATTERNS and accented_text is not None else text,
                term,
            )
            for term in terms
        ):
            matched.append(label)
    return matched


def _term_matches(text: str, term: str) -> bool:
    # Word-boundary match: bare substrings misfire on normalized Vietnamese
    # ("cua" in "chua"/"cua(của)", "oc" in "duoc", "lac" in "lau"). Terms in
    # _DIACRITIC_SENSITIVE_PATTERNS are matched against diacritic-preserving
    # text using their dedicated pattern instead (see call site), so
    # "cửa"/"của"/"mức" no longer collide with "cua"/"muc".
    pattern = _DIACRITIC_SENSITIVE_PATTERNS.get(term, rf"\b{re.escape(term)}\b")
    return re.search(pattern, text) is not None


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
    return extract_party_size_from_text(normalized)


def _extract_requested_count(normalized: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*(?:mon|dishes|items|món)\b", normalized)
    if match:
        return min(max(int(match.group(1)), 1), 8)
    return None


# Danh mục thực đơn trùng miền với một dị nguyên. Nếu khách khai dị ứng đúng miền
# đó thì danh mục là thứ cần TRÁNH, không phải thứ cần lọc tới.
_ALLERGEN_CATEGORIES_TO_DROP: dict[str, str] = {"hai san": "seafood"}


def _detect_category(normalized: str) -> str | None:
    """Longest whole-phrase match wins.

    A raw substring test made "tráng miệng menu" resolve to `ca phe tra`, because the
    tea alias `tra` sits inside "trang".  The assistant then filtered correctly for
    the wrong category and answered a dessert question with four teas.

    Matching on whole tokens fixes that; taking the longest match keeps a two-word
    alias from losing to a one-word alias that also happens to fit.
    """
    padded = f" {normalized} "
    best: tuple[int, str] | None = None
    for category, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            if f" {alias} " not in padded:
                continue
            if _is_negated(normalized, alias):
                continue
            length = len(alias.split())
            if best is None or length > best[0]:
                best = (length, category)
    return best[1] if best else None


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
    return normalize_query_text(value)


def _casefold_preserve_diacritics(value: str) -> str:
    """Lowercase and collapse whitespace only — keep every original character.

    Used for _DIACRITIC_SENSITIVE_TERMS, where the presence/absence of a
    diacritic is the only thing that distinguishes the real keyword from an
    unrelated common word (see ALLERGEN_KEYWORDS comment).
    """
    return " ".join(value.casefold().split())
