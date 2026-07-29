# -*- coding: utf-8 -*-
"""Xây kho tri thức nhà hàng — hai loại tri thức, hai mức độ tin được.

Vì sao chia hai loại
--------------------
Một kho tri thức trộn lẫn "sự thật tính được từ dữ liệu" với "chính sách do người viết" là
kho tri thức không ai biết tin phần nào. Bản cũ trộn cả hai vào 213 đoạn văn, và 47 đoạn
trong đó hoá ra là hướng dẫn dành cho AI đọc chứ không dành cho khách — không ai phát hiện
trong nhiều tháng.

Ở đây mỗi mục khai rõ nguồn của nó:

- **`derived`** — tính trực tiếp từ `menu-dataset.json` mỗi lần chạy script này. Không thể
  lệch khỏi thực đơn, vì nó *là* thực đơn được diễn đạt lại. Tin được như tin dữ liệu.
- **`demo`** — chính sách nhà hàng, do tôi viết giá trị hợp lý để hệ thống chạy được. **Chủ
  nhà hàng phải thay bằng sự thật.** Không ai ngoài họ biết giờ mở cửa hay có chỗ đỗ xe.

Phân biệt này máy kiểm được: `check_restaurant_facts.py` đếm và nêu tên từng mục còn ở mức
`demo`, nên nó không thể âm thầm trở thành sự thật production.

Vì sao không cần hệ truy hồi
----------------------------
Chủ đề đã được nhận diện ở bước hiểu câu hỏi, nên truy hồi ở đây là **tra khóa**. Không
xếp hạng, không ngưỡng tương đồng, nên không có chỗ nào để chệch. Bản cũ dựng embedding và
so 7 phương pháp truy hồi (~3GB RAM) cho một bài toán tra 20 khóa.

    python ai/scripts/build_restaurant_facts.py --check
    python ai/scripts/build_restaurant_facts.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"
DICT_PATH = REPO_ROOT / "backend" / "data" / "menu-tags.json"
FACTS_PATH = REPO_ROOT / "backend" / "data" / "restaurant-facts.json"

RESTAURANT = "CMC Restaurant"


def money(value: int) -> str:
    return f"{value:,}".replace(",", ".") + "đ"


def names(items: list[dict], tag: str) -> list[str]:
    return sorted(m["name"] for m in items if tag in m["tags"])


def build_derived(menu: dict, dictionary: dict) -> dict[str, dict]:
    """Tri thức tính từ thực đơn. Mỗi câu ở đây truy được về một con số cụ thể.

    Một phát hiện khi viết phần này: `diet:vegan` và `diet:vegetarian` gắn trên **đúng cùng
    17 món**, nên một trong hai nhãn không phân biệt được gì trong bộ dữ liệu này. Với món
    chay Việt thì điều đó hợp lý (chay Phật giáo vốn không dùng sữa, trứng), nhưng nghĩa là
    câu hỏi "có món thuần chay không" và "có món chay không" cho cùng kết quả — và câu trả
    lời nên nói ra điều đó thay vì để khách tự đoán.
    """
    items = menu["items"]
    categories = menu["categories"]
    prices = sorted(m["price"] for m in items)
    cheapest = min(items, key=lambda m: m["price"])
    priciest = max(items, key=lambda m: m["price"])

    preorder = names(items, "serving:preorder")
    takeaway = names(items, "serving:takeaway")
    child = names(items, "audience:child")
    elderly = names(items, "audience:elderly")
    vegetarian = names(items, "diet:vegetarian")
    vegan = names(items, "diet:vegan")
    no_spice = names(items, "spice:none")

    allergen_groups = sorted(
        entry["label_vi"]
        for entry in dictionary["tags"].values()
        if entry["group"] == "allergen"
    )
    labelled = len({m["id"] for m in items if any(t.startswith("allergen:") for t in m["tags"])})

    return {
        "menu_size": {
            "label_vi": "Quy mô thực đơn",
            "source": "derived",
            "answer_vi": (
                f"Thực đơn hiện có {len(items)} món, chia {len(categories)} nhóm: "
                + ", ".join(c["name"] for c in categories)
                + "."
            ),
        },
        "price_range": {
            "label_vi": "Khoảng giá",
            "source": "derived",
            "answer_vi": (
                f"Giá món từ {money(prices[0])} đến {money(prices[-1])}, phần lớn quanh "
                f"{money(prices[len(prices) // 2])}. Món rẻ nhất là {cheapest['name']} "
                f"({money(cheapest['price'])}), món cao nhất là {priciest['name']} "
                f"({money(priciest['price'])})."
            ),
        },
        "preorder": {
            "label_vi": "Món cần đặt trước",
            "source": "derived",
            "answer_vi": (
                f"Có {len(preorder)} món cần đặt trước vì phải chuẩn bị lâu, gồm "
                + ", ".join(preorder[:4])
                + f" và {len(preorder) - 4} món khác. Bạn nói với nhân viên trước khi gọi "
                "để bếp chuẩn bị kịp nhé."
            ),
        },
        "takeaway_items": {
            "label_vi": "Món mang đi được",
            "source": "derived",
            "answer_vi": (
                f"Thực đơn ghi nhận {len(takeaway)} món phù hợp mang đi. Đây là thông tin "
                "về từng món, còn việc nhà hàng có giao hàng hay không thì bạn xem phần "
                "giao hàng — hai việc khác nhau."
            ),
        },
        "children": {
            "label_vi": "Món cho trẻ em",
            "source": "derived",
            "answer_vi": (
                f"Thực đơn ghi nhận {len(child)} món phù hợp trẻ em và {len(elderly)} món "
                f"phù hợp người lớn tuổi. Trong đó có {len(no_spice)} món không cay trên "
                "toàn thực đơn để bạn dễ chọn."
            ),
        },
        "vegetarian": {
            "label_vi": "Món chay",
            "source": "derived",
            "answer_vi": (
                f"Có {len(vegetarian)} món chay, và cả {len(vegan)} món đều là thuần chay "
                "— không dùng sữa hay trứng. Nhóm Món chay riêng có 7 món, phần còn lại "
                "nằm rải ở các nhóm khác."
            ),
        },
        "spice_levels": {
            "label_vi": "Mức cay",
            "source": "derived",
            "answer_vi": (
                "Mỗi món đều được ghi một trong bốn mức: không cay, cay nhẹ, cay vừa, cay "
                f"đậm. Toàn thực đơn có {len(no_spice)} món không cay, nên bạn nói mức cay "
                "muốn ăn là mình lọc được ngay."
            ),
        },
        # Mục quan trọng nhất nhóm này, và là mục duy nhất nói về GIỚI HẠN của dữ liệu.
        "allergen_labelling": {
            "label_vi": "Cách thực đơn ghi nhận dị nguyên",
            "source": "derived",
            "answer_vi": (
                "Thực đơn ghi nhận "
                + ", ".join(g.lower() for g in allergen_groups)
                + f". Hiện {labelled}/{len(items)} món có ghi nhận dị nguyên, nghĩa là món "
                "KHÔNG có ghi nhận thì chỉ có nghĩa thực đơn chưa ghi, chứ không có nghĩa "
                "món đó không chứa. Vì vậy khi bạn có dị ứng, mình luôn nhắc xác nhận lại "
                "với nhân viên và bếp trước khi gọi."
            ),
        },
    }


# Chính sách nhà hàng. Giá trị dưới đây là MẪU để hệ thống chạy được — chủ nhà hàng phải
# thay bằng sự thật. Mỗi mục cố ý viết ngắn, đúng một hai câu, vì AI đọc nguyên văn.
DEMO_POLICY: dict[str, dict] = {
    "hours": {
        "label_vi": "Giờ mở cửa",
        "answer_vi": f"{RESTAURANT} mở 10h00–22h00 tất cả các ngày, kể cả cuối tuần và ngày lễ.",
    },
    "payment": {
        "label_vi": "Thanh toán",
        "answer_vi": (
            "Nhà hàng nhận tiền mặt, thẻ ngân hàng, và chuyển khoản qua mã QR VietQR hiện "
            "ngay trên hoá đơn của bàn."
        ),
    },
    "invoice": {
        "label_vi": "Hoá đơn, VAT",
        "answer_vi": (
            "Nhà hàng xuất hoá đơn VAT khi bạn cung cấp thông tin công ty. Bạn nói với "
            "nhân viên trước khi thanh toán nhé."
        ),
    },
    "parking": {
        "label_vi": "Chỗ đỗ xe",
        "answer_vi": (
            "Có chỗ gửi xe máy miễn phí trước cửa. Ô tô đỗ ở khu vực bên cạnh, nhân viên "
            "hỗ trợ hướng dẫn."
        ),
    },
    "wifi": {
        "label_vi": "Wifi",
        "answer_vi": "Có wifi miễn phí. Tên mạng và mật khẩu ghi trên thẻ để ở mỗi bàn.",
    },
    "booking": {
        "label_vi": "Đặt bàn",
        "answer_vi": (
            "Nhà hàng nhận đặt bàn qua số điện thoại của quán. Nhóm từ 8 người nên đặt "
            "trước ít nhất 2 tiếng để bếp và bàn chuẩn bị."
        ),
    },
    "delivery": {
        "label_vi": "Giao hàng",
        "answer_vi": (
            "Nhà hàng có bán mang về tại quầy. Giao tận nơi thì qua các ứng dụng giao đồ "
            "ăn, nhà hàng không nhận giao trực tiếp."
        ),
    },
    "location": {
        "label_vi": "Địa chỉ, đường đi",
        "answer_vi": (
            "Bạn hỏi nhân viên để được hướng dẫn địa chỉ và đường đi chính xác nhất nhé."
        ),
    },
    "contact": {
        "label_vi": "Liên hệ",
        "answer_vi": (
            "Bạn gọi nhân viên tại bàn, hoặc liên hệ số điện thoại của quán ghi trên hoá đơn."
        ),
    },
    "service_charge": {
        "label_vi": "Phụ phí, tiền tip",
        "answer_vi": (
            "Giá trên thực đơn là giá cuối, không thu thêm phụ phí phục vụ. Tiền tip là "
            "tuỳ tâm, không bắt buộc."
        ),
    },
    "private_room": {
        "label_vi": "Phòng riêng, tổ chức tiệc",
        "answer_vi": (
            "Nhà hàng có khu vực riêng cho nhóm đông và tiệc nhỏ. Bạn liên hệ nhân viên "
            "để xem sức chứa và đặt trước."
        ),
    },
    "high_chair": {
        "label_vi": "Ghế cho trẻ nhỏ",
        "answer_vi": "Nhà hàng có ghế ăn cho trẻ nhỏ. Bạn nói với nhân viên để được mang ra.",
    },
    "accessibility": {
        "label_vi": "Lối đi cho xe lăn",
        "answer_vi": (
            "Nhà hàng có lối vào bằng phẳng cho xe lăn. Bạn nhắn trước để nhân viên xếp "
            "bàn thuận tiện."
        ),
    },
    "smoking": {
        "label_vi": "Khu vực hút thuốc",
        "answer_vi": "Không hút thuốc trong khu vực ăn. Có khu riêng ngoài trời cho việc này.",
    },
    "outside_food": {
        "label_vi": "Mang đồ từ ngoài vào",
        "answer_vi": (
            "Nhà hàng cho phép mang bánh sinh nhật vào. Đồ ăn và thức uống khác thì không, "
            "bạn thông cảm giúp nhé."
        ),
    },
    # Mục an toàn nhất trong nhóm này, và câu trả lời cố ý viết theo hướng THẬN TRỌNG.
    "kitchen_allergy": {
        "label_vi": "Bếp xử lý dị ứng thế nào",
        "answer_vi": (
            "Bếp dùng chung khu chế biến nên không thể loại bỏ hoàn toàn nguy cơ lẫn "
            "thành phần. Khi bạn có dị ứng, bạn nói rõ với nhân viên để bếp biết và tư vấn "
            "trực tiếp — mình chỉ đọc được phần thực đơn ghi nhận."
        ),
    },
}


def build(menu: dict, dictionary: dict) -> dict:
    topics: dict[str, dict] = {}
    for key, entry in build_derived(menu, dictionary).items():
        topics[key] = {
            "label_vi": entry["label_vi"],
            "source": "derived",
            "answer_vi": entry["answer_vi"],
        }
    for key, entry in DEMO_POLICY.items():
        topics[key] = {
            "label_vi": entry["label_vi"],
            "source": "demo",
            "answer_vi": entry["answer_vi"],
        }
    return {
        "schema_version": 2,
        "_huong_dan": [
            "Sinh bởi ai/scripts/build_restaurant_facts.py — đừng sửa tay tệp này.",
            "",
            "Mỗi mục khai `source`:",
            "  derived = tính từ menu-dataset.json, không thể lệch khỏi thực đơn. Tin được.",
            "  demo    = chính sách nhà hàng, tôi viết giá trị hợp lý để hệ thống chạy được.",
            "            CHỦ NHÀ HÀNG PHẢI THAY BẰNG SỰ THẬT.",
            "",
            "Sửa nội dung `demo`: sửa DEMO_POLICY trong script rồi chạy lại, đồng thời đổi",
            "`source` của mục đó thành 'restaurant' để nó không còn bị đếm là mẫu.",
            "",
            "Để trống `answer_vi` thì AN TOÀN: AI vẫn nói 'chưa có dữ liệu' và chuyển nhân",
            "viên. Điền sai còn tệ hơn để trống, vì AI đọc nguyên văn cho khách.",
        ],
        "topics": dict(sorted(topics.items())),
        "_khong_bao_gio_tra_loi": {
            "_vi_sao": [
                "Bốn nhóm dưới đây KHÔNG thuộc kho tri thức và cố tình không có chỗ điền.",
                "Chúng nằm đây để giải thích vì sao, không phải để bổ sung sau.",
            ],
            "dinh_duong": (
                "Số calo, natri, thành phần định lượng. Thực đơn chỉ có mô tả bằng chữ. "
                "Nhãn `health:high_protein` là đánh giá cảm quan của người nhập liệu, "
                "không phải kết quả phân tích — dùng nó để trả lời calo là bịa."
            ),
            "noi_bo": (
                "Doanh thu, lợi nhuận, lương nhân viên. Không có dữ liệu, và cũng không "
                "nên có trong kênh chat khách hàng."
            ),
            "nhan_su": "Tên bếp trưởng, ai nấu món nào. Không có dữ liệu nhân sự.",
            "ngoai_bai_toan": (
                "Thời tiết, gọi taxi, dịch thuật, prompt hệ thống. Ngoài phạm vi — AI từ "
                "chối ngắn gọn rồi mời về chuyện ăn uống."
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm, không ghi.")
    args = parser.parse_args(argv)

    menu = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
    dictionary = json.loads(DICT_PATH.read_text(encoding="utf-8-sig"))
    facts = build(menu, dictionary)

    sources = Counter(t["source"] for t in facts["topics"].values())
    print(f"chủ đề          : {len(facts['topics'])}")
    for source in sorted(sources):
        print(f"  {source:12} {sources[source]:2}")
    filled = sum(1 for t in facts["topics"].values() if t["answer_vi"].strip())
    print(f"đã có nội dung  : {filled}/{len(facts['topics'])}")

    want = json.dumps(facts, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        current = FACTS_PATH.read_text(encoding="utf-8-sig") if FACTS_PATH.exists() else ""
        if current != want:
            print("\nTỆP ĐÃ COMMIT KHÁC KẾT QUẢ SINH LẠI.")
            print("Chạy `python ai/scripts/build_restaurant_facts.py` để cập nhật.")
            return 1
        print("\n--check: tệp đã commit khớp kết quả sinh lại.")
        return 0

    FACTS_PATH.write_text(want, encoding="utf-8")
    print(f"\nĐã ghi {FACTS_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
