from __future__ import annotations

import re
import unicodedata


MAX_MENU_CANDIDATES = 8


def select_menu_candidates(message: str, menu_items: list[dict], limit: int = MAX_MENU_CANDIDATES) -> list[dict]:
    """Return the only live-menu items an LLM may mention or action.

    Category and tag intent are deterministic constraints, not soft prompt
    hints. This protects grounded answers when the model is asked, for example,
    for ``Hải sản`` while other menu categories are present.
    """

    query = _normalize(message)
    available = [item for item in menu_items if bool(item.get("is_available", True))]
    if not available:
        return []

    category_matches = {
        _normalize(str(item.get("category_name") or ""))
        for item in available
        if _is_meaningful(item.get("category_name"))
        and _contains_phrase(query, _normalize(str(item.get("category_name") or "")))
    }
    tag_matches = {
        _normalize(str(tag))
        for item in available
        for tag in _tags(item)
        if _is_meaningful(tag) and _contains_phrase(query, _normalize(str(tag)))
    }

    if category_matches:
        constrained = [
            item
            for item in available
            if _normalize(str(item.get("category_name") or "")) in category_matches
        ]
    elif tag_matches:
        constrained = [
            item
            for item in available
            if any(_normalize(str(tag)) in tag_matches for tag in _tags(item))
        ]
    else:
        constrained = available

    return sorted(
        constrained,
        key=lambda item: (-_relevance(query, item), _normalize(str(item.get("name") or ""))),
    )[: max(1, limit)]


def _relevance(query: str, item: dict) -> int:
    document = _normalize(
        " ".join(
            [
                str(item.get("name") or ""),
                str(item.get("description") or ""),
                str(item.get("category_name") or ""),
                " ".join(str(tag) for tag in _tags(item)),
            ]
        )
    )
    return sum(1 for token in query.split() if len(token) > 1 and token in document)


def _tags(item: dict) -> list[object]:
    tags = item.get("tags") or []
    return [tags] if isinstance(tags, str) else list(tags)


def _is_meaningful(value: object) -> bool:
    return len(_normalize(str(value or ""))) >= 3


def _contains_phrase(query: str, phrase: str) -> bool:
    return bool(phrase) and f" {phrase} " in f" {query} "


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))
