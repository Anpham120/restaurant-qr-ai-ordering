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
]


def detect_guardrail_flags(message: str) -> list[str]:
    normalized = _normalize(message)
    flags: list[str] = []
    if any(re.search(pattern, normalized) for pattern in ORDER_CREATION_PATTERNS):
        flags.append("CUSTOMER_CONFIRMATION_REQUIRED")
    if "gia" in normalized and ("tu tao" in normalized or "bia" in normalized):
        flags.append("PRICE_FABRICATION_BLOCKED")
    if "mon moi" in normalized or "ngoai thuc don" in normalized:
        flags.append("MENU_FABRICATION_BLOCKED")
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
