from __future__ import annotations

import re
from typing import Any

from app.rag.vietnamese_normalizer import normalize_query_text


EXCLUDED_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "cat_alcohol": ("bia ruou", "bia", "ruou", "cocktail", "co con", "alcohol", "beer", "wine"),
}

NEGATION_WINDOW = 20

DRINK_NON_ALCOHOL_INTROS = (
    "Dạ, em gợi ý vài đồ uống không cồn từ thực đơn hiện tại:",
    "Em chọn giúp bạn vài đồ uống không cồn đang có sẵn:",
    "Theo thực đơn hiện tại, đây là vài đồ uống không cồn phù hợp:",
)
DRINK_INTROS = (
    "Dạ, em gợi ý vài đồ uống phù hợp từ thực đơn:",
    "Em chọn giúp bạn vài đồ uống đang có sẵn:",
    "Theo thực đơn hiện tại, đây là vài đồ uống bạn có thể thử:",
)
DESSERT_INTROS = (
    "Dạ, em gợi ý vài món tráng miệng từ thực đơn:",
    "Em chọn giúp bạn vài món ngọt nhẹ để kết thúc bữa:",
    "Theo thực đơn hiện tại, đây là vài món tráng miệng phù hợp:",
)
FOOD_INTROS = (
    "Dạ, em gợi ý vài món ăn phù hợp từ thực đơn:",
    "Em chọn giúp bạn vài món ăn đang có sẵn:",
    "Theo thực đơn hiện tại, đây là vài món ăn bạn có thể thử:",
)
GENERAL_INTROS = (
    "Dựa trên thực đơn hiện tại, em gợi ý các món sau:",
    "Em chọn giúp bạn vài món phù hợp từ thực đơn:",
    "Theo thực đơn hiện tại, bạn có thể tham khảo các món sau:",
)

def detect_excluded_category_ids(message: str, history: list[dict[str, Any]] | None = None) -> frozenset[str]:
    history = history or []
    combined = " ".join(
        [_normalize(str(turn.get("content") or "")) for turn in history[-6:] if turn.get("content")]
        + [_normalize(message)]
    )
    excluded: set[str] = set()

    for category_id, aliases in EXCLUDED_CATEGORY_ALIASES.items():
        for alias in aliases:
            if alias in combined and _is_negated(combined, alias):
                excluded.add(category_id)

    if re.search(r"(khong|chu)\s+(phai|muon|lay)\s+(bia|ruou)", combined):
        excluded.add("cat_alcohol")
    if "khong co con" in combined or "non alcoholic" in combined:
        excluded.add("cat_alcohol")
    if "do uong" in combined and ("khong phai bia" in combined or "tranh bia" in combined):
        excluded.add("cat_alcohol")

    return frozenset(excluded)


def filter_items_by_excluded_categories(
    items: list[dict],
    excluded_category_ids: frozenset[str],
) -> list[dict]:
    if not excluded_category_ids:
        return list(items)

    return [
        item
        for item in items
        if str(item.get("category_id") or "").strip() not in excluded_category_ids
    ]


def build_suggestion_reason(item: dict, *, seed: str = "") -> str:
    name = str(item.get("name") or "Món").strip()
    category = _normalize(str(item.get("category_name") or ""))
    tags = {_normalize(str(tag)) for tag in (item.get("tags") or [])}

    if "cat_alcohol" == str(item.get("category_id") or ""):
        return _pick_variant(
            (
                f"{name} hợp để nhâm nhi cùng món ăn.",
                f"{name} dễ uống khi ăn cùng bạn bè.",
                f"{name} đang có sẵn nếu bạn muốn thêm đồ uống có cồn.",
            ),
            seed or name,
        )
    if any(token in category for token in ("ca phe", "tra")):
        return _pick_variant(
            (
                f"{name} nhẹ nhàng, dễ uống trước hoặc sau bữa.",
                f"{name} thơm dịu, hợp khi muốn uống nhẹ.",
                f"{name} đang có sẵn trong nhóm cà phê & trà.",
            ),
            seed or name,
        )
    if any(token in category for token in ("nuoc ep", "sinh to")):
        return _pick_variant(
            (
                f"{name} tươi mát, hợp làm đồ uống giải khát.",
                f"{name} ngọt tự nhiên, dễ uống cả nhà.",
                f"{name} mát lạnh, hợp ngày nóng.",
            ),
            seed or name,
        )
    if "mat" in tags or "thanh" in tags:
        return _pick_variant(
            (
                f"{name} thanh mát, dễ uống.",
                f"{name} nhẹ, dễ thử nếu bạn muốn đồ thanh.",
                f"{name} mát, hợp giải khát.",
            ),
            seed or name,
        )
    if "trang mieng" in category or "che" in tags:
        return _pick_variant(
            (
                f"{name} ngọt nhẹ, hợp kết thúc bữa ăn.",
                f"{name} dễ ăn sau bữa chính.",
                f"{name} mát, hợp làm tráng miệng.",
            ),
            seed or name,
        )
    if "khai vi" in category:
        return _pick_variant(
            (
                f"{name} nhẹ, dễ ăn đầu bữa.",
                f"{name} dễ thử trước món chính.",
                f"{name} hợp mở đầu bữa ăn.",
            ),
            seed or name,
        )
    return _pick_variant(
        (
            f"{name} đang có sẵn trong thực đơn.",
            f"{name} phù hợp với yêu cầu hiện tại.",
            f"{name} là lựa chọn an toàn từ menu hiện có.",
        ),
        seed or name,
    )


def recommendation_intro(
    *,
    requested_item_kind: str | None = None,
    excluded_category_ids: frozenset[str] | None = None,
    seed: str = "",
) -> str:
    excluded = excluded_category_ids or frozenset()
    if requested_item_kind == "drink" and "cat_alcohol" in excluded:
        return _pick_variant(DRINK_NON_ALCOHOL_INTROS, seed or "drink-non-alcohol")
    if requested_item_kind == "drink":
        return _pick_variant(DRINK_INTROS, seed or "drink")
    if requested_item_kind == "dessert":
        return _pick_variant(DESSERT_INTROS, seed or "dessert")
    if requested_item_kind == "food":
        return _pick_variant(FOOD_INTROS, seed or "food")
    return _pick_variant(GENERAL_INTROS, seed or "general")

def _is_negated(text: str, term: str) -> bool:
    index = text.find(term)
    while index != -1:
        window = text[max(0, index - NEGATION_WINDOW) : index]
        if any(
            marker in window
            for marker in (
                "khong ",
                "bo ",
                "tranh ",
                "no ",
                "without ",
                "not ",
                "chu khong ",
                "khong muon ",
                "khong lay ",
            )
        ):
            return True
        index = text.find(term, index + 1)
    return False


def _normalize(value: str) -> str:
    return normalize_query_text(value)


def _pick_variant(variants: tuple[str, ...], seed: str) -> str:
    if not variants:
        return ""
    score = sum(ord(char) for char in seed)
    return variants[score % len(variants)]