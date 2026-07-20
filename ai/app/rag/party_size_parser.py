"""Shared party-size and solo-dining detection for routing constraints."""

from __future__ import annotations

import re

from app.rag.vietnamese_normalizer import normalize_query_text
from app.rag.intent_routing_signals import is_seating_inquiry

VI_WORD_TO_INT: dict[str, int] = {
    "mot": 1,
    "hai": 2,
    "ba": 3,
    "bon": 4,
    "tu": 4,
    "nam": 5,
    "sau": 6,
    "bay": 7,
    "tam": 8,
    "chin": 9,
    "muoi": 10,
    "muoi mot": 11,
    "muoi hai": 12,
    "muoi ba": 13,
    "muoi bon": 14,
    "muoi lam": 15,
}

EN_WORD_TO_INT: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

SOLO_DINING_PATTERN = re.compile(
    r"\b("
    r"mot\s*minh|di\s*mot\s*minh|an\s*mot\s*minh|minh\s*toi|1\s*minh|"
    r"chi\s+co\s+minh|chi\s+minh|"
    r"di\s+an\s+solo|an\s+solo|dining\s+solo|solo\s+(?:dining|thoi|toi|tonight)|"
    r"\balone\b|eating\s+alone|just\s+me|"
    r"1\s+nguoi\s+thoi"
    r")\b"
)

CAPACITY_QUESTION_PATTERN = re.compile(
    r"\b(suc chua|cho ngoi|bao nhieu nguoi|may nguoi|phong bao nhieu)\b"
)


def normalize_party_text(value: str) -> str:
    return normalize_query_text(value)


def is_solo_dining_text(normalized: str) -> bool:
    return SOLO_DINING_PATTERN.search(normalized) is not None


def is_solo_seating_question(normalized: str) -> bool:
    return is_seating_inquiry(normalized)


def is_capacity_info_question(normalized: str) -> bool:
    if not CAPACITY_QUESTION_PATTERN.search(normalized):
        return False
    return not any(
        term in normalized
        for term in ("an gi", "goi y", "goi mon", "dat mon", "recommend", "suggest")
    )


def extract_party_size_from_text(normalized: str) -> int | None:
    """Parse party size from normalized user text."""

    if is_solo_seating_question(normalized):
        return None
    if is_solo_dining_text(normalized):
        return 1

    digit_patterns = (
        r"\b(\d{1,2})\s*(?:nguoi|person|people|pax|khach)\b",
        r"\bcho\s*(\d{1,2})\s*(?:nguoi|person|people|pax)\b",
        r"\bparty\s*of\s*(\d{1,2})\b",
        r"\btable\s*for\s*(\d{1,2})\b",
    )
    for pattern in digit_patterns:
        match = re.search(pattern, normalized)
        if match:
            return min(max(int(match.group(1)), 1), 20)

    for words, value in sorted(VI_WORD_TO_INT.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(words)}\s+nguoi\b", normalized):
            return min(max(value, 1), 20)

    for words, value in EN_WORD_TO_INT.items():
        if re.search(rf"\b{re.escape(words)}\s+people\b", normalized):
            return min(max(value, 1), 20)
        if re.search(rf"\btable\s+for\s+{re.escape(words)}\b", normalized):
            return min(max(value, 1), 20)

    return None
