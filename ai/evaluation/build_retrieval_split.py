# -*- coding: utf-8 -*-
"""Chia tập đánh giá truy hồi thành ba nhóm, TẤT ĐỊNH và theo HỌ.

Ba nhóm, không phải hai
-----------------------
    chốt         luôn phải đạt. KHÔNG phải số liệu — một ca đỏ ở đây là CHẶN.
    phát triển   được xem, được sửa theo.
    niêm phong   CHỈ MỞ MỘT LẦN để chốt kết quả.

Chia theo HỌ, không theo ca. Nếu chia theo ca thì `kb-region-central-1` vào tập phát triển và
`kb-region-central-2` vào tập niêm phong — hai ca hỏi CÙNG một chủ đề, chỉ khác cách diễn đạt.
Xem một ca là biết ca kia, nên tập niêm phong không còn niêm phong.

Nhóm CHỐT của tập này là ba họ đo việc BIẾT KHI NÀO KHÔNG TRẢ LỜI
-----------------------------------------------------------------
    kb-verbatim-topic   chủ đề trả nguyên văn — đoạn của nó KHÔNG ở trong chỉ mục
    kb-out-of-scope     ngoài phạm vi
    kb-number           câu về SỐ — BM25 và embedding không hiểu số

Vì sao ba họ này là chốt chứ không phải số liệu: một bộ truy hồi **luôn trả về 5 đoạn** sẽ đạt
điểm cao trên mọi họ khác, và chỉ ba họ này bắt được nó. Đưa chúng vào tập phát triển thì tỷ lệ
chung sẽ che mất chúng — đúng lỗi mà tập 119 ca đã tránh bằng cách tách nhóm chốt.

Bài học đã trả giá: **tập niêm phong của tập 119 ca đã dùng hết ở bước 4.** Mọi con số trên nó
không còn là held-out. Tập này chỉ được mở MỘT lần, và lần đó phải ghi vào tài liệu.

    python ai/evaluation/build_retrieval_split.py           # ghi split
    python ai/evaluation/build_retrieval_split.py --check   # kiểm, không ghi
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "retrieval_cases.json"
OUT_PATH = HERE / "retrieval_split.json"

# Họ CHỐT — xem docstring. Ba họ này đo điều Hit@k không đo.
GATE_FAMILIES = {"kb-verbatim-topic", "kb-out-of-scope", "kb-number"}

# Tỷ lệ niêm phong trong phần còn lại. 1/3 để tập niêm phong đủ lớn cho con số có nghĩa: với 11 họ
# còn lại thì 1/3 là ~4 họ, và một họ lệch là ~25% — vẫn thô, nên con số phải kèm `n`.
SEALED_SHARE = 3


def signature(family: str) -> tuple[str, str]:
    """Vân tay tất định của một họ. Dùng hash chứ không dùng `random`.

    `random.shuffle` với seed cũng tất định, nhưng nó phụ thuộc PHIÊN BẢN Python — Python đổi
    thuật toán thì phép chia đổi theo, và tập niêm phong lặng lẽ trộn vào tập phát triển. Hash
    của tên họ thì không đổi bao giờ.
    """
    return hashlib.sha256(family.encode("utf-8")).hexdigest(), family


def build(cases: list[dict]) -> dict:
    by_family = collections.Counter(c["family"] for c in cases)
    gate = sorted(f for f in by_family if f in GATE_FAMILIES)
    rest = sorted((f for f in by_family if f not in GATE_FAMILIES), key=signature)

    sealed = [f for i, f in enumerate(rest) if i % SEALED_SHARE == 0]
    dev = [f for f in rest if f not in sealed]

    return {
        "schema_version": 1,
        "authored": "Sinh bởi ai/evaluation/build_retrieval_split.py — đừng sửa tay.",
        "how": [
            "Chia theo HỌ, không theo ca: hai ca cùng họ hỏi cùng chủ đề nên xem một ca là biết",
            "ca kia. Chia theo ca thì tập niêm phong không còn niêm phong.",
            "",
            "Thứ tự do sha256(tên họ) quyết định, không do random.shuffle — shuffle phụ thuộc",
            "phiên bản Python, nên Python đổi thuật toán thì phép chia đổi theo và tập niêm phong",
            "lặng lẽ trộn vào tập phát triển.",
        ],
        "sealed_opened": False,
        "sealed_opened_note": (
            "Đặt thành true VÀ ghi ngày khi mở tập niêm phong. Tập 119 ca đã mất tính held-out vì "
            "được mở rồi sửa theo — đừng lặp lại mà không ghi."
        ),
        "gate_families": gate,
        "dev_families": sorted(dev),
        "test_families": sorted(sealed),
    }


def describe(cases: list[dict], split: dict) -> list[str]:
    by_family = collections.defaultdict(list)
    for c in cases:
        by_family[c["family"]].append(c)

    nhom = {
        "chốt": set(split["gate_families"]),
        "phát triển": set(split["dev_families"]),
        "niêm phong": set(split["test_families"]),
    }
    lines = [f"{'nhóm':14}{'ca':>5}{'họ':>5}   {'rỗng':>5}   họ"]
    lines.append("-" * 92)
    for ten, ho in nhom.items():
        ca = [c for f in ho for c in by_family[f]]
        rong = sum(1 for c in ca if c["expect_nothing"])
        lines.append(f"{ten:14}{len(ca):>5}{len(ho):>5}   {rong:>5}   {', '.join(sorted(ho))[:52]}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kiểm, không ghi.")
    args = parser.parse_args(argv)

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))["cases"]
    split = build(cases)

    # Bất biến: mọi họ phải thuộc đúng MỘT nhóm. Một họ ở hai nhóm là rò rỉ tập niêm phong.
    gate, dev, test = (set(split[k]) for k in ("gate_families", "dev_families", "test_families"))
    problems: list[str] = []
    if gate & dev or gate & test or dev & test:
        problems.append("có họ thuộc hai nhóm — rò rỉ tập niêm phong")
    tat_ca = {c["family"] for c in cases}
    if gate | dev | test != tat_ca:
        problems.append(f"họ chưa được gán: {sorted(tat_ca - (gate | dev | test))}")
    thieu_gate = GATE_FAMILIES - tat_ca
    if thieu_gate:
        problems.append(
            f"họ CHỐT không có ca nào: {sorted(thieu_gate)} — nhóm chốt rỗng thì nó không chặn gì"
        )

    for line in describe(cases, split):
        print(line)

    if problems:
        print(f"\nVẤN ĐỀ ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        return 1

    text = json.dumps(split, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT_PATH.exists() or OUT_PATH.read_text(encoding="utf-8-sig") != text:
            print("\n--check: split khác kết quả sinh lại. Chạy lại script.")
            return 1
        print("\n--check: không ghi tệp nào.")
    else:
        OUT_PATH.write_text(text, encoding="utf-8")
        print(f"\nĐã ghi {OUT_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
