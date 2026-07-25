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


_OPEN_MENU_BROWSE_TERMS = (
    "mon gi",
    "co gi an",
    "mon nao",
    "nhung mon",
    "nhung bia",
    "bia gi",
    "gi nhi",
    "an nhe",
    "mon nhe",
    "goi y",
    "de xuat",
    "tu van",
)


def _is_menu_presence_query(normalized: str) -> bool:
    padded = f" {normalized} "
    has_khong = " khong" in padded or normalized.endswith(" khong")
    if any(
        phrase in normalized
        for phrase in (
            "khong phai bia",
            "khong muon bia",
            "khong lay bia",
            "tranh bia",
        )
    ):
        return False
    if any(term in normalized for term in _OPEN_MENU_BROWSE_TERMS):
        return False
    if has_khong and _menu_keywords(normalized):
        return True
    if any(term in normalized for term in _MENU_PRESENCE_TERMS):
        return has_khong and bool(_menu_keywords(normalized))
    if "o day co" in normalized and has_khong:
        return bool(_menu_keywords(normalized))
    return False


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
        "nhau",
    ):
        if keyword in tokens:
            keywords.append(keyword)
    # Avoid matching "bo" inside "bo qua" (skip/avoid), not beef dishes.
    if "bo" in tokens and "qua" not in tokens:
        keywords.append("bo")
    return keywords


def is_menu_presence_query(message: str) -> bool:
    """True when user asks whether a dish/category exists on the live menu."""

    return _is_menu_presence_query(_normalize(message))


def try_menu_presence_fast_path(
    message: str,
    menu_items: list[dict[str, Any]],
    *,
    wants_recommendations: bool,
) -> dict[str, Any] | None:
    """Answer 'có món X không?' from live menu without LLM."""

    normalized = _normalize(message)
    if not menu_items:
        return None
    if not is_menu_presence_query(message):
        return None

    if any(term in normalized for term in _ALLERGY_OR_AVOID_TERMS):
        return None

    keywords = _menu_keywords(normalized)
    if not keywords:
        return None

    matched = [
        item
        for item in menu_items
        if bool(item.get("is_available", True))
        and any(
            keyword
            in _normalize(
                " ".join(
                    [
                        str(item.get("name") or ""),
                        str(item.get("category_name") or item.get("category") or ""),
                        " ".join(str(tag) for tag in (item.get("tags") or [])),
                    ]
                )
            )
            for keyword in keywords
        )
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
    cited_items = matched[:8]
    evidence = [
        {
            "source": "live_menu",
            "menu_item_id": str(item.get("id") or item.get("menu_item_id")),
            "title": str(item.get("name") or "Món"),
            "score": 1.0,
        }
        for item in cited_items
        if item.get("id") or item.get("menu_item_id")
    ]
    claims = []
    for item in cited_items:
        item_id = str(item.get("id") or item.get("menu_item_id") or "").strip()
        if not item_id:
            continue
        name = str(item.get("name") or "Món").strip()
        price = item.get("price_vnd") or item.get("price")
        claim_text = f"{name} có trong thực đơn hiện tại và đang còn phục vụ"
        if isinstance(price, (int, float)):
            claim_text += f", giá {int(price):,} đồng".replace(",", ".")
        claims.append(
            {
                "text": claim_text + ".",
                "evidence_ids": [item_id],
                "verified": True,
                "reason": None,
            }
        )
    return {
        "content": content,
        "provider_available": False,
        "model": "deterministic-menu-presence",
        "retrieved_sources": [],
        "evidence": evidence,
        "claims": claims,
        "guardrail_flags": [],
        "suggested_cart_actions": [],
        "follow_up": {"can_show_more": len(matched) > 8, "remaining_count": max(len(matched) - 8, 0)},
        "suggest_staff_handoff": "tre em" in normalized or "tre con" in normalized,
    }
