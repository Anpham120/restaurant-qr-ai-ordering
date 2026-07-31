# -*- coding: utf-8 -*-
"""Ngôn ngữ chọn món cho tập đánh giá — khóa đáp án là truy vấn, không phải danh sách.

Tên tệp có tiền tố `menu_` là có chủ ý: `selectors` là tên một module chuẩn của
Python (asyncio và subprocess đều dùng). Đặt tên trùng rồi chèn thư mục này lên đầu
`sys.path` sẽ che module chuẩn — đã kiểm và đúng là nó che thật.

Vì sao thiết kế như vậy
-----------------------
Bản cũ viết khóa đáp án bằng tay. Kết quả: 96 khóa trỏ vào những đoạn văn bản dành cho
AI đọc chứ không dành cho khách, và không ai phát hiện trong nhiều tháng — vì không có
cách nào kiểm một danh sách viết tay là đúng.

Ở đây mỗi ca đánh giá không ghi "đáp án là các món m_008, m_012...". Nó ghi **điều kiện**
mà đáp án phải thỏa, ví dụ "mọi món mang nhãn `spice:none`". Bộ chạy tự tính danh sách từ
thực đơn. Ba lợi ích:

1. Không thể sai lệch âm thầm. Thực đơn đổi giá hay đổi nhãn thì khóa đáp án đổi theo.
2. Kiểm được chính ca đánh giá. Một điều kiện chọn ra 0 món là ca sai, và lộ ra ngay.
3. Đọc được. `{"tags_all": ["spice:none", "diet:vegetarian"]}` nói rõ ý định hơn một dãy
   mã món.

Điều kiện có thể lồng nhau, và mọi khóa trong một điều kiện phải cùng đúng (phép AND).
"""
from __future__ import annotations

from typing import Any, Callable

MenuItem = dict[str, Any]

# Mỗi khóa điều kiện -> hàm kiểm một món. Thêm khóa mới thì thêm ở đây, và
# `validate_selector` sẽ tự từ chối khóa lạ.
_PREDICATES: dict[str, Callable[[MenuItem, Any], bool]] = {
    # Nhãn
    "tags_all": lambda it, v: all(t in it["tags"] for t in v),
    "tags_any": lambda it, v: any(t in it["tags"] for t in v),
    "tags_none": lambda it, v: not any(t in it["tags"] for t in v),
    # Giá, đơn vị đồng
    "price_max": lambda it, v: it["price"] <= v,
    "price_min": lambda it, v: it["price"] >= v,
    # Danh mục
    "category_in": lambda it, v: it["categoryId"] in v,
    "category_not_in": lambda it, v: it["categoryId"] not in v,
    # Món cụ thể, dùng khi câu hỏi nêu tên món
    "id_in": lambda it, v: it["id"] in v,
    # Còn hàng. Hiện cả 91 món đều True nên khóa này chưa phân biệt được gì — giữ để
    # khi có dữ liệu món hết hàng thì ca đánh giá không phải viết lại.
    "available": lambda it, v: bool(it["isAvailable"]) is bool(v),
}


class SelectorError(ValueError):
    """Điều kiện chọn viết sai. Là lỗi của ca đánh giá, không phải của hệ thống AI."""


def clean_selector(selector: dict[str, Any]) -> dict[str, Any]:
    """Bỏ các khóa tài liệu (bắt đầu bằng `_`) khỏi một điều kiện chọn.

    Mục trong `named_selectors` mang thêm khóa `_why` giải thích tập đó là gì — bắt buộc, vì
    một điều kiện không giải thích được thì không ai xét lại được nó. Nhưng `validate_selector`
    từ chối khóa lạ, nên mọi nơi dùng phải lọc trước.

    Trước khi có hàm này, đoạn lọc đó **bị lặp ở ba chỗ** (`validate_cases.py`,
    `answer_metric.py`, và notebook báo cáo), và chỗ thứ ba đã quên lọc rồi ném
    `SelectorError: khóa điều kiện không có: '_why'`. Một cạnh sắc mà ba nơi phải tự nhớ thì
    sớm muộn có nơi quên — nên nó thành một hàm.

    Cố ý KHÔNG cho `validate_selector` tự bỏ qua khóa `_`: làm vậy thì `_tags_all` gõ sai sẽ
    bị bỏ qua im lặng thay vì báo lỗi.
    """
    return {k: v for k, v in selector.items() if not k.startswith("_")}


def validate_selector(selector: dict[str, Any]) -> None:
    if not isinstance(selector, dict) or not selector:
        raise SelectorError(f"điều kiện chọn phải là dict không rỗng: {selector!r}")
    for key, value in selector.items():
        if key not in _PREDICATES:
            raise SelectorError(
                f"khóa điều kiện không có: {key!r} "
                f"(có: {', '.join(sorted(_PREDICATES))})"
            )
        if key.startswith("tags") or key.endswith(("_in", "_not_in")):
            if not isinstance(value, list) or not value:
                raise SelectorError(f"{key} cần danh sách không rỗng, nhận {value!r}")
        elif key.startswith("price"):
            if not isinstance(value, int) or value < 0:
                raise SelectorError(f"{key} cần số nguyên không âm, nhận {value!r}")


def select(items: list[MenuItem], selector: dict[str, Any]) -> list[MenuItem]:
    """Chọn các món thỏa **mọi** điều kiện."""
    validate_selector(selector)
    return [
        item
        for item in items
        if all(_PREDICATES[key](item, value) for key, value in selector.items())
    ]


def select_ids(items: list[MenuItem], selector: dict[str, Any]) -> set[str]:
    return {item["id"] for item in select(items, selector)}


def known_tags(dictionary: dict) -> set[str]:
    return set(dictionary["tags"])


def selector_tags(selector: dict[str, Any]) -> set[str]:
    """Mọi nhãn nhắc tới trong một điều kiện — để kiểm chúng có thật trong từ điển."""
    out: set[str] = set()
    for key, value in selector.items():
        if key.startswith("tags"):
            out.update(value)
    return out
