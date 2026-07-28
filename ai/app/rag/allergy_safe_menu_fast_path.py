"""Deterministic answers for "I'm allergic to X — what can I eat?".

Why this path exists
--------------------
Allergy was the only question family in the evaluation set answered 0% by a
deterministic path: every case went to the generation step.  That combination —
safety-critical, model-dependent, no deterministic floor — was the highest risk in
the system, and it showed.  Asked "Tôi dị ứng hải sản, món nào an toàn?", the
assistant replied "Bạn vui lòng gửi mình ảnh thực đơn" — it asked the guest to
supply the menu it was already holding.

Which dishes contain an allergen is a lookup, not a judgement.  The catalogue
carries curated `co <allergen>` labels and free-text descriptions, and
``infer_allergen_excluded_menu_item_ids`` reads both.  Doing the lookup in code
gives an answer that is the same every time and cannot invent a dish.

What this path will not do
--------------------------
``knowledge-base/allergy-disclaimer.md`` forbids three claims outright: that a dish
is "an toàn 100%", that it "chắc chắn không có" an allergen, and that the kitchen
separates preparation entirely.  Nothing here asserts safety.  It reports what the
catalogue records — "không ghi nhận <allergen>" — carries the mandatory disclaimer
verbatim, and always offers staff confirmation, because a menu description is not
a kitchen audit.
"""
from __future__ import annotations

from typing import Any, Sequence

from app.rag.menu_query_filters import infer_allergen_excluded_menu_item_ids
from app.rag.vietnamese_normalizer import normalize_query_text

# Câu bắt buộc, lấy nguyên văn từ knowledge-base/allergy-disclaimer.md.
DISCLAIMER_VI = (
    "Thông tin dị ứng chỉ mang tính tham khảo từ mô tả menu. Nếu bạn dị ứng "
    "nghiêm trọng, vui lòng báo nhân viên để xác nhận trực tiếp với bếp trước khi đặt."
)
DISCLAIMER_EN = (
    "Allergy information is based on menu descriptions only. For severe allergies, "
    "please ask staff to confirm with the kitchen before ordering."
)

# Đủ để khách chọn, không dài tới mức phải cuộn.
MAX_DISHES_LISTED = 6

# Tên tiếng Việt của dị nguyên, để câu trả lời không in ra nhãn tiếng Anh.
ALLERGEN_LABELS_VI: dict[str, str] = {
    "seafood": "hải sản",
    "peanut": "đậu phộng",
    "gluten": "gluten",
    "egg": "trứng",
    "dairy": "sữa",
    "soy": "đậu nành",
}

ALLERGEN_LABELS_EN: dict[str, str] = {
    "seafood": "seafood",
    "peanut": "peanuts",
    "gluten": "gluten",
    "egg": "egg",
    "dairy": "dairy",
    "soy": "soy",
}

# Khách hỏi theo hai chiều: "món nào ăn được" và "món nào phải tránh".
_AVOID_MARKERS: tuple[str, ...] = (
    "tranh",
    "bo qua",
    "khong goi",
    "khong an duoc",
    "chua",
    "co khong",
    "avoid",
    "which contain",
)
_SAFE_MARKERS: tuple[str, ...] = (
    "an toan",
    "an duoc",
    "phu hop",
    "goi y",
    "mon khac",
    "khong co",
    "safe",
    "recommend",
)


def _normalise(text: str) -> str:
    return normalize_query_text(text)


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("menu_item_id") or "").strip()


def _format_price(item: dict[str, Any]) -> str:
    price = item.get("price_vnd") or item.get("price")
    if not isinstance(price, (int, float)):
        return "chưa có giá"
    return f"{int(price):,}".replace(",", ".") + "đ"


def _is_english(message: str) -> bool:
    lowered = message.casefold()
    return any(word in lowered for word in ("allergic", "allergy", "avoid", "safe"))


def wants_avoid_list(message: str) -> bool:
    """True khi khách hỏi *món nào phải tránh* thay vì *món nào ăn được*.

    Khi câu chứa cả hai loại dấu hiệu thì trả về danh sách ăn được, vì đó là thứ
    dùng được ngay — khách còn đặt món, không chỉ để biết.
    """
    normalised = f" {_normalise(message)} "
    if any(marker in normalised for marker in _SAFE_MARKERS):
        return False
    return any(marker in normalised for marker in _AVOID_MARKERS)


def build_safe_list_content(
    allergen_names: Sequence[str],
    safe: Sequence[dict[str, Any]],
    excluded_count: int,
    *,
    english: bool,
) -> str:
    names = ", ".join(allergen_names)
    lines: list[str] = []
    if english:
        lines.append(
            f"These dishes record no {names} in the current menu "
            f"({excluded_count} dishes were set aside):"
        )
    else:
        lines.append(
            f"Các món dưới đây không ghi nhận {names} theo thực đơn hiện tại "
            f"(đã bỏ qua {excluded_count} món):"
        )
    for item in safe[:MAX_DISHES_LISTED]:
        lines.append(
            f"- {item.get('name')} ({_format_price(item)})"
            f" · nhóm {item.get('category_name') or 'chưa rõ'}"
        )
    remaining = max(0, len(safe) - MAX_DISHES_LISTED)
    if remaining:
        lines.append(
            f"Còn {remaining} món khác cũng không ghi nhận {names}."
            if not english
            else f"{remaining} more dishes also record no {names}."
        )
    lines.append(DISCLAIMER_EN if english else DISCLAIMER_VI)
    return "\n".join(lines)


def build_avoid_list_content(
    allergen_names: Sequence[str],
    avoid: Sequence[dict[str, Any]],
    *,
    english: bool,
) -> str:
    names = ", ".join(allergen_names)
    lines: list[str] = []
    if english:
        lines.append(f"These dishes record {names}, so they are the ones to skip:")
    else:
        lines.append(f"Các món sau có ghi nhận {names}, bạn nên bỏ qua:")
    for item in avoid[:MAX_DISHES_LISTED]:
        lines.append(f"- {item.get('name')} ({_format_price(item)})")
    remaining = max(0, len(avoid) - MAX_DISHES_LISTED)
    if remaining:
        lines.append(
            f"Còn {remaining} món khác cũng có ghi nhận {names}."
            if not english
            else f"{remaining} more dishes also record {names}."
        )
    lines.append(DISCLAIMER_EN if english else DISCLAIMER_VI)
    return "\n".join(lines)


def try_allergy_safe_menu_fast_path(
    message: str,
    menu_items: Sequence[dict[str, Any]],
    *,
    allergens: Sequence[str],
    excluded_ids: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any] | None:
    """Trả về danh sách món theo dị nguyên đã khai, hoặc None để nhường đường khác."""
    if not allergens:
        return None

    available = [
        item
        for item in menu_items
        if bool(item.get("is_available", True)) and _item_id(item)
    ]
    if not available:
        return None

    allergen_excluded = infer_allergen_excluded_menu_item_ids(allergens, available)
    avoid = [item for item in available if _item_id(item) in allergen_excluded]
    safe = [
        item
        for item in available
        if _item_id(item) not in allergen_excluded
        and _item_id(item) not in excluded_ids
    ]
    if not safe and not avoid:
        return None

    english = _is_english(message)
    labels = ALLERGEN_LABELS_EN if english else ALLERGEN_LABELS_VI
    names = [labels.get(str(a), str(a)) for a in allergens]

    if wants_avoid_list(message) and avoid:
        listed = avoid[:MAX_DISHES_LISTED]
        content = build_avoid_list_content(names, avoid, english=english)
        # Không gắn thẻ thêm giỏ cho món cần tránh — đó là mời khách đặt đúng thứ
        # họ vừa nói là không ăn được.
        cart_actions: list[dict[str, Any]] = []
        claim_verb = "có ghi nhận"
    else:
        if not safe:
            return None
        listed = safe[:MAX_DISHES_LISTED]
        content = build_safe_list_content(names, safe, len(avoid), english=english)
        cart_actions = [
            {
                "menu_item_id": _item_id(item),
                "name": str(item.get("name") or ""),
                "price_vnd": item.get("price_vnd") or item.get("price"),
                "quantity": 1,
                "reason": f"Không ghi nhận {', '.join(names)}",
                "requires_customer_confirmation": True,
            }
            for item in listed
        ]
        claim_verb = "không ghi nhận"

    return {
        "content": content,
        "provider_available": False,
        "model": "deterministic-allergy-menu",
        "retrieved_sources": [],
        "evidence": [
            {
                "source": "live_menu",
                "menu_item_id": _item_id(item),
                "title": str(item.get("name") or ""),
                "score": 1.0,
            }
            for item in listed
        ],
        "claims": [
            {
                "text": (
                    f"{item.get('name')} {claim_verb} "
                    f"{', '.join(names)} theo mô tả thực đơn."
                ),
                "evidence_ids": [_item_id(item)],
                "verified": True,
                "reason": None,
            }
            for item in listed
        ],
        "guardrail_flags": [
            "ALLERGY_DISCLAIMER",
            "ALLERGEN_CAUTION",
            "CUSTOMER_CONFIRMATION_REQUIRED",
        ],
        "suggested_cart_actions": cart_actions,
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        # Mô tả menu không phải kết quả kiểm tra bếp: luôn mở đường hỏi nhân viên.
        "suggest_staff_handoff": True,
    }
