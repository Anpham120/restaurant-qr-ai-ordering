from __future__ import annotations

import re
import unicodedata


TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").lower().replace("đ", "d"))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(TOKEN_PATTERN.findall(ascii_text))


def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)
    return normalized.split() if normalized else []

