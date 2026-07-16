from __future__ import annotations

import re
import unicodedata
from typing import Iterable


ORDER_CREATION_PATTERNS = [
    r"\bdat\s+luon\b",
    r"\bdat\s+mon\b",
    r"\bthem\s+vao\s+gio\b",
    r"\bthanh\s+toan\b",
    r"\bchot\s+don\b",
    r"\bgui\s+don\b",
    r"\bmua\s+luon\b",
]

OFF_TOPIC_PATTERNS = [
    r"\bthoi\s+tiet\b",
    r"\bbong\s+da\b",
    r"\bchinh\s+tri\b",
    r"\btin\s+tuc\b",
    r"\bchung\s+khoan\b",
    r"\bcrypto\b",
    r"\bbitcoin\b",
    r"\blam\s+bai\b",
    r"\bgiai\s+toan\b",
    r"\bviet\s+code\b",
    r"\blap\s+trinh\b",
    # Additional off-topic patterns
    r"\bphim\s+(?:hay|moi)\b",
    r"\bnhac\s+(?:hay|moi)\b",
    r"\bgame\b",
    r"\btrinh\s+duyet\b",
    r"\bdownload\b",
    r"\bhack\b",
    r"\bpassword\b",
    r"\bai\s+la\s+(?:tong\s+thong|thu\s+tuong)\b",
    r"\bthe\s+gioi\b.*\b(?:chien\s+tranh|xung\s+dot)\b",
]

PROFANITY_PATTERNS = [
    r"\bdm\b",
    r"\bvcl\b",
    r"\bngu\b",
    r"\bdien\b.*\bchung\b",
    r"\bmat\s+day\b",
    # Additional profanity
    r"\bcc\b",
    r"\bcl\b",
    r"\bdo\s+ngu\b",
    r"\blon\b",
    r"\bdit\s+me\b",
    r"\bdo\s+cho\b",
    r"\bkho\s+dam\b",
]

PROMPT_INJECTION_PATTERNS = [
    r"\bignore\s+(?:previous|all|above)\b",
    r"\bdisregard\b.*\binstructions?\b",
    r"\bsystem\s+prompt\b",
    r"\byou\s+are\s+now\b",
    r"\bpretend\s+(?:to\s+be|you\s+are)\b",
    r"\bact\s+as\b",
    r"\brole\s*play\b",
    r"\bjailbreak\b",
    r"\bdan\s+mode\b",
    r"\bbo\s+qua\s+(?:luat|quy\s+tac|chinh\s+sach)\b",
    r"\bkhong\s+can\s+(?:tuan\s+theo|lam\s+theo)\b",
    r"\bgia\s+vo\b.*\b(?:la|lam)\b",
    r"\blam\s+nhu\b.*\b(?:khong\s+co|khong\s+phai)\b",
    r"\boverride\b",
    r"\bbypass\b",
]

PII_PATTERNS = [
    r"\b\d{9,12}\b",                          # CMND / CCCD (9-12 digits)
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card number
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b(?:0\d{9,10})\b",                     # Phone number (Vietnamese)
]


def detect_guardrail_flags(message: str) -> list[str]:
    """Scan *message* for guardrail-triggering patterns and return flag names.

    Flags:
    - CUSTOMER_CONFIRMATION_REQUIRED: user intends to place an order via chat.
    - PRICE_FABRICATION_BLOCKED: user asks AI to fabricate prices.
    - MENU_FABRICATION_BLOCKED: user asks for items outside the menu.
    - OUT_OF_SCOPE: message is unrelated to restaurant/food.
    - PROFANITY_DETECTED: message contains offensive language.
    """
    normalized = _normalize(message)
    flags: list[str] = []

    if any(re.search(pattern, normalized) for pattern in ORDER_CREATION_PATTERNS):
        flags.append("CUSTOMER_CONFIRMATION_REQUIRED")

    if "gia" in normalized and ("tu tao" in normalized or "bia" in normalized or "re hon" in normalized):
        flags.append("PRICE_FABRICATION_BLOCKED")

    if "mon moi" in normalized or "ngoai thuc don" in normalized or "tu nghi" in normalized:
        flags.append("MENU_FABRICATION_BLOCKED")

    if any(re.search(pattern, normalized) for pattern in OFF_TOPIC_PATTERNS):
        flags.append("OUT_OF_SCOPE")

    if any(re.search(pattern, normalized) for pattern in PROFANITY_PATTERNS):
        flags.append("PROFANITY_DETECTED")

    if any(re.search(pattern, normalized) for pattern in PROMPT_INJECTION_PATTERNS):
        flags.append("PROMPT_INJECTION_BLOCKED")

    if any(re.search(pattern, message) for pattern in PII_PATTERNS):
        flags.append("PII_DETECTED")

    return flags


def filter_available_menu_item_ids(menu_items: Iterable[dict]) -> set[str]:
    available_ids: set[str] = set()
    for item in menu_items:
        item_id = str(item.get("id") or item.get("menu_item_id") or "").strip()
        if item_id and bool(item.get("is_available", True)):
            available_ids.add(item_id)
    return available_ids


def validate_suggested_item_ids(suggested_ids: Iterable[str], menu_items: Iterable[dict]) -> list[str]:
    available_ids = filter_available_menu_item_ids(menu_items)
    return [item_id for item_id in suggested_ids if item_id in available_ids]


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower().replace("đ", "d"))
    return "".join(char for char in normalized if not unicodedata.combining(char))
