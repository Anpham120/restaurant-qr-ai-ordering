"""Rule-based intent classifier for restaurant chatbot.

Classifies user messages into intents and maps each intent
to relevant knowledge base sources for retrieval boosting.
No ML model needed — uses keyword matching on normalized text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.rag.vietnamese_normalizer import normalize_query_text


@dataclass(frozen=True)
class IntentResult:
    """Result of intent classification."""
    intent: str
    confidence: float  # 0.0–1.0
    source_hints: tuple[str, ...]  # KB files to prioritize
    query_boost_terms: tuple[str, ...]  # Extra terms to add to retrieval query


# Intent definitions: (intent_name, keywords, source_hints, boost_terms)
# boost_terms should contain EXACT words that appear in the KB files for BM25 matching
INTENT_RULES: list[tuple[str, list[str], list[str], list[str]]] = [
    # Browse menu
    (
        "browse_menu",
        [
            "xem menu", "thuc don", "co gi an", "an gi",
            "doi", "co mon", "cho xem", "menu",
            "mon ngon", "an ngon", "uong gi", "mon gi",
            "danh sach mon", "co nhung mon", "mon nao",
            "ngon", "uong", "khuyen",
        ],
        ["menu.md", "combo-pairing.md"],
        ["Phở bò", "Cơm sườn", "Lẩu", "Bún bò", "gỏi cuốn", "menu", "thực đơn"],
    ),
    # Ask price
    (
        "ask_price",
        [
            "bao nhieu", "gia", "tien", "bao nhieu tien",
            "gia ca", "phi", "gia bao nhieu", "mac", "re",
            "nhiu",
        ],
        ["menu.md"],
        ["giá", "menu", "Phở bò", "Cơm sườn"],
    ),
    # Order food
    (
        "order",
        [
            "dat mon", "dat luon", "goi mon", "them vao gio",
            "mua", "order", "chot don", "gui don",
            "dat cho toi", "goi cho toi", "them", "phan",
        ],
        ["ordering-policy.md", "menu.md"],
        ["đặt món", "giỏ hàng", "chính sách đặt món"],
    ),
    # Payment
    (
        "payment",
        [
            "tinh tien", "thanh toan", "tra tien", "bill",
            "hoa don", "vietqr", "chuyen khoan", "the",
            "tien mat", "chia bill", "voucher", "ma giam",
        ],
        ["payment-methods.md", "ordering-policy.md"],
        ["thanh toán", "phương thức", "hóa đơn"],
    ),
    # Restaurant info
    (
        "restaurant_info",
        [
            "mo cua", "dong cua", "gio", "dia chi",
            "o dau", "wifi", "gui xe", "do xe",
            "phong vip", "suc chua", "ban", "cho ngoi",
            "nha ve sinh", "toilet", "hotline", "lien he",
            "quan", "nha hang",
        ],
        ["restaurant-info.md", "faq.md", "service-guide.md"],
        ["CMC Restaurant", "giờ mở cửa", "wifi", "mật khẩu", "phòng VIP", "gửi xe", "Không Gian"],
    ),
    # Dietary / allergy
    (
        "dietary",
        [
            "di ung", "allergy", "chay", "thuan chay",
            "kieng", "keto", "gluten", "an duoc",
            "be an", "tre em", "khong an duoc",
            "lactose", "dau phong", "hai san",
            "protein", "calo", "dinh duong",
            "cho be", "em be", "tre nho", "con nho",
            "vegetarian", "vegan", "halal", "low carb",
        ],
        ["allergy-dietary.md", "vegan-halal-keto.md", "ingredient-nutrition.md", "menu.md"],
        ["dị ứng", "chế độ ăn", "trẻ em", "thành phần", "an toàn", "chay"],
    ),
    # Promotion
    (
        "promotion",
        [
            "khuyen mai", "giam gia", "uu dai", "sale",
            "promotion", "combo", "tiet kiem",
        ],
        ["seasonal-promotion.md", "combo-pairing.md"],
        ["khuyến mãi", "giảm giá", "ưu đãi"],
    ),
    # Recommend
    (
        "recommend",
        [
            "goi y", "de xuat", "tu van", "nen an",
            "recommend", "suggest", "combo cho",
            "nhom", "nguoi", "an toi", "an trua",
        ],
        ["combo-pairing.md", "data-mining-insights.md", "menu.md"],
        ["gợi ý", "đề xuất", "combo", "phù hợp"],
    ),
    # Service / how-to
    (
        "service",
        [
            "cach dat", "huong dan", "lam sao",
            "qr", "quet ma", "goi nhan vien",
            "ghi chu", "them da", "giam cay",
        ],
        ["service-guide.md", "ordering-policy.md"],
        ["hướng dẫn", "cách", "sử dụng"],
    ),
    # Staff escalation / complaint
    (
        "staff_escalation",
        [
            "gap nhan vien", "goi quan ly", "gap quan ly",
            "khieu nai", "phan nan", "co van de",
            "hoan tien", "phuc vu truc tiep", "nhan vien ho tro",
        ],
        ["staff-escalation.md", "service-guide.md"],
        ["nhân viên", "quản lý", "khiếu nại", "escalate"],
    ),
    # Spice level
    (
        "spice_level",
        [
            "do cay", "cay muc", "muc cay", "cay khong",
            "cay co", "thang cay", "cay lam khong", "cay nhu the nao",
        ],
        ["spice-flavor-scale.md", "menu.md"],
        ["thang cay", "mức cay", "cay đậm"],
    ),
    # Occasion dining
    (
        "occasion",
        [
            "ky niem", "ngay cuoi", "anniversary", "hen ho",
            "tiep khach", "cong ty", "doi tac", "lien hoan",
            "sinh nhat", "tiec",
            "office lunch", "quick lunch", "business lunch",
            "an trua nhanh", "lunch nhanh", "trua van phong",
        ],
        ["occasion-dining.md", "combo-pairing.md"],
        ["dịp", "kỷ niệm", "tiệc", "combo"],
    ),
    # Kids / elderly audience
    (
        "kids_elderly",
        [
            "tre em", "tre con", "be", "children", "child portion",
            "kids menu", "kid friendly", "nguoi cao tuoi", "elderly", "senior",
        ],
        ["kids-elderly.md", "faq.md"],
        ["trẻ em", "mềm", "dễ nhai"],
    ),
]


def classify_intent_with_history(
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> IntentResult:
    """Classify intent using current message plus recent user history."""
    result = classify_intent(message)
    history = history or []
    normalized = _normalize(message)

    if result.confidence >= 0.1 and result.intent not in {"general"}:
        return result

    history_text = " ".join(
        _normalize(str(turn.get("content") or ""))
        for turn in history[-6:]
        if str(turn.get("role") or "").casefold() == "user"
    )
    group_context_terms = ("nhom", "nguoi", "goi y", "mon", "an chung", "dong nguoi", "de xuat")
    elliptical_terms = ("thi sao", "the con", "con gi", "ve thanh toan", "thanh toan thi sao")
    payment_terms = ("thanh toan", "tinh tien", "tra tien", "hoa don", "bill")

    if any(term in normalized for term in elliptical_terms) or any(
        term in normalized for term in payment_terms
    ):
        if any(term in history_text for term in group_context_terms) or any(
            term in history_text for term in payment_terms
        ):
            payment_result = classify_intent("thanh toan nhom an chung")
            if payment_result.intent == "payment":
                return IntentResult(
                    intent="payment",
                    confidence=max(result.confidence, 0.35),
                    source_hints=payment_result.source_hints,
                    query_boost_terms=payment_result.query_boost_terms,
                )

    return result


def classify_intent(message: str) -> IntentResult:
    """Classify user message into an intent.

    Returns the highest-confidence matching intent.
    Falls back to 'general' if no intent matches.
    """
    normalized = _normalize(message)

    best_intent = "general"
    best_score = 0.0
    best_sources: list[str] = []
    best_boost: list[str] = []

    # Collect all scored intents for conflict resolution
    scored_intents: list[tuple[str, float, list[str], list[str]]] = []

    for intent_name, keywords, sources, boost in INTENT_RULES:
        score = _compute_match_score(normalized, keywords)
        scored_intents.append((intent_name, score, sources, boost))
        if score > best_score:
            best_score = score
            best_intent = intent_name
            best_sources = sources
            best_boost = boost

    # Implicit intent detection for edge cases
    if best_score < 0.1:
        implicit = _detect_implicit_intent(normalized, message)
        if implicit:
            return implicit

    # Threshold: need at least 0.1 match score
    if best_score < 0.1:
        return IntentResult(
            intent="general",
            confidence=0.0,
            source_hints=(),
            query_boost_terms=(),
        )

    # Resolve conflicts when multiple intents have similar scores
    resolved = _resolve_intent_conflicts(
        normalized, scored_intents, best_intent, best_score
    )
    if resolved is not None:
        return resolved

    return IntentResult(
        intent=best_intent,
        confidence=min(best_score, 1.0),
        source_hints=tuple(best_sources),
        query_boost_terms=tuple(best_boost),
    )


# Common Vietnamese food names (no diacritics) for implicit menu detection
_FOOD_NAMES = {
    "pho", "bun", "com", "lau", "banh", "che", "goi", "cha",
    "ga", "bo", "heo", "tom", "ca", "muc", "oc", "cua",
    "nuoc", "tra", "bia", "cafe", "sinh to",
}

# Implicit expressions mapping to intents
_IMPLICIT_PATTERNS: list[tuple[str, str, list[str], list[str]]] = [
    # "Tôi đói quá", "đói bụng"
    (r"\bdoi\b", "browse_menu", ["menu.md"], ["Phở bò", "Cơm sườn", "Lẩu", "menu"]),
    # "Khát nước"
    (r"\bkhat\b", "browse_menu", ["menu.md"], ["đồ uống", "nước", "trà", "sinh tố"]),
    # "wifi", "phòng VIP" — single keyword is enough for restaurant_info
    (r"\bwifi\b", "restaurant_info", ["restaurant-info.md", "faq.md"], ["CMC Restaurant", "wifi", "Tiện Nghi", "mật khẩu"]),
    (r"\bvip\b", "restaurant_info", ["restaurant-info.md"], ["CMC Restaurant", "phòng VIP", "Không Gian"]),
    (r"\bgui\s*xe\b", "restaurant_info", ["restaurant-info.md", "faq.md"], ["CMC Restaurant", "gửi xe", "Giao Thông", "đậu xe"]),
    (r"\btre\s*(em|con)\b", "dietary", ["allergy-dietary.md", "faq.md", "menu.md"], ["trẻ em", "an toàn", "dị ứng"]),
    (r"\bmo\s*cua\b", "restaurant_info", ["restaurant-info.md"], ["CMC Restaurant", "giờ mở cửa", "Giờ Hoạt Động"]),
]


def _detect_implicit_intent(normalized: str, original: str) -> IntentResult | None:
    """Detect intent from implicit expressions and food name mentions."""
    import re as _re

    # Check implicit patterns
    for pattern, intent, sources, boost in _IMPLICIT_PATTERNS:
        if _re.search(pattern, normalized):
            return IntentResult(
                intent=intent,
                confidence=0.3,
                source_hints=tuple(sources),
                query_boost_terms=tuple(boost),
            )

    # Check if query contains food names → ask_price or browse_menu
    words = set(normalized.split())
    food_matches = words & _FOOD_NAMES
    if food_matches:
        # Contains food name + question words → likely asking about that food
        if any(w in normalized for w in ("bao nhieu", "nhiu", "gia", "tien")):
            return IntentResult(
                intent="ask_price",
                confidence=0.4,
                source_hints=("menu.md",),
                query_boost_terms=("giá", "menu", "Phở bò", "Cơm sườn"),
            )
        return IntentResult(
            intent="browse_menu",
            confidence=0.3,
            source_hints=("menu.md",),
            query_boost_terms=("Phở bò", "Cơm sườn", "menu"),
        )

    return None


def _compute_match_score(normalized: str, keywords: list[str]) -> float:
    """Compute match score with context awareness.

    Unlike the previous pure-count approach, this version:
    1. Checks for negation/context words near keyword matches
    2. Penalises single-char token matches that are likely false positives
    3. Gives extra weight to multi-word phrase matches (stronger signal)
    """
    if not normalized:
        return 0.0

    matches = 0.0
    total_weight = 0.0
    words = normalized.split()
    word_set = set(words)

    for keyword in keywords:
        kw_words = keyword.split()
        weight = len(kw_words)  # Multi-word keywords score higher
        total_weight += weight

        if len(kw_words) == 1:
            if kw_words[0] in word_set:
                # Check context: is this keyword negated or in a different context?
                kw_index = _find_word_index(words, kw_words[0])
                if kw_index is not None:
                    context_window = words[max(0, kw_index - 3):kw_index + 4]
                    context_text = " ".join(context_window)
                    # Negation near keyword reduces score
                    if any(neg in context_text for neg in (
                        "khong", "chua", "dung", "het", "tranh",
                    )):
                        matches += weight * 0.3  # Reduced weight for negated context
                    else:
                        matches += weight
                else:
                    matches += weight
        else:
            # Check if multi-word keyword appears as substring
            if keyword in normalized:
                matches += weight * 1.5  # Bonus for exact phrase match

    return matches / max(total_weight, 1.0)


def _find_word_index(words: list[str], target: str) -> int | None:
    """Find the index of target word in words list."""
    for i, w in enumerate(words):
        if w == target:
            return i
    return None


# Intent conflict resolution rules.
# When two intents score similarly, these patterns determine which one wins
# based on the full sentence context.
_INTENT_CONFLICT_PATTERNS: list[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = [
    # (intent_a, intent_b, a_wins_if_has_terms, b_wins_if_has_terms)
    # "có món chay không?" → dietary, not browse_menu
    ("browse_menu", "dietary", ("menu", "xem", "danh sach"), ("chay", "kieng", "di ung", "allergy", "vegan", "keto")),
    # "giá phòng VIP?" → restaurant_info, not ask_price
    ("ask_price", "restaurant_info", ("pho", "bun", "com", "lau", "mon"), ("phong", "vip", "ban", "xe", "gui")),
    # "2 người ngồi đâu?" → restaurant_info, not recommend
    ("recommend", "restaurant_info", ("an", "goi y", "tu van", "mon"), ("ngoi", "ban", "cho", "phong")),
    # "đặt bàn trước" → restaurant_info, not order
    ("order", "restaurant_info", ("mon", "them", "gio"), ("ban", "truoc", "phong", "cho")),
    # "bún bò có cay không?" → spice_level, not browse_menu
    ("browse_menu", "spice_level", ("xem", "menu", "danh sach"), ("cay", "muc cay", "do cay")),
]


def _resolve_intent_conflicts(
    normalized: str,
    scored_intents: list[tuple[str, float, list[str], list[str]]],
    best_intent: str,
    best_score: float,
) -> IntentResult | None:
    """Resolve ambiguity when multiple intents have similar scores.

    Uses sentence-level context patterns to pick the correct intent
    instead of relying solely on keyword count.
    """
    if best_score < 0.05:
        return None

    # Build a dict of intent -> (score, sources, boost)
    intent_map = {
        name: (score, sources, boost)
        for name, score, sources, boost in scored_intents
    }

    for intent_a, intent_b, a_context_terms, b_context_terms in _INTENT_CONFLICT_PATTERNS:
        score_a = intent_map.get(intent_a, (0.0, [], []))[0]
        score_b = intent_map.get(intent_b, (0.0, [], []))[0]

        # Only resolve if both intents are in contention
        if score_a < 0.05 or score_b < 0.05:
            continue
        # Only resolve if scores are close enough or the "wrong" one won
        if best_intent not in (intent_a, intent_b):
            continue

        has_a_context = any(term in normalized for term in a_context_terms)
        has_b_context = any(term in normalized for term in b_context_terms)

        # If the sentence has context for B but not A, B should win
        if has_b_context and not has_a_context and best_intent == intent_a:
            _, sources_b, boost_b = intent_map[intent_b]
            return IntentResult(
                intent=intent_b,
                confidence=min(max(score_b, best_score * 0.8), 1.0),
                source_hints=tuple(sources_b),
                query_boost_terms=tuple(boost_b),
            )
        # If the sentence has context for A but not B, A should win
        if has_a_context and not has_b_context and best_intent == intent_b:
            _, sources_a, boost_a = intent_map[intent_a]
            return IntentResult(
                intent=intent_a,
                confidence=min(max(score_a, best_score * 0.8), 1.0),
                source_hints=tuple(sources_a),
                query_boost_terms=tuple(boost_a),
            )

    return None


def _normalize(text: str) -> str:
    return normalize_query_text(text)
