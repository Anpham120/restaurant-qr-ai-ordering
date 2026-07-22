from __future__ import annotations

from typing import Any

from app.rag.vietnamese_normalizer import normalize_query_text


_MENU_PRESENCE_TERMS = ("co mon", "mon nao", "co gi an", "co nhung mon", "ban co mon")

_ALLERGY_OR_AVOID_TERMS = (
    "di ung",
    "allerg",
    "bo qua",
    "tranh",
    "khong an",
    "avoid",
    "nen bo qua",
)


def _normalize(text: str) -> str:
    return normalize_query_text(text)


def _menu_keywords(normalized_query: str) -> list[str]:
    tokens = set(normalized_query.split())
    keywords: list[str] = []
    for keyword in (
        "goi",
        "pho",
        "bun",
        "com",
        "lau",
        "chay",
        "banh",
        "che",
        "ga",
        "tom",
        "cua",
        "muc",
        "dessert",
        "tra",
        "bia",
    ):
        if keyword in tokens:
            keywords.append(keyword)
    # Avoid matching "bo" inside "bo qua" (skip/avoid), not beef dishes.
    if "bo" in tokens and "qua" not in tokens:
        keywords.append("bo")
    return keywords


def try_menu_presence_fast_path(
    message: str,
    menu_items: list[dict[str, Any]],
    *,
    wants_recommendations: bool,
) -> dict[str, Any] | None:
    """Answer 'có món X không?' from live menu without LLM."""

    if wants_recommendations or not menu_items:
        return None

    normalized = _normalize(message)
    if any(term in normalized for term in _ALLERGY_OR_AVOID_TERMS):
        return None
    if not any(term in normalized for term in _MENU_PRESENCE_TERMS):
        return None

    keywords = _menu_keywords(normalized)
    if not keywords:
        return None

    matched = [
        item
        for item in menu_items
        if bool(item.get("is_available", True))
        and any(keyword in _normalize(str(item.get("name") or "")) for keyword in keywords)
    ]
    if not matched:
        return None

    lines = []
    for item in matched[:8]:
        name = str(item.get("name") or "Món").strip()
        price = item.get("price_vnd") or item.get("price")
        if isinstance(price, (int, float)):
            lines.append(f"- {name} ({int(price):,}đ)".replace(",", "."))
        else:
            lines.append(f"- {name}")

    kid_note = ""
    if any(token in normalized for token in ("tre em", "tre con", "be an")):
        kid_note = " Với trẻ em, nên chọn món ít cay và xác nhận dị ứng với nhân viên nếu cần."

    content = (
        "Theo thực đơn hiện tại, nhà hàng có các món liên quan:\n"
        + "\n".join(lines)
        + kid_note
    )
    return {
        "content": content,
        "provider_available": False,
        "model": "deterministic-menu-presence",
        "retrieved_sources": [],
        "guardrail_flags": [],
        "suggested_cart_actions": [],
        "follow_up": {"can_show_more": len(matched) > 8, "remaining_count": max(len(matched) - 8, 0)},
        "suggest_staff_handoff": "tre em" in normalized or "tre con" in normalized,
    }
