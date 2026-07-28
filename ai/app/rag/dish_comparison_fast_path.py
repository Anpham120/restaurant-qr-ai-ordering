"""Deterministic side-by-side comparison of dishes the guest named.

Why this path exists
--------------------
Comparison questions ("phở bò với phở gà khác gì nhau?", "so sánh gỏi cuốn và
nem rán") were previously handled by the generation step, which measured poorly:
it described taste in vague terms without citing any figure, attached no cart
card, and in some cases dropped one of the two dishes entirely and answered with
unrelated recommendations instead.

A comparison is a table lookup, not a reasoning task: price, category, spice tag,
allergen tag and availability all live in the live menu. Building that table in
code gives figures that are correct by construction and a card for every dish the
guest asked about.

Boundaries
----------
* Fires only when the guest names **at least two** dishes that exist in the live
  menu *and* the phrasing signals comparison. One dish, or none, is left to the
  other paths — a vague "món nào ngon hơn?" with no dish named is genuinely
  ambiguous and must be asked back, not guessed.
* Never ranks dishes by "better". It reports the differences and lets the guest
  decide, per ``knowledge-base/dish-comparison.md``.
"""
from __future__ import annotations

from typing import Any, Sequence

from app.rag.menu_item_kind import classify_menu_item_kind
from app.rag.vietnamese_normalizer import normalize_query_text

# Cách khách nêu ý muốn đối chiếu. "hay"/"với" chỉ tính khi đã tìm được ≥2 món,
# vì hai từ này quá phổ biến để dùng làm tín hiệu độc lập.
_COMPARISON_MARKERS: tuple[str, ...] = (
    "so sanh",
    "khac gi",
    "khac nhau",
    "so voi",
    "nen chon",
    "chon cai nao",
    "chon mon nao",
    "compare",
    "difference",
    "versus",
    " vs ",
)

# Các từ nối yếu: chỉ đủ tin cậy khi đứng giữa hai tên món đã khớp thực đơn.
_WEAK_CONNECTORS: tuple[str, ...] = (" hay ", " voi ", " and ", " or ")

MAX_DISHES = 4  # dish-comparison.md giới hạn 4 món/lượt để câu trả lời còn đọc được

# Nhãn độ cay và dị nguyên dùng để dựng cột đối chiếu.
_SPICE_TAGS: dict[str, str] = {
    "khong cay": "không cay",
    "cay nhe": "cay nhẹ",
    "cay vua": "cay vừa",
    "cay": "có cay",
    "rat cay": "rất cay",
}


def _normalise(text: str) -> str:
    return normalize_query_text(text)


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("menu_item_id") or "").strip()


def _item_tags(item: dict[str, Any]) -> list[str]:
    tags = item.get("tags") or []
    if isinstance(tags, str):
        return [_normalise(tags)]
    return [_normalise(str(tag)) for tag in tags]


def has_comparison_intent(message: str, matched_count: int) -> bool:
    """True khi khách muốn đối chiếu, chứ không phải chỉ nhắc tên nhiều món."""
    normalised = f" {_normalise(message)} "
    if any(marker in normalised for marker in _COMPARISON_MARKERS):
        return True
    # Từ nối yếu chỉ được tin khi đã có từ hai món khớp thực đơn trở lên.
    return matched_count >= 2 and any(c in normalised for c in _WEAK_CONNECTORS)


# Từ nối dùng để tách câu hỏi thành từng cụm, mỗi cụm ứng với một món.
_SPLIT_TOKENS: tuple[str, ...] = (
    " so voi ", " voi ", " hay ", " va ", " vs ", " and ", " or ", ",",
)

# Từ chức năng trong câu hỏi so sánh, không phải phần tên món.
_QUERY_NOISE = frozenset(
    {
        "so", "sanh", "khac", "gi", "nhau", "nen", "chon", "mon", "nao", "hon",
        "cai", "the", "compare", "difference", "please", "giup", "minh", "toi",
        "cho", "xem", "thi", "sao", "voi", "hay", "va", "ngon", "ban", "a",
    }
)


def _name_tokens(text: str) -> list[str]:
    return [t for t in _normalise(text).split() if t]


def find_named_dishes(
    message: str,
    menu_items: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Các món khách nêu tên, khớp theo cả hai chiều.

    Khách thường gõ tên ngắn hơn tên trên thực đơn ("phở bò" cho "Phở bò tái
    nạm"), nên chỉ kiểm tra chuỗi con một chiều là bỏ sót. Câu hỏi được tách theo
    từ nối rồi mỗi cụm ghép với món có tên chứa **toàn bộ** từ đặc trưng của cụm
    đó; yêu cầu ít nhất hai từ để "phở" không khớp bừa mọi món phở.
    """
    normalised = f" {_normalise(message)} "

    # Tách câu hỏi thành các cụm ứng viên.
    cum = [normalised]
    for sep in _SPLIT_TOKENS:
        moi: list[str] = []
        for phan in cum:
            moi.extend(phan.split(sep))
        cum = moi

    ket_qua: list[dict[str, Any]] = []
    da_chon: set[str] = set()
    for phan in cum:
        tu_dac_trung = [t for t in _name_tokens(phan) if t not in _QUERY_NOISE]
        if len(tu_dac_trung) < 2:
            continue
        khop: list[tuple[int, dict[str, Any]]] = []
        for item in menu_items:
            if not bool(item.get("is_available", True)) or not _item_id(item):
                continue
            ten_tu = set(_name_tokens(str(item.get("name") or "")))
            if not ten_tu:
                continue
            # Cụm phải nằm trọn trong tên món, hoặc tên món nằm trọn trong cụm.
            trong_ten = all(t in ten_tu for t in tu_dac_trung)
            trong_cum = ten_tu <= set(tu_dac_trung)
            if trong_ten or trong_cum:
                # Ưu tiên món có tên ngắn nhất còn thoả — sát ý khách nhất.
                khop.append((len(ten_tu), item))
        if not khop:
            continue
        khop.sort(key=lambda pair: pair[0])
        chon = khop[0][1]
        if _item_id(chon) not in da_chon:
            da_chon.add(_item_id(chon))
            ket_qua.append(chon)
    return ket_qua


def _spice_label(item: dict[str, Any]) -> str:
    tags = _item_tags(item)
    for tag, nhan in _SPICE_TAGS.items():
        if tag in tags:
            return nhan
    return "chưa ghi nhận"


def _allergen_label(item: dict[str, Any]) -> str:
    dinh = [tag for tag in _item_tags(item) if tag.startswith("co ")]
    if not dinh:
        return "không ghi nhận"
    return ", ".join(tag[3:] for tag in dinh)


def _format_price(item: dict[str, Any]) -> str:
    gia = item.get("price_vnd") or item.get("price")
    if not isinstance(gia, (int, float)):
        return "chưa có giá"
    return f"{int(gia):,}".replace(",", ".") + "đ"


def build_comparison_content(dishes: Sequence[dict[str, Any]]) -> str:
    """Bảng đối chiếu dạng văn bản, mọi số liệu lấy trực tiếp từ thực đơn."""
    ten_cac_mon = " và ".join(str(d.get("name")) for d in dishes)
    dong: list[str] = [f"So sánh {ten_cac_mon} theo dữ liệu thực đơn hiện tại:"]
    for dish in dishes:
        dong.append(
            f"- {dish.get('name')}: {_format_price(dish)}"
            f" · nhóm {dish.get('category_name') or 'chưa rõ'}"
            f" · {_spice_label(dish)}"
            f" · thành phần cần lưu ý: {_allergen_label(dish)}"
        )

    # Chênh lệch giá là khác biệt khách quan dễ dùng nhất; chỉ nêu khi đủ dữ liệu.
    gia = [
        (d, d.get("price_vnd") or d.get("price"))
        for d in dishes
        if isinstance(d.get("price_vnd") or d.get("price"), (int, float))
    ]
    if len(gia) >= 2:
        re_nhat = min(gia, key=lambda pair: pair[1])
        dat_nhat = max(gia, key=lambda pair: pair[1])
        if re_nhat[1] != dat_nhat[1]:
            chenh = int(dat_nhat[1] - re_nhat[1])
            dong.append(
                f"Về giá: {re_nhat[0].get('name')} thấp hơn {dat_nhat[0].get('name')} "
                f"{chenh:,}".replace(",", ".") + "đ."
            )

    dong.append(
        "Mình nêu khác biệt để bạn tự chọn theo khẩu vị; cả hai món đều đang phục vụ."
    )
    return "\n".join(dong)


def try_dish_comparison_fast_path(
    message: str,
    menu_items: Sequence[dict[str, Any]],
    *,
    excluded_ids: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any] | None:
    """Trả về phản hồi so sánh tất định, hoặc None để nhường cho đường khác."""
    dishes = [
        dish
        for dish in find_named_dishes(message, menu_items)
        if _item_id(dish) not in excluded_ids
    ]
    if len(dishes) < 2:
        return None
    if not has_comparison_intent(message, len(dishes)):
        return None

    # Chỉ so sánh trong cùng một loại: đối chiếu bia với phở không có ý nghĩa.
    loai = {str(classify_menu_item_kind(dish)) for dish in dishes}
    if len(loai) > 1:
        return None

    dishes = dishes[:MAX_DISHES]
    content = build_comparison_content(dishes)

    return {
        "content": content,
        "provider_available": False,
        "model": "deterministic-dish-comparison",
        "retrieved_sources": [],
        "evidence": [
            {
                "source": "live_menu",
                "menu_item_id": _item_id(dish),
                "title": str(dish.get("name") or ""),
                "score": 1.0,
            }
            for dish in dishes
        ],
        "claims": [
            {
                "text": f"{dish.get('name')} có giá {_format_price(dish)} "
                        f"thuộc nhóm {dish.get('category_name') or 'chưa rõ'}.",
                "evidence_ids": [_item_id(dish)],
                "verified": True,
                "reason": None,
            }
            for dish in dishes
        ],
        "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
        # Thẻ cho MỌI món được so sánh — khách phải chọn được cả hai.
        "suggested_cart_actions": [
            {
                "menu_item_id": _item_id(dish),
                "name": str(dish.get("name") or ""),
                "price_vnd": dish.get("price_vnd") or dish.get("price"),
                "quantity": 1,
                "reason": "Món trong so sánh",
                "requires_customer_confirmation": True,
            }
            for dish in dishes
        ],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": False,
    }
