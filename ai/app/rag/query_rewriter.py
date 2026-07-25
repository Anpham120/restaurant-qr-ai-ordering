"""Query rewriting for improved RAG retrieval.

Pipeline:
1. Vietnamese normalization (teencode, no-diacritics, slang)
2. Intent classification → source hints + boost terms
3. Synonym expansion
4. Price/category query extraction
5. Conversation history context

Rewrites short/ambiguous user queries into richer retrieval queries.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.rag.intent_classifier import IntentResult, classify_intent_with_history
from app.rag.vietnamese_normalizer import normalize_vietnamese, normalize_query_text


# ---------------------------------------------------------------------------
# Synonym / Expansion Maps
# ---------------------------------------------------------------------------

QUERY_EXPANSIONS: dict[str, list[str]] = {
    # Drinks
    "đồ uống": ["nước uống", "trà", "cà phê", "sinh tố", "nước ép", "bia", "cocktail"],
    "nước uống": ["nước uống", "trà", "cà phê", "sinh tố", "nước ép"],
    "trà": ["trà nóng", "trà đá", "trà sữa"],
    "bia": ["bia", "đồ uống có cồn"],
    "cà phê": ["cà phê", "espresso", "cappuccino", "latte"],
    # Food categories
    "món chính": ["món chính", "cơm", "phở", "bún"],
    "khai vị": ["khai vị", "appetizer", "món nhẹ"],
    "tráng miệng": ["tráng miệng", "dessert", "chè", "bánh"],
    "đồ ăn nhẹ": ["đồ ăn nhẹ", "snack", "khai vị", "món phụ"],
    # Dietary
    "chay": ["chay", "thuần chay", "vegetarian", "vegan"],
    "keto": ["keto", "ít carb", "low carb", "protein cao"],
    "ăn kiêng": ["ăn kiêng", "diet", "ít calo", "healthy"],
    # Combo/pairing
    "combo": ["combo", "set", "bộ", "phần ăn kèm"],
    "khuyến mãi": ["khuyến mãi", "giảm giá", "promotion", "ưu đãi"],
    # Ordering
    "đặt món": ["đặt món", "thêm vào giỏ hàng", "order"],
    "thanh toán": ["thanh toán", "hóa đơn", "trả tiền", "tính tiền"],
    # Queries
    "dị ứng": ["dị ứng", "allergy", "không ăn được"],
    "thanh mát": ["thanh mát", "mát", "nhẹ nhàng", "salad", "nước ép"],
    "protein cao": ["protein cao", "nhiều đạm", "thịt", "cá", "trứng"],
    "trẻ em": ["trẻ em", "bé", "con nhỏ", "em bé", "trẻ nhỏ"],
}

# Patterns to extract item names from queries
PRICE_QUERY_PATTERN = re.compile(
    r"^(.+?)\s+(?:bao\s+nhiêu|giá\s+bao|giá)\s*(?:tiền)?[?.!]*$",
    re.IGNORECASE,
)

MENU_QUERY_PATTERN = re.compile(
    r"^(?:cho\s+(?:xem|tôi\s+xem)|xem)\s+(.+?)$",
    re.IGNORECASE,
)


def rewrite_query(
    message: str,
    history: list[dict[str, Any]] | None = None,
    *,
    intent: IntentResult | None = None,
    session_state: dict[str, Any] | None = None,
    rolling_summary: str = "",
) -> str:
    """Rewrite a user query for better RAG retrieval.

    Full pipeline:
    1. Normalize Vietnamese (teencode, diacritics, slang)
    2. Classify intent → get source hints + boost terms
    3. Expand synonyms
    4. Extract item name / category
    5. Add conversation context

    Returns the rewritten query string.
    """
    if not message or not message.strip():
        return message

    original = message.strip()

    # Step 1: Normalize Vietnamese
    normalized = normalize_vietnamese(original)

    # Step 2: Intent classification (reuse when caller already classified)
    if intent is None:
        intent = classify_intent_with_history(original, history)

    parts: list[str] = [original]  # Keep original first

    # Add normalized version if different
    if normalized != original.lower() and normalized != original:
        parts.append(normalized)

    # Step 3: Intent boost terms
    if intent.query_boost_terms:
        parts.append(" ".join(intent.query_boost_terms))

    # Step 4: Expand synonyms (on normalized text)
    expansions = _expand_synonyms(normalized)
    if expansions:
        parts.append(" ".join(expansions))

    # Step 5: Extract item name from price queries
    item_name = _extract_item_from_price_query(normalized)
    if item_name:
        parts.append(f"menu {item_name} giá tiền")

    # Step 6: Extract category from browse queries
    category = _extract_category_query(normalized)
    if category:
        parts.append(f"danh sách {category} menu")

    # Step 7: Context from recent history
    if history:
        context = _extract_history_context(history)
        if context:
            parts.append(context)

    reference_context = _extract_reference_context(original, history or [], session_state or {})
    if reference_context:
        parts.append(reference_context)

    typed_context = _extract_typed_state_context(session_state or {}, rolling_summary)
    if typed_context:
        parts.append(typed_context)

    # Dedupe and join
    if len(parts) <= 1:
        return normalized if normalized != original else original

    return " | ".join(parts)


def _extract_reference_context(
    message: str,
    history: list[dict[str, Any]],
    session_state: dict[str, Any],
) -> str:
    normalized = normalize_query_text(message)
    referential_terms = (
        "cai do",
        "mon do",
        "mon nay",
        "no bao nhieu",
        "cai nay",
        "that one",
        "it cost",
    )
    if not any(term in normalized for term in referential_terms):
        return ""

    for turn in reversed(history):
        actions = list(turn.get("suggested_cart_actions") or [])
        for action in reversed(actions):
            item_id = str(action.get("menu_item_id") or "").strip()
            name = str(action.get("name") or "").strip()
            if item_id or name:
                return f"tham chieu mon {name} {item_id}".strip()

    for key in (
        "referenced_menu_item_ids",
        "accepted_menu_item_ids",
        "suggested_menu_item_ids",
    ):
        ids = [str(value).strip() for value in (session_state.get(key) or []) if str(value).strip()]
        if ids:
            return f"tham chieu menu id {ids[-1]}"
    return ""


def _extract_typed_state_context(session_state: dict[str, Any], rolling_summary: str) -> str:
    parts: list[str] = []
    constraints = session_state.get("constraints") or {}
    for key in sorted(constraints)[:6]:
        value = constraints[key]
        if value not in (None, "", [], {}):
            parts.append(f"{key}={value}")
    for fact in list(session_state.get("facts") or [])[:4]:
        kind = str(fact.get("kind") or "").strip()
        value = str(fact.get("value") or "").strip()
        if kind and value:
            parts.append(f"{kind}={value}")
    summary = normalize_query_text(rolling_summary)[:160].strip()
    if summary:
        parts.append(f"tom tat phien {summary}")
    return " ".join(parts)


def _expand_synonyms(text: str) -> list[str]:
    """Find matching expansion terms for the text."""
    expansions: list[str] = []
    text_lower = text.lower()
    for trigger, terms in QUERY_EXPANSIONS.items():
        if trigger in text_lower:
            expansions.extend(terms)
    return expansions


def _extract_item_from_price_query(text: str) -> str | None:
    """Extract item name from price-asking queries."""
    match = PRICE_QUERY_PATTERN.match(text)
    if match:
        return match.group(1).strip()
    return None


def _extract_category_query(text: str) -> str | None:
    """Extract category from browse queries like 'cho xem đồ uống'."""
    match = MENU_QUERY_PATTERN.match(text)
    if match:
        return match.group(1).strip()
    return None


RECOMMENDATION_CONTEXT_TERMS = (
    "goi y",
    "de xuat",
    "tu van",
    "nhom",
    "nguoi",
    "mon khac",
    "dong nguoi",
    "nhieu nguoi",
    "an chung",
    "combo",
)


def _extract_history_context(history: list[dict[str, Any]], max_turns: int = 3) -> str:
    """Extract relevant context from recent conversation history."""
    context_terms: list[str] = []
    recent = history[-max_turns * 2:]
    user_turns = [
        turn
        for turn in recent
        if str(turn.get("role") or "").casefold() == "user" and str(turn.get("content") or "").strip()
    ][-2:]

    for turn in user_turns:
        content = str(turn.get("content") or "").strip()
        normalized = normalize_query_text(content)
        snippet = normalized[:80].strip()
        if snippet:
            context_terms.append(snippet)

        party_match = re.search(r"\b(\d{1,2})\s+nguoi\b", normalized)
        if party_match:
            party_size = int(party_match.group(1))
            context_terms.append(f"{party_match.group(1)} nguoi")
            if party_size >= 4:
                context_terms.extend(
                    ["lau an chung", "mon chia se", "met thap cam", "hai san nguyen"]
                )

        for term in RECOMMENDATION_CONTEXT_TERMS:
            if term in normalized:
                context_terms.append(term)

    for turn in recent:
        role = str(turn.get("role") or "").casefold()
        content = str(turn.get("content") or "")
        if role == "user" and content:
            text_lower = content.lower()
            for trigger in QUERY_EXPANSIONS:
                if trigger in text_lower:
                    context_terms.append(trigger)

    deduped: list[str] = []
    seen: set[str] = set()
    for term in context_terms:
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)

    return " ".join(deduped[:8]) if deduped else ""
