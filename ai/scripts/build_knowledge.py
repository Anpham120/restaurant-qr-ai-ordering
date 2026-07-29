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

from rag.chunker import KnowledgeError, load_all  # noqa: E402

MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"
DICT_PATH = REPO_ROOT / "backend" / "data" / "menu-tags.json"
KNOWLEDGE_ROOT = REPO_ROOT / "ai" / "knowledge"
DERIVED_DIR = KNOWLEDGE_ROOT / "derived"
WRITTEN_DIR = KNOWLEDGE_ROOT / "written"

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
#   diet, audience, serving, promo  đã có chủ đề trong restaurant-facts.json
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

    lines = [
        "---",
        f"id: {doc_id}",
        f"title: Món {label.lower()}",
        f"topic_keys: [{group}_{value}]",
        "source: derived",
        "audience: guest",
        "---",
        "",
        f"# Món {label.lower()}",
        "",
        f"Tài liệu này nói về nhóm {group_label} **{label}**. {group_note}",
        "",
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
        cheapest, priciest = matched[0], matched[-1]
        lines += [
            "",
            "## Gợi ý chọn",
            "",
            f"- Muốn thử nhẹ ví: **{cheapest['name']}** ({money(cheapest['price'])}).",
            f"- Muốn món đáng nhớ nhất nhóm: **{priciest['name']}** "
            f"({money(priciest['price'])}).",
        ]
        no_spice = [m for m in matched if "spice:none" in m["tags"]]
        if no_spice:
            lines.append(
                f"- Không ăn được cay: có {len(no_spice)} món không cay, ví dụ "
                f"**{no_spice[0]['name']}**."
            )

    return "\n".join(lines) + "\n"


def generate(menu: dict, dictionary: dict) -> dict[Path, str]:
    items = menu["items"]
    cats = {c["categoryId"]: c["name"] for c in menu["categories"]}
    out: dict[Path, str] = {}
    for group, (group_label, group_note) in DERIVED_GROUPS.items():
        values = sorted(
            (k, e["label_vi"]) for k, e in dictionary["tags"].items() if e["group"] == group
        )
        for tag, label in values:
            value = tag.split(":", 1)[1]
            path = DERIVED_DIR / f"{group}-{value}.md"
            out[path] = build_derived_doc(
                group, tag, label, items, cats, group_label, group_note
            )
    return out


def inspect(problems: list[str]) -> tuple[int, int, Counter]:
    """Nạp toàn bộ kho, kiểm bất biến, trả về (số tài liệu, số đoạn, đếm theo nguồn)."""
    try:
        docs = load_all(KNOWLEDGE_ROOT)
    except KnowledgeError as exc:
        problems.append(str(exc))
        return 0, 0, Counter()

    chunks = [c for d in docs for c in d.chunks]
    sources = Counter(d.source for d in docs)

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
    tiny = [c.chunk_id for c in chunks if c.word_count < 12]
    if tiny:
        problems.append(f"đoạn quá ngắn (<12 từ): {tiny[:5]}")

    return len(docs), len(chunks), sources


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
        docs, chunks, sources = inspect(problems)
    else:
        DERIVED_DIR.mkdir(parents=True, exist_ok=True)
        WRITTEN_DIR.mkdir(parents=True, exist_ok=True)
        for path, text in wanted.items():
            path.write_text(text, encoding="utf-8")
        docs, chunks, sources = inspect(problems)

    print(f"tài liệu       : {docs}")
    print(f"đoạn (chunk)   : {chunks}")
    if docs:
        print(f"đoạn / tài liệu: {chunks / docs:.1f}")
    print("theo nguồn     : " + ", ".join(f"{k}={v}" for k, v in sorted(sources.items())))

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
