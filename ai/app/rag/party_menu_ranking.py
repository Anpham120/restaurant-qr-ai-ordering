from __future__ import annotations

from typing import Any

from app.rag.vietnamese_normalizer import normalize_query_text

SHARED_NAME_TERMS = (
    "lau",
    "met ",
    " met",
    "thap cam",
    "hai san nguyen",
    "ca nguyen",
    "la hanh",
    "nuong nguyen",
    "goi lon",
)

SHARED_CATEGORY_TERMS = (
    "lau",
    "hot pot",
)

SHARED_TAG_TERMS = (
    "nau",
    "gia dinh",
    "an chung",
)

INDIVIDUAL_NAME_TERMS = (
    "pho ",
    " pho",
    "bun ",
    " bun",
    "com tam",
    "com suon",
    "mi xao",
)


def _normalize(value: str) -> str:
    return normalize_query_text(value)


def _item_tags(item: dict[str, Any]) -> str:
    tags = item.get("tags") or []
    if isinstance(tags, str):
        return _normalize(tags)
    return _normalize(" ".join(str(tag) for tag in tags))


def shared_dish_score(item: dict[str, Any]) -> int:
    name = _normalize(str(item.get("name") or ""))
    category = _normalize(str(item.get("category_name") or item.get("category_id") or ""))
    tags = _item_tags(item)
    score = 0
    if any(term in name for term in SHARED_NAME_TERMS):
        score += 4
    if any(term in category for term in SHARED_CATEGORY_TERMS):
        score += 5
    if "lau" in name:
        score += 3
    if any(term in tags for term in SHARED_TAG_TERMS):
        score += 2
    if any(term in name for term in INDIVIDUAL_NAME_TERMS):
        score -= 3
    return score


def is_shared_group_dish(item: dict[str, Any], *, min_score: int = 3) -> bool:
    return shared_dish_score(item) >= min_score


def rank_candidates_for_party(
    candidates: list[dict[str, Any]],
    party_size: int | None,
) -> list[dict[str, Any]]:
    if not party_size or party_size < 4:
        return list(candidates)

    return sorted(
        candidates,
        key=lambda item: (
            -shared_dish_score(item),
            str(item.get("name") or ""),
        ),
    )


def party_recommendation_intro(party_size: int | None) -> str | None:
    if not party_size:
        return None
    if party_size == 1:
        return "Bạn đi một mình thì mình gợi ý vài món phần cá nhân vừa ăn:"
    if party_size >= 6:
        return (
            f"Với nhóm {party_size} người, mình ưu tiên món ăn chung như lẩu/mẹt "
            "thay vì nhiều phần cá nhân."
        )
    if party_size >= 4:
        return (
            f"Với nhóm {party_size} người, mình ưu tiên món chia sẻ hoặc lẩu nhỏ "
            "thay vì chỉ gợi ý phần ăn cá nhân."
        )
    return f"Với {party_size} người, mình gợi ý vài món vừa khẩu phần:"
