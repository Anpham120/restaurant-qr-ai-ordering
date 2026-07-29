# -*- coding: utf-8 -*-
"""Trả lời khách chỉ bằng cách tra thực đơn — không dùng mô hình sinh nào.

Vì sao bước này đứng trước mô hình
----------------------------------
Bản cũ có 8 đường xử lý tất định chồng lên nhau, và chỉ 33% câu trả lời do mã sinh ra —
phần còn lại phụ thuộc mô hình. Không ai nói được đường nào phụ trách việc gì, và hai
đường bị một cờ legacy tắt mà hệ thống vẫn hoạt động đúng.

Ở đây làm ngược lại: dựng phần tra bảng **trước**, đo xem nó trả lời được bao nhiêu, rồi
mới biết mô hình còn phải làm gì. Con số đó là số nền, và nó có hai tính chất mà câu trả
lời của mô hình không có: **đúng 100% về dữ liệu** và **giống nhau mọi lần chạy**.

Sáu nhánh, mỗi nhánh một việc
-----------------------------
Không có nhánh nào chồng nhánh nào, và thứ tự là thứ tự loại trừ:

1. ngoài bài toán      -> từ chối ngắn gọn
2. câu chính sách      -> nói thẳng chưa có dữ liệu
3. hỏi giá một món     -> nêu giá
4. so sánh hai món     -> nêu dữ kiện cả hai
5. món đắt/rẻ nhất     -> tính rồi nêu
6. còn lại             -> lọc thực đơn theo ràng buộc

Nhánh 6 sinh ra câu hỏi lại khi khách chưa nói gì đủ để lọc. Hỏi lại là câu trả lời đúng
ở đó, không phải thất bại.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import json
from pathlib import Path

from understand import DRINK_CATEGORIES, FOOD_CATEGORIES, Request

FACTS_PATH = Path(__file__).resolve().parents[2] / "backend" / "data" / "restaurant-facts.json"


def load_facts() -> dict[str, str]:
    """Sự thật về nhà hàng, theo chủ đề. Chỉ nhận mục đã được điền.

    Đây là toàn bộ "kho tri thức" của hệ thống, và nó nhỏ có chủ ý. Bản cũ dựng 26 tài
    liệu, 213 đoạn, so sánh 7 phương pháp truy hồi có embedding (~3GB RAM) — cho đúng 6
    chủ đề mà phần nhận diện câu hỏi đã xử lý chính xác 100%. Máy móc hạng nặng cho một
    bài toán nhỏ, và nó còn gây một lỗi thật: 47/221 đoạn là hướng dẫn dành cho AI đọc
    nhưng lại được trích cho khách.

    Ở đây truy hồi là **tra khóa**: chủ đề đã nhận ra ở bước hiểu câu hỏi chính là khóa.
    Không có xếp hạng, không có ngưỡng tương đồng, nên không có chỗ nào để chệch.

    Mục để trống bị BỎ QUA, không phải trả về chuỗi rỗng. Nhờ vậy một tệp chưa điền gì
    hành xử đúng như khi chưa có tệp: hệ thống nói chưa có dữ liệu và chuyển nhân viên.
    Điền được bao nhiêu thì dùng bấy nhiêu.
    """
    if not FACTS_PATH.exists():
        return {}
    try:
        data = json.loads(FACTS_PATH.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError):
        # Tệp hỏng thì coi như chưa có — không được làm sập luồng trả lời khách.
        return {}
    out: dict[str, str] = {}
    for topic, entry in (data.get("topics") or {}).items():
        if not isinstance(entry, dict):
            continue
        answer = entry.get("answer_vi")
        if isinstance(answer, str) and answer.strip():
            out[topic] = answer.strip()
    return out

# Số món nêu ra trong một câu liệt kê. Thước đo chặn ở 12 món ("đổ cả thực đơn ra không
# phải tư vấn"), còn ca đòi nhiều nhất là 5 món — nên 6 vừa đủ rộng mà vẫn gọn.
LIST_SIZE = 6

STAFF_NOTE = "Bạn nhắc nhân viên khi gọi món để bếp xác nhận lại giúp nhé."


@dataclass
class Reply:
    """Cùng hình dạng với `Answer` của thước đo, để chấm được trực tiếp."""

    text: str
    items: list[str] = field(default_factory=list)
    kind: str = "list"
    asks_back: bool = False
    branch: str = ""
    notes: list[str] = field(default_factory=list)


def money(value: int) -> str:
    return f"{value:,}".replace(",", ".") + "đ"


def phrase(item: dict) -> str:
    return f"{item['name']} ({money(item['price'])})"


def listing(items: list[dict]) -> str:
    return ", ".join(phrase(i) for i in items)


def select(request: Request, items: list[dict]) -> list[dict]:
    """Lọc thực đơn theo đúng những gì khách đã nói.

    Thứ tự áp ràng buộc không đổi kết quả (đều là phép AND), nhưng ràng buộc dị nguyên
    được áp **cuối** và không bao giờ bị nới — kể cả khi kết quả rỗng. Đó là fail-closed:
    thà nói "không có món nào phù hợp" còn hơn mời khách một món có thể gây dị ứng.
    """
    picked = list(items)
    if request.categories:
        picked = [i for i in picked if i["categoryId"] in request.categories]
    elif request.wants == "food":
        picked = [i for i in picked if i["categoryId"] in FOOD_CATEGORIES]
    elif request.wants == "drink":
        picked = [i for i in picked if i["categoryId"] in DRINK_CATEGORIES]
    for tag in request.require_tags:
        picked = [i for i in picked if tag in i["tags"]]
    if request.budget_max is not None:
        if request.budget_strict:
            picked = [i for i in picked if i["price"] < request.budget_max]
        else:
            picked = [i for i in picked if i["price"] <= request.budget_max]
    for tag in request.avoid_tags:
        picked = [i for i in picked if tag not in i["tags"]]
    return picked


def _order(items: list[dict], prefer_tags: list[str]) -> list[dict]:
    """Sắp cố định để câu trả lời giống nhau mọi lần chạy.

    Món mang nhãn ngữ cảnh khách nêu (dịp ăn) được đưa lên trước, nhưng món không mang
    nhãn đó **không bị loại**. Đó là cách dùng đúng cho nhóm nhãn không phủ hết 91 món:
    thiếu nhãn nghĩa là *chưa ghi nhận*, không phải *không phù hợp*.
    """
    def key(item: dict) -> tuple:
        matched = sum(1 for t in prefer_tags if t in item["tags"])
        return (-matched, item["price"], item["id"])

    return sorted(items, key=key)


def respond(request: Request, items: list[dict]) -> Reply:
    by_id = {i["id"]: i for i in items}
    named = [by_id[i] for i in request.named_items if i in by_id]

    # 1. Ngoài bài toán.
    if request.off_topic:
        return Reply(
            text=(
                "Mình chỉ hỗ trợ về món ăn và đồ uống của nhà hàng thôi ạ. "
                "Bạn cần gợi ý món gì không?"
            ),
            kind="refuse",
            branch="off_topic",
        )

    # 2. Câu chính sách và câu dinh dưỡng — chưa có kho tri thức nào.
    if request.policy_topic is not None:
        if request.policy_topic == "internal":
            return Reply(
                text=(
                    "Mình không cung cấp thông tin nội bộ của nhà hàng ạ. "
                    "Mình hỗ trợ bạn chọn món thì tiện hơn."
                ),
                kind="refuse",
                branch="internal",
            )
        if request.policy_topic == "no_size":
            # Món có thể có thật, nhưng thực đơn không có khái niệm size. Nêu giá cho
            # "size lớn" là bịa ra một thứ không tồn tại.
            item = named[0] if named else None
            head = f"{phrase(item)}. " if item is not None else ""
            return Reply(
                text=(
                    f"{head}Thực đơn chưa ghi nhận tùy chọn size cho món này, nên mình "
                    f"chưa có dữ liệu về giá theo size ạ. {STAFF_NOTE}"
                ),
                items=[item["id"]] if item is not None else [],
                kind="no_data",
                branch="no_size",
            )
        known = load_facts().get(request.policy_topic)
        if known:
            return Reply(
                text=f"{known} Nếu cần rõ hơn, bạn hỏi nhân viên giúp mình nhé.",
                kind="fact",
                branch=f"facts:{request.policy_topic}",
            )
        return Reply(
            text=(
                "Mình chưa có dữ liệu về việc này ạ. "
                f"{STAFF_NOTE}"
            ),
            kind="no_data",
            branch=f"policy:{request.policy_topic}",
        )

    # 2b. Khách hỏi một món cụ thể mà thực đơn không có. Phải nói không có, tuyệt đối
    #     không được xác nhận hay bịa giá cho nó.
    if request.unknown_item:
        return Reply(
            text=(
                "Thực đơn của nhà hàng chưa có món đó nên mình chưa có dữ liệu về nó ạ. "
                "Bạn cho mình biết bạn thích vị gì để mình gợi ý món gần nhất nhé?"
            ),
            kind="no_data",
            branch="unknown_item",
            asks_back=True,
        )

    # 3. Hỏi giá một món đã nêu tên.
    if request.asks_price and len(named) == 1 and not request.is_comparison:
        item = named[0]
        return Reply(
            text=f"{item['name']} giá {money(item['price'])} ạ.",
            items=[item["id"]],
            kind="fact",
            branch="price_lookup",
        )

    # 4. So sánh hai món đã nêu tên.
    if request.is_comparison and len(named) == 2:
        first, second = named
        gap = abs(first["price"] - second["price"])
        cheaper = first if first["price"] <= second["price"] else second
        return Reply(
            text=(
                f"{phrase(first)} và {phrase(second)}. "
                f"Chênh nhau {money(gap)}, {cheaper['name']} nhẹ ví hơn. "
                "Bạn muốn mình nói thêm về khẩu vị của từng món không?"
            ),
            items=[first["id"], second["id"]],
            kind="compare",
            branch="compare",
        )

    # 5. Món đắt nhất / rẻ nhất, trong đúng phạm vi khách nêu.
    if request.asks_extreme is not None:
        pool = select(request, items) or items
        item = min(pool, key=lambda i: i["price"]) if request.asks_extreme == "cheapest" \
            else max(pool, key=lambda i: i["price"])
        label = "rẻ nhất" if request.asks_extreme == "cheapest" else "đắt nhất"
        return Reply(
            text=f"Món {label} là {item['name']}, giá {money(item['price'])} ạ.",
            items=[item["id"]],
            kind="fact",
            branch=f"extreme:{request.asks_extreme}",
        )

    # 6a. Câu hỏi về dị nguyên của một món đã nêu tên.
    if named and request.asks_allergy:
        item = named[0]
        present = [t for t in request.avoid_tags if t in item["tags"]]
        if present:
            return Reply(
                text=(
                    f"Thực đơn có ghi nhận thành phần bạn cần tránh trong {phrase(item)}, "
                    f"nên mình không gợi ý món này. {STAFF_NOTE}"
                ),
                items=[item["id"]],
                kind="fact",
                branch="allergen_named_dish",
            )
        return Reply(
            text=(
                f"Thực đơn không ghi nhận thành phần đó trong {phrase(item)}. "
                f"Mình chỉ đọc được phần thực đơn ghi, nên {STAFF_NOTE}"
            ),
            items=[item["id"]],
            kind="fact",
            branch="allergen_named_dish",
        )

    # 6b. Khách nêu tên món mà không hỏi gì cụ thể — nêu dữ kiện món đó.
    if named and not request.require_tags and not request.categories:
        item = named[0]
        spice = next((t for t in item["tags"] if t.startswith("spice:")), None)
        spice_vi = {
            "spice:none": "không cay",
            "spice:mild": "cay nhẹ",
            "spice:medium": "cay vừa",
            "spice:hot": "cay đậm",
        }.get(spice or "", "")
        tail = f" Món này {spice_vi}." if spice_vi else ""
        return Reply(
            text=f"{phrase(item)}.{tail}",
            items=[item["id"]],
            kind="fact",
            branch="item_detail",
        )

    # 6c. Lọc thực đơn.
    said_something = bool(
        request.require_tags
        or request.prefer_tags
        or request.avoid_tags
        or request.categories
        or request.budget_max is not None
        or request.wants != "any"
    )
    if not said_something:
        return Reply(
            text=(
                "Để gợi ý đúng ý bạn, cho mình biết bạn muốn món ăn hay đồ uống, "
                "đi mấy người, và tầm giá khoảng bao nhiêu ạ?"
            ),
            kind="clarify",
            asks_back=True,
            branch="clarify",
        )

    picked = _order(select(request, items), request.prefer_tags)
    if not picked:
        return Reply(
            text=(
                "Mình chưa tìm được món nào thỏa hết những điều bạn nêu ạ. "
                f"{STAFF_NOTE}"
            ),
            kind="no_data",
            branch="empty_result",
        )

    shown = picked[:LIST_SIZE]
    lead = "Mời bạn tham khảo" if not request.avoid_tags else \
        "Thực đơn không ghi nhận thành phần bạn cần tránh ở những món này"
    text = f"{lead}: {listing(shown)}."
    if request.avoid_tags:
        text += f" {STAFF_NOTE}"
    if len(picked) > len(shown):
        text += f" Còn {len(picked) - len(shown)} món nữa, bạn muốn xem thêm không?"
    return Reply(
        text=text,
        items=[i["id"] for i in shown],
        kind="list",
        asks_back=len(picked) > len(shown),
        branch="filter",
    )
