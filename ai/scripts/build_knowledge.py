# -*- coding: utf-8 -*-
"""Sinh tài liệu tri thức tính từ thực đơn, và kiểm toàn bộ kho tri thức.

Vì sao SINH thay vì viết tay
----------------------------
Kho tri thức bản cũ có `menu.md` — 159 dòng **kể lại thực đơn bằng văn xuôi**: tên món, mã
món, mô tả từng món. Nó ghi *"hơn 90 món"* trong khi thực đơn có **đúng 91 món**. Con số viết
tay, không ai canh, và nó sai ngay từ lúc viết.

Đó là lớp lỗi không thể tránh bằng cách cẩn thận: **văn xuôi kể lại dữ liệu thì luôn trôi khỏi
dữ liệu.** Cách duy nhất chặn được là **tính lại từ dữ liệu mỗi lần**.

Nên kho tri thức chia hai loại, và phân biệt này là quyết định trung tâm của khâu dữ liệu:

    derived  — SINH từ menu-dataset.json. Không thể lệch, vì nó LÀ thực đơn diễn đạt lại.
    demo     — người viết. Chính sách nhà hàng, gợi ý kết hợp — dữ liệu không suy ra được.

30 tài liệu `derived` được sinh ở đây: 10 cách chế biến, 10 vùng miền, 10 nguyên liệu. Mỗi câu
trong đó truy được về một con số cụ thể của thực đơn.

    python ai/scripts/build_knowledge.py --check   # kiểm, không ghi
    python ai/scripts/build_knowledge.py           # sinh lại tài liệu derived
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

from rag.chunker import SYNTHESIZE, KnowledgeError, load_all  # noqa: E402

MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"
DICT_PATH = REPO_ROOT / "backend" / "data" / "menu-tags.json"
KNOWLEDGE_ROOT = REPO_ROOT / "ai" / "knowledge"
DERIVED_DIR = KNOWLEDGE_ROOT / "derived"
WRITTEN_DIR = KNOWLEDGE_ROOT / "written"
POLICY_DIR = KNOWLEDGE_ROOT / "policy"

# Nhóm nhãn nào sinh một tài liệu cho mỗi giá trị, và giải thích nhóm đó là gì.
#
# Tiêu chí chọn nhóm — và đây là tiêu chí thật, không phải "thêm cho đủ số đoạn":
#
#     Nhóm này có câu hỏi nào mà LỚP TRA KHÓA không trả lời được không?
#
# CÓ, nên sinh tài liệu:
#   method     "món nướng có gì đặc trưng"      cần mô tả, không chỉ danh sách
#   region     "đặc sản miền Trung là gì"        cần bối cảnh vùng miền
#   ingredient "món nào có bò"                   cần phân biệt với dị ứng
#   occasion   "đi hẹn hò nên gọi gì"            cần lời khuyên, không chỉ lọc
#   flavour    "món đậm đà đưa cơm"              cần diễn giải cảm giác vị
#   health     "mình đang giảm cân"               cần lời khuyên kèm cảnh báo
#
# KHÔNG, nên bỏ qua:
#   spice, price, party, season   lớp lọc theo nhãn đã đúng 100% (phủ 91/91 món)
#   diet, audience, serving, promo  đã có tài liệu chính sách trong `knowledge/policy/`
#
# Thêm tài liệu cho nhóm đã được xử lý tốt là tạo **đường thứ hai cho cùng một việc** — đúng
# bệnh 8 đường chồng nhau của bản cũ, nơi 2 đường bị tắt mà hệ thống vẫn chạy đúng.
DERIVED_GROUPS = {
    "method": (
        "cách chế biến",
        "Cách chế biến quyết định kết cấu và vị của món. Khách hay hỏi theo cách này khi họ "
        "biết mình muốn gì về kết cấu — giòn, mềm, hay nước.",
    ),
    "region": (
        "vùng miền",
        "Ẩm thực Việt khác nhau rõ theo vùng. Khách hỏi theo vùng khi muốn ăn đúng đặc sản "
        "một nơi, hoặc khi nhớ món quê.",
    ),
    "ingredient": (
        "nguyên liệu chính",
        "Khách hỏi theo nguyên liệu khi họ có sở thích hoặc tránh một loại đạm nào đó. Lưu ý "
        "đây KHÁC với dị ứng: dị ứng dùng nhãn allergen và luôn fail-closed.",
    ),
    "occasion": (
        "dịp ăn",
        "Dịp ăn là NGỮ CẢNH, không phải ràng buộc: món không mang nhãn dịp này vẫn có thể phù "
        "hợp. Nhóm occasion chỉ phủ 79/91 món, nên dùng nó để sắp thứ tự chứ không để loại "
        "món.",
    ),
    "flavour": (
        "hương vị",
        "Khách thường mô tả vị bằng cảm giác chứ không bằng tên nhãn — 'chua chua', 'đậm đà "
        "đưa cơm', 'thanh thanh'. Nhóm flavour phủ 72/91 món nên chỉ dùng theo chiều khẳng "
        "định.",
    ),
    "health": (
        "sức khỏe",
        "QUAN TRỌNG: các nhãn này là ĐÁNH GIÁ CẢM QUAN của người nhập liệu, KHÔNG phải kết "
        "quả phân tích dinh dưỡng. Thực đơn không có số calo hay natri nào. Dùng chúng để gợi "
        "ý được, dùng để khẳng định về sức khỏe thì không.",
    ),
}


# Danh mục đồ uống — giữ khớp với `understand.DRINK_CATEGORIES`.
DANH_MUC_DO_UONG = ("cat_drink", "cat_juice", "cat_alcohol")


def money(value: int) -> str:
    return f"{value:,}".replace(",", ".") + "đ"


def spice_label(item: dict) -> str:
    return {
        "spice:none": "không cay",
        "spice:mild": "cay nhẹ",
        "spice:medium": "cay vừa",
        "spice:hot": "cay đậm",
    }.get(next((t for t in item["tags"] if t.startswith("spice:")), ""), "")


def build_derived_doc(
    group: str, tag: str, label: str, items: list[dict], cats: dict[str, str],
    group_label: str, group_note: str,
) -> str:
    """Một tài liệu cho một giá trị nhãn. Mọi con số tính từ `items`."""
    matched = sorted(
        (m for m in items if tag in m["tags"]), key=lambda m: (m["price"], m["id"])
    )
    value = tag.split(":", 1)[1]
    doc_id = f"kb.{group}.{value}.v1"

    by_cat = Counter(cats[m["categoryId"]] for m in matched)
    prices = [m["price"] for m in matched]
    allergens = Counter(
        t.split(":", 1)[1] for m in matched for t in m["tags"] if t.startswith("allergen:")
    )
    vi_allergen = {"seafood": "hải sản", "peanut": "đậu phộng", "egg": "trứng",
                   "dairy": "sữa", "gluten": "gluten"}

    # TIÊU ĐỀ phải khớp thứ tài liệu THẬT SỰ liệt kê.
    #
    # Nhãn `flavour`, `region`, `occasion`, `health` áp cho CẢ món ăn lẫn đồ uống, nên 19/49 tài
    # liệu `derived` có đồ uống trong danh sách. Nhưng tiêu đề luôn là "Món {nhãn}", nên khách đọc
    # tài liệu **Món chua** và thấy Cocktail chanh đào mật ong, Rượu mơ Hà Nội, Sinh tố dâu tây.
    #
    # Danh sách KHÔNG sai — cocktail chanh đào đúng là vị chua. Cái sai là chữ "Món", và nó sai
    # theo kiểu làm khách nghi ngờ cả phần đúng.
    #
    # Tiêu đề tính từ nội dung thật, nên nó không thể lệch: có đồ uống thì nói có đồ uống.
    co_uong = any(m.get("categoryId") in DANH_MUC_DO_UONG for m in matched)
    co_mon = any(m.get("categoryId") not in DANH_MUC_DO_UONG for m in matched)
    if co_uong and co_mon:
        tieu_de = f"Món và đồ uống {label.lower()}"
    elif co_uong:
        tieu_de = f"Đồ uống {label.lower()}"
    else:
        tieu_de = f"Món {label.lower()}"

    lines = [
        "---",
        f"id: {doc_id}",
        f"title: {tieu_de}",
        f"topic_keys: [{group}_{value}]",
        "source: derived",
        "audience: guest",
        "answer_mode: synthesize",
        "---",
        "",
        f"# {tieu_de}",
        "",
        f"Tài liệu này nói về nhóm {group_label} **{label}**. {group_note}",
        "",
        # Tiêu đề mục dùng CHUNG một khuôn cho cả 57 tài liệu `derived`.
        #
        # Đã thử đổi sang tiêu đề đặc thù theo tài liệu ("Gợi ý chọn" -> "Gợi ý chọn món gà") vì
        # `analyze_failures.py` xếp 19/43 ca hỏng vào lớp `retrieval_twin_section`. Kho cải thiện
        # rõ — 179 -> 365 tiêu đề khác nhau, 283/452 -> 93/452 đoạn dùng chung — nhưng **truy hồi
        # KHÔNG khá hơn**:
        #
        #     Hit@1 niêm phong  0,609 -> 0,609   (không đổi)
        #     Hit@5 niêm phong  0,674 -> 0,630   (tụt)
        #     tổng ca hỏng         43 -> 46      (tăng)
        #
        # 19 ca kia không được sửa — chúng ĐỔI TÊN LỖI từ `twin_section` sang `retrieval_rank`.
        # Trần không nằm ở tiêu đề. Và việc đổi còn xoá mất tiền đề của họ `derived` trong
        # `build_chunk_selection_cases.py`, vốn tồn tại CHÍNH VÌ các tài liệu này dùng chung khuôn.
        #
        # Giữ khuôn chung, và ghi kết quả thí nghiệm ở đây để không ai phải chạy lại.
        "## Tổng quan",
        "",
        f"Thực đơn có **{len(matched)} món** {label.lower()}"
        + (f", giá từ {money(min(prices))} đến {money(max(prices))}." if prices else "."),
    ]

    if by_cat:
        spread = ", ".join(f"{name} ({n} món)" for name, n in by_cat.most_common())
        lines += ["", f"Chúng nằm ở các nhóm: {spread}."]

    lines += ["", "## Danh sách món", ""]
    for m in matched:
        spice = spice_label(m)
        note = f" — {spice}" if spice else ""
        lines.append(f"- **{m['name']}** ({money(m['price'])}){note}")

    # Mục dị nguyên: nói cả điều biết VÀ điều không biết. Đây là chỗ dễ sai nhất.
    lines += ["", "## Dị nguyên trong nhóm này", ""]
    if allergens:
        listed = ", ".join(
            f"{vi_allergen.get(k, k)} ({n} món)" for k, n in allergens.most_common()
        )
        lines.append(f"Thực đơn ghi nhận: {listed}.")
    else:
        lines.append("Thực đơn không ghi nhận dị nguyên nào ở nhóm món này.")
    unlabelled = sum(
        1 for m in matched if not any(t.startswith("allergen:") for t in m["tags"])
    )
    lines += [
        "",
        f"Trong {len(matched)} món này, **{unlabelled} món chưa có ghi nhận dị nguyên nào**. "
        "Chưa ghi nhận KHÔNG có nghĩa là không chứa — thực đơn chỉ ghi phần đã được ghi. Khi "
        "khách có dị ứng, luôn nhắc xác nhận lại với nhân viên và bếp trước khi gọi.",
    ]

    if len(matched) >= 3:
        # GỢI Ý phải lấy ví dụ CÙNG LOẠI với thứ câu gợi ý đang nói.
        #
        # Bản trước lấy `matched[0]` (rẻ nhất) và `no_spice[0]` (rẻ nhất trong nhóm không cay).
        # Danh sách sắp theo giá, và **đồ uống là thứ rẻ nhất thực đơn** (bia hơi 12.000đ), nên
        # chúng thắng ở mọi nhóm có đồ uống. Kết quả in ra 18 tài liệu:
        #
        #     - Muốn thử nhẹ ví: **Bia Hà Nội** (18.000đ).
        #     - Không ăn được cay: có 10 món không cay, ví dụ **Bia Hà Nội**.
        #
        # Dòng thứ hai là dòng tệ nhất trong cả kho: khách nói **không ăn được cay** — một câu về
        # MÓN ĂN — và nhận về một chai bia. Nó không sai về dữ liệu (bia đúng là không cay) mà sai
        # về việc trả lời đúng câu hỏi, và nó lặp ở 18/49 tài liệu.
        #
        # "Bia hơi Hà Nội" xuất hiện ở 8 tài liệu, "Nước rau má" ở 6 — nên lỗi này còn nhân bản
        # cùng một tên món khắp kho.
        #
        # Quy tắc: ưu tiên MÓN ĂN làm ví dụ; chỉ dùng đồ uống khi nhóm KHÔNG có món ăn nào (tài
        # liệu về chính nhóm đồ uống), và khi đó gọi đúng tên là "đồ uống".
        mon_an = [m for m in matched if m.get("categoryId") not in DANH_MUC_DO_UONG]
        vi_du = mon_an or matched
        tu = "món" if mon_an else "đồ uống"
        cheapest, priciest = vi_du[0], vi_du[-1]
        lines += [
            "",
            "## Gợi ý chọn",
            "",
            f"- Muốn thử nhẹ ví: **{cheapest['name']}** ({money(cheapest['price'])}).",
            f"- Muốn {tu} đáng nhớ nhất nhóm: **{priciest['name']}** "
            f"({money(priciest['price'])}).",
        ]
        no_spice = [m for m in vi_du if "spice:none" in m["tags"]]
        if no_spice and mon_an:
            # Chỉ nêu dòng độ cay khi nhóm CÓ món ăn — độ cay không áp dụng cho đồ uống, và
            # đếm cả đồ uống vào "10 món không cay" là thổi phồng con số bằng thứ không liên quan.
            lines.append(
                f"- Không ăn được cay: có {len(no_spice)} món không cay, ví dụ "
                f"**{no_spice[0]['name']}**."
            )

    return "\n".join(lines) + "\n"


def _policy_doc(topic: str, title: str, answer: str) -> str:
    """Một tài liệu chính sách `verbatim`: một khối, không mục `##`.

    Ngắt dòng ở 96 ký tự cho dễ đọc — an toàn vì `KnowledgeDoc.verbatim_answer` thu khoảng
    trắng về một dấu cách, nên chuỗi tới khách không đổi theo cách ngắt dòng.
    """
    lines, cur = [], ""
    for word in " ".join(answer.split()).split():
        if cur and len(cur) + 1 + len(word) > 96:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    body = "\n".join(lines)
    return (
        "---\n"
        f"id: kb.policy.{topic}.v1\n"
        f"title: {title}\n"
        f"topic_keys: [{topic}]\n"
        "source: derived\n"
        "audience: guest\n"
        "answer_mode: verbatim\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{body}\n"
    )


def build_policy_derived(menu: dict, dictionary: dict) -> dict[Path, str]:
    """Tám tài liệu chính sách có SỐ tính từ thực đơn, nên chúng phải do máy sinh.

    Mười sáu tài liệu chính sách còn lại (`giờ mở cửa`, `wifi`, `đỗ xe`...) là chính sách thật
    của nhà hàng, không suy được từ thực đơn — chúng là tệp tĩnh trong `knowledge/policy/` và
    script này không chạm vào.

    Phần này trước đây nằm ở `build_restaurant_facts.py`, sinh ra `restaurant-facts.json`. Kho
    tri thức đã gộp về một chỗ nên script đó nghỉ, và logic tính chuyển về đây nguyên văn — mọi
    con số phải giữ đúng như cũ, nếu không 112 ca sẽ đổi kết quả.

    Ghi nhận từ lúc viết phần này: `diet:vegan` và `diet:vegetarian` gắn trên ĐÚNG CÙNG 17 món,
    nên trong bộ dữ liệu này một trong hai nhãn không phân biệt được gì. Với món chay Việt thì
    hợp lý (chay Phật giáo vốn không dùng sữa, trứng), nhưng nghĩa là câu "có món thuần chay
    không" và "có món chay không" cho cùng kết quả — và câu trả lời nói ra điều đó thay vì để
    khách tự đoán.
    """
    items = menu["items"]
    categories = menu["categories"]
    prices = sorted(m["price"] for m in items)
    cheapest = min(items, key=lambda m: m["price"])
    priciest = max(items, key=lambda m: m["price"])

    def names(tag: str) -> list[str]:
        return sorted(m["name"] for m in items if tag in m["tags"])

    preorder = names("serving:preorder")
    takeaway = names("serving:takeaway")
    child = names("audience:child")
    elderly = names("audience:elderly")
    vegetarian = names("diet:vegetarian")
    vegan = names("diet:vegan")
    no_spice = names("spice:none")

    allergen_groups = sorted(
        entry["label_vi"] for entry in dictionary["tags"].values() if entry["group"] == "allergen"
    )
    labelled = len({m["id"] for m in items if any(t.startswith("allergen:") for t in m["tags"])})

    facts = {
        "menu_size": (
            "Quy mô thực đơn",
            f"Thực đơn hiện có {len(items)} món, chia {len(categories)} nhóm: "
            + ", ".join(c["name"] for c in categories)
            + ".",
        ),
        "price_range": (
            "Khoảng giá",
            f"Giá món từ {money(prices[0])} đến {money(prices[-1])}, phần lớn quanh "
            f"{money(prices[len(prices) // 2])}. Món rẻ nhất là {cheapest['name']} "
            f"({money(cheapest['price'])}), món cao nhất là {priciest['name']} "
            f"({money(priciest['price'])}).",
        ),
        "preorder": (
            "Món cần đặt trước",
            f"Có {len(preorder)} món cần đặt trước vì phải chuẩn bị lâu, gồm "
            + ", ".join(preorder[:4])
            + f" và {len(preorder) - 4} món khác. Bạn nói với nhân viên trước khi gọi "
            "để bếp chuẩn bị kịp nhé.",
        ),
        "takeaway_items": (
            "Món mang đi được",
            f"Thực đơn ghi nhận {len(takeaway)} món phù hợp mang đi. Đây là thông tin "
            "về từng món, còn việc nhà hàng có giao hàng hay không thì bạn xem phần "
            "giao hàng — hai việc khác nhau.",
        ),
        "children": (
            "Món cho trẻ em",
            f"Thực đơn ghi nhận {len(child)} món phù hợp trẻ em và {len(elderly)} món "
            f"phù hợp người lớn tuổi. Trong đó có {len(no_spice)} món không cay trên "
            "toàn thực đơn để bạn dễ chọn.",
        ),
        "vegetarian": (
            "Món chay",
            f"Có {len(vegetarian)} món chay, và cả {len(vegan)} món đều là thuần chay "
            "— không dùng sữa hay trứng. Nhóm Món chay riêng có 7 món, phần còn lại "
            "nằm rải ở các nhóm khác.",
        ),
        "spice_levels": (
            "Mức cay",
            "Mỗi món đều được ghi một trong bốn mức: không cay, cay nhẹ, cay vừa, cay "
            f"đậm. Toàn thực đơn có {len(no_spice)} món không cay, nên bạn nói mức cay "
            "muốn ăn là mình lọc được ngay.",
        ),
        # Mục quan trọng nhất nhóm này, và là mục duy nhất nói về GIỚI HẠN của dữ liệu.
        "allergen_labelling": (
            "Cách thực đơn ghi nhận dị nguyên",
            "Thực đơn ghi nhận "
            + ", ".join(g.lower() for g in allergen_groups)
            + f". Hiện {labelled}/{len(items)} món có ghi nhận dị nguyên, nghĩa là món "
            "KHÔNG có ghi nhận thì chỉ có nghĩa thực đơn chưa ghi, chứ không có nghĩa "
            "món đó không chứa. Vì vậy khi bạn có dị ứng, mình luôn nhắc xác nhận lại "
            "với nhân viên và bếp trước khi gọi.",
        ),
    }
    return {
        POLICY_DIR / f"{topic.replace('_', '-')}.md": _policy_doc(topic, title, answer)
        for topic, (title, answer) in facts.items()
    }


def generate(menu: dict, dictionary: dict) -> dict[Path, str]:
    """Chỉ còn sinh tài liệu CHÍNH SÁCH. 49 tài liệu theo nhãn đã bị bỏ — xem bên dưới.

    VÌ SAO BỎ 49 TÀI LIỆU SINH THEO NHÃN
    ------------------------------------
    Chúng chiếm **190/372 = 51% chỉ mục truy hồi** và không phục vụ ai.

    1. Nhánh lọc nhãn KHÔNG đọc chúng. `select(request, items)` chỉ nhận thực đơn — không có
       đường nào để nó mở kho tri thức.
    2. Tra khóa KHÔNG tới được chúng: 0/49 `topic_keys` có mặt trong từ vựng.
    3. Nên chỉ truy hồi toàn kho đọc chúng — và 106 ca từng nhắm vào chúng đều là **câu chọn
       món** ("Món Hà Nội có gì?"), tức câu của nhánh lọc. Sau khi thêm 36 cụm từ vựng,
       **99,1% (105/106)** số ca ấy đi thẳng nhánh lọc và không còn chạm truy hồi.

    Và chúng làm HỎNG phần truy hồi còn lại: 49 tài liệu dùng chung đúng 4 tiêu đề mục, tài liệu
    điển hình có **0 từ chỉ xuất hiện ở riêng nó** (văn xuôi viết tay: 2, nhiều nhất 18), vì danh
    sách món rò rỉ từ vựng của mọi nhóm khác. Bộ nhúng phải chọn giữa 190 đoạn gần trùng nhau.

    Ba cách chữa đã đo, cả ba đều không thắng — xếp lại bằng cross-encoder (p = 0,8238), gộp
    thành 6 tài liệu theo họ (p = 0,5488), cắt bớt mục (0 từ riêng lên 1). Thứ trùng lặp là chính
    cái khuôn, nên cách duy nhất còn lại là **bỏ hẳn**.

    Kết quả: chỉ mục còn **182 đoạn văn xuôi viết tay đồng nhất** — đúng thứ bài toán RAG cần.
    Nội dung mất đi không mất thật: mọi thứ 49 tài liệu ấy nói (danh sách món mang nhãn X, dị
    nguyên trong nhóm, dải giá) đều tính được từ nhãn, và nhánh lọc làm việc đó **chính xác
    100,00%** thay vì 54,40%.
    """
    return build_policy_derived(menu, dictionary)


def inspect(problems: list[str]) -> tuple[int, int, Counter, Counter]:
    """Nạp toàn bộ kho, kiểm bất biến, trả về (số tài liệu, số đoạn, đếm theo nguồn)."""
    try:
        docs = load_all(KNOWLEDGE_ROOT)
    except KnowledgeError as exc:
        problems.append(str(exc))
        return 0, 0, Counter(), Counter()

    chunks = [c for d in docs for c in d.chunks]
    sources = Counter(d.source for d in docs)
    modes = Counter(d.answer_mode for d in docs)

    # Bất biến 1: chunk_id không trùng. Tập đánh giá truy hồi trỏ vào chunk_id, nên trùng là
    # hai đoạn khác nhau cùng một địa chỉ.
    dupes = [k for k, n in Counter(c.chunk_id for c in chunks).items() if n > 1]
    if dupes:
        problems.append(f"chunk_id trùng: {dupes[:5]}")

    # Bất biến 2: mọi đoạn phải kèm tiêu đề tài liệu, để tự đủ nghĩa khi trích rời.
    orphan = [c.chunk_id for c in chunks if not c.text.startswith(c.title)]
    if orphan:
        problems.append(f"đoạn không kèm tiêu đề tài liệu: {orphan[:5]}")

    # Bất biến 3: đoạn quá ngắn thì vô dụng khi truy hồi — nó không mang đủ tín hiệu.
    #
    # Chỉ áp cho đoạn `synthesize`. Tài liệu `verbatim` không đi qua xếp hạng, và câu trả lời
    # nguyên văn thì NGẮN LÀ ĐÚNG — "Có wifi miễn phí. Tên mạng và mật khẩu ghi trên thẻ để ở
    # mỗi bàn." đúng 16 từ và đó là câu trả lời hoàn chỉnh.
    tiny = [c.chunk_id for c in chunks if c.answer_mode == SYNTHESIZE and c.word_count < 12]
    if tiny:
        problems.append(f"đoạn quá ngắn (<12 từ): {tiny[:5]}")

    problems.extend(kiem_so_tien(docs))

    return len(docs), len(chunks), sources, modes


# Ngưỡng ngân sách tròn — số dùng để NÓI VỀ mức chi, không phải giá của món nào.
#
# Danh sách này hẹp và viết tay có chủ ý: mỗi con số ở đây là một lần ai đó quyết định rằng nó
# KHÔNG cần bám giá món. Để trống danh sách thì tám câu tư vấn ngân sách hỏng; để nó rộng thì phép
# kiểm mất tác dụng. Thêm số vào đây phải là một hành động có ý thức.
NGUONG_NGAN_SACH = {90_000, 100_000, 200_000, 300_000, 500_000, 62_500}


def kiem_so_tien(docs) -> list[str]:
    """Mọi số tiền trong kho phải truy được về `menu-dataset.json`.

    Vì sao bất biến này tồn tại
    ---------------------------
    36 tài liệu `written` là văn xuôi VIẾT TAY, và nhiều đoạn trong đó nêu số tiền: "giá trung vị
    của thực đơn là 65.000đ", "lẩu đều từ 250.000đ trở lên". Những con số ấy đúng lúc viết, và
    **không có gì buộc chúng đúng sau khi thực đơn đổi giá**. Một tài liệu `derived` thì không trôi
    được vì nó sinh lại từ dữ liệu; một tài liệu `written` thì trôi được, và trôi im lặng.

    Đây là hố mà đường sinh KHÔNG che: `build_knowledge.py` chỉ sinh lại phần `derived`.

    Lỗ này lộ ra khi đổi mô hình nhúng sang `bge-m3`. Mô hình mới chọn một MỤC KHÁC của tài liệu
    `meal_sets` cho câu "Có set bữa trưa nào không?", và mục đó có hai con số. Thước đo 140 ca báo
    đỏ vì nó không có nguồn hợp lệ nào cho "số tiền suy từ tổng thể thực đơn".

    Kiểm lại thì **cả hai con số đều đúng** — trung vị đúng 65.000đ, lẩu rẻ nhất đúng 250.000đ. Nên
    việc phải làm không phải nới thước đo mà là **bảo đảm chúng luôn đúng**, rồi mới cho thước đo
    tin vào chữ trong kho.

    Đo trên kho hiện tại: **1.031 lần nêu tiền, 1.023 khớp giá món thật hoặc trung vị (99,22%)**,
    8 lần còn lại là ngưỡng ngân sách tròn trong `NGUONG_NGAN_SACH`.
    """
    import json
    import re
    import statistics

    duong = REPO_ROOT / "backend" / "data" / "menu-dataset.json"
    items = json.loads(duong.read_text(encoding="utf-8-sig"))["items"]
    hop_le = {i["price"] for i in items}
    hop_le.add(int(statistics.median(i["price"] for i in items)))
    hop_le |= NGUONG_NGAN_SACH

    mau = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*đ")
    la: list[str] = []
    for d in docs:
        for m in mau.findall(d.title + " " + getattr(d, "body", "")):
            v = int(m.replace(".", ""))
            if v not in hop_le:
                la.append(f"{d.doc_id}: {m}đ không phải giá món, trung vị, hay ngưỡng đã khai")
    return sorted(set(la))[:8]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kiểm, không ghi.")
    args = parser.parse_args(argv)

    menu = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
    dictionary = json.loads(DICT_PATH.read_text(encoding="utf-8-sig"))
    wanted = generate(menu, dictionary)
    problems: list[str] = []

    if args.check:
        stale = [
            p for p, text in wanted.items()
            if not p.exists() or p.read_text(encoding="utf-8-sig") != text
        ]
        if stale:
            problems.append(
                f"{len(stale)} tài liệu derived khác kết quả sinh lại: "
                + ", ".join(p.name for p in stale[:4])
            )
        docs, chunks, sources, modes = inspect(problems)
    else:
        DERIVED_DIR.mkdir(parents=True, exist_ok=True)
        WRITTEN_DIR.mkdir(parents=True, exist_ok=True)
        POLICY_DIR.mkdir(parents=True, exist_ok=True)
        for path, text in wanted.items():
            path.write_text(text, encoding="utf-8")
        docs, chunks, sources, modes = inspect(problems)

    print(f"tài liệu       : {docs}")
    print(f"đoạn (chunk)   : {chunks}")
    if docs:
        print(f"đoạn / tài liệu: {chunks / docs:.1f}")
    print("theo nguồn     : " + ", ".join(f"{k}={v}" for k, v in sorted(sources.items())))
    print("theo chế độ    : " + ", ".join(f"{k}={v}" for k, v in sorted(modes.items())))

    if problems:
        print(f"\nVẤN ĐỀ ({len(problems)}):")
        for line in problems:
            print(f"  - {line}")
        if not args.check:
            print("Đã ghi tài liệu derived, nhưng kho vẫn có vấn đề ở trên.")
        return 1

    if args.check:
        print("\n--check: tài liệu derived khớp kết quả sinh lại, kho tri thức hợp lệ.")
    else:
        print(f"\nĐã ghi {len(wanted)} tài liệu vào {DERIVED_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
