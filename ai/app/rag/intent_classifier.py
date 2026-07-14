"""Rule-based intent classifier for restaurant chatbot.

Classifies user messages into intents and maps each intent
to relevant knowledge base sources for retrieval boosting.
No ML model needed — uses keyword matching on normalized text.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


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
        ["restaurant-info.md", "service-guide.md"],
        ["CMC Restaurant", "giờ mở cửa", "wifi", "phòng VIP", "gửi xe", "Không Gian"],
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
        ],
        ["allergy-dietary.md", "ingredient-nutrition.md", "menu.md"],
        ["dị ứng", "chế độ ăn", "trẻ em", "thành phần", "an toàn"],
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
]


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

    for intent_name, keywords, sources, boost in INTENT_RULES:
        score = _compute_match_score(normalized, keywords)
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
    (r"\bwifi\b", "restaurant_info", ["restaurant-info.md"], ["CMC Restaurant", "wifi", "Tiện Nghi"]),
    (r"\bvip\b", "restaurant_info", ["restaurant-info.md"], ["CMC Restaurant", "phòng VIP", "Không Gian"]),
    (r"\bgui\s*xe\b", "restaurant_info", ["restaurant-info.md"], ["CMC Restaurant", "gửi xe", "Giao Thông"]),
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
    """Compute match score between normalized text and keyword list."""
    if not normalized:
        return 0.0

    matches = 0
    total_weight = 0.0
    words = set(normalized.split())

    for keyword in keywords:
        kw_words = keyword.split()
        weight = len(kw_words)  # Multi-word keywords score higher
        total_weight += weight

        if len(kw_words) == 1:
            if kw_words[0] in words:
                matches += weight
        else:
            # Check if multi-word keyword appears as substring
            if keyword in normalized:
                matches += weight * 1.5  # Bonus for exact phrase match

    return matches / max(total_weight, 1.0)


def _normalize(text: str) -> str:
    """Normalize for intent matching: lowercase, strip diacritics."""
    lower = text.lower().replace("đ", "d")
    nfkd = unicodedata.normalize("NFKD", lower)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(stripped.split())
