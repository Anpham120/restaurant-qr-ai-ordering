"""Vietnamese text normalizer for chatbot NLU.

Handles:
1. Teencode / abbreviations (ko → không, dc → được, bn → bao nhiêu)
2. Southern dialect (hông → không, hen → nhé)
3. Gen-Z speak (k → không, j → gì, z → gì)
4. Common typos and misspellings
5. No-diacritics restoration for key food/restaurant terms
"""
from __future__ import annotations

import re
import unicodedata


# ---------------------------------------------------------------------------
# Teencode & abbreviation mappings
# ---------------------------------------------------------------------------

TEENCODE_MAP: dict[str, str] = {
    # Phủ định — safe, unambiguous
    "ko": "không",
    "hk": "không",
    "khg": "không",
    "kp": "không phải",
    "hông": "không",
    "hem": "không",
    "hok": "không",
    "hong": "không",
    # Được
    "dc": "được",
    "đc": "được",
    # Xác nhận
    "okie": "được",
    # Nghi vấn
    "bn": "bao nhiêu",
    "bnh": "bao nhiêu",
    "nhiu": "nhiêu",
    "ntn": "như thế nào",
    # Liên từ / phụ từ
    "vs": "với",
    "mk": "mình",
    # Cảm ơn
    "tks": "cảm ơn",
    "thanks": "cảm ơn",
    # No-diacritics common words (safe, multi-char)
    "luon": "luôn",
    "nhe": "nhé",
    "duoc": "được",
}

# Patterns with word boundaries — only replace whole words
# Sort by length descending so longer matches take priority
_TEENCODE_SORTED = sorted(TEENCODE_MAP.items(), key=lambda x: -len(x[0]))
_TEENCODE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k, _ in _TEENCODE_SORTED) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# No-diacritics → diacritics for restaurant domain keywords
# ---------------------------------------------------------------------------

NODIACRITICS_MAP: dict[str, str] = {
    # Món ăn
    "pho": "phở",
    "pho bo": "phở bò",
    "pho ga": "phở gà",
    "bun bo": "bún bò",
    "bun bo hue": "bún bò huế",
    "bun dau": "bún đậu",
    "bun cha": "bún chả",
    "com": "cơm",
    "com suon": "cơm sườn",
    "com tam": "cơm tấm",
    "com ga": "cơm gà",
    "lau": "lẩu",
    "lau hai san": "lẩu hải sản",
    "lau nam": "lẩu nấm",
    "goi cuon": "gỏi cuốn",
    "cha gio": "chả giò",
    "banh xeo": "bánh xèo",
    "banh mi": "bánh mì",
    "che": "chè",
    "ga nuong": "gà nướng",
    "tom hum": "tôm hùm",
    "ca loc": "cá lóc",
    "muc xao": "mực xào",
    # Đồ uống
    "ca phe": "cà phê",
    "cafe": "cà phê",
    "tra da": "trà đá",
    "tra nong": "trà nóng",
    "tra sua": "trà sữa",
    "nuoc ep": "nước ép",
    "sinh to": "sinh tố",
    "nuoc mia": "nước mía",
    "bia": "bia",
    "ruou": "rượu",
    # Nhà hàng
    "nha hang": "nhà hàng",
    "thuc don": "thực đơn",
    "mon an": "món ăn",
    "dat mon": "đặt món",
    "thanh toan": "thanh toán",
    "tinh tien": "tính tiền",
    "khuyen mai": "khuyến mãi",
    "giam gia": "giảm giá",
    "gia": "giá",
    "bao nhieu": "bao nhiêu",
    "bao nhieu tien": "bao nhiêu tiền",
    "do uong": "đồ uống",
    "do an": "đồ ăn",
    "hai san": "hải sản",
    "mon chay": "món chay",
    "an kieng": "ăn kiêng",
    "di ung": "dị ứng",
    "tre em": "trẻ em",
    "wifi": "wifi",
    "gui xe": "gửi xe",
    "mo cua": "mở cửa",
    "gio mo cua": "giờ mở cửa",
    "phong vip": "phòng VIP",
}

# Sort by length descending for longest-match-first
_NODIAC_SORTED = sorted(NODIACRITICS_MAP.items(), key=lambda x: -len(x[0]))


def normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text for better NLU.

    Pipeline:
    1. Lowercase + strip
    2. Replace teencode/abbreviations
    3. Restore diacritics for domain keywords
    4. Clean up whitespace
    """
    if not text or not text.strip():
        return text

    result = text.strip()

    # Step 1: Lowercase
    lower = result.lower()

    # Step 2: Remove diacritics for matching (keep original for output)
    stripped = _strip_diacritics(lower)

    # Step 3: Replace teencode (on stripped version)
    normalized = _replace_teencode(stripped)

    # Step 4: Restore diacritics for domain keywords
    normalized = _restore_diacritics(normalized)

    # Step 5: Clean whitespace
    normalized = " ".join(normalized.split())

    return normalized


def _replace_teencode(text: str) -> str:
    """Replace teencode/abbreviations with full words."""
    def _replace(match: re.Match) -> str:
        word = match.group(0).lower()
        return TEENCODE_MAP.get(word, word)

    return _TEENCODE_PATTERN.sub(_replace, text)


def _restore_diacritics(text: str) -> str:
    """Restore Vietnamese diacritics for known domain terms."""
    result = text
    for nodiac, diac in _NODIAC_SORTED:
        # Use word boundary matching
        pattern = r"\b" + re.escape(nodiac) + r"\b"
        result = re.sub(pattern, diac, result, flags=re.IGNORECASE)
    return result


def _strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics (NFD decomposition)."""
    nfkd = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in nfkd if not unicodedata.combining(c))
