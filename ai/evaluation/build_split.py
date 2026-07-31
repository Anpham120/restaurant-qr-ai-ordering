# -*- coding: utf-8 -*-
"""Chia tập đánh giá thành ba phần: chốt an toàn, tập phát triển, tập niêm phong.

Vì sao ba phần chứ không phải hai
---------------------------------
Ca an toàn (dị ứng, bịa món, rò rỉ chỉ dẫn nội bộ) **không phải số liệu để so**. Chúng
là chốt: luôn phải xanh, ở mọi lần chạy. Đưa chúng vào tập phát triển thì tỷ lệ chung sẽ
che mất một ca dị ứng đỏ; đưa vào tập niêm phong thì một lỗi an toàn có thể nằm im nhiều
tuần. Nên chúng thành nhóm riêng, chạy mọi lần, và một ca đỏ là chặn.

Phần còn lại chia phát triển / niêm phong, với hai ràng buộc:

1. **Chia theo họ câu hỏi, không theo từng ca.** Nếu "Món nào dưới 50.000đ?" ở tập phát
   triển mà "Mình có 200 nghìn, ăn được món gì?" ở tập niêm phong thì chỉnh cho ca đầu
   xanh sẽ kéo ca sau xanh theo mà không học được gì. Cả họ đi cùng một phía.
2. **Cân theo (loại câu hỏi, dạng đáp án).** Tập phát triển chỉ dự báo được tập niêm
   phong khi hai bên có thành phần giống nhau. Bản cũ chia theo họ nhưng không cân, nên
   một bên nặng ca tra cứu và bên kia nặng ca phán đoán.

Cách chia là **tất định, không dùng số ngẫu nhiên**: sắp họ theo số ca giảm dần rồi tên
tăng dần, và lần lượt đặt mỗi họ vào phía đang thiếu nhất ở đúng chữ ký (loại, dạng) của
nó. Không có hạt giống nào để chọn cho ra kết quả đẹp, và ai chạy lại cũng ra đúng vậy.

    python ai/evaluation/build_split.py --check
    python ai/evaluation/build_split.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "cases.json"
SPLIT_PATH = HERE / "split.json"

# Họ câu hỏi là chốt an toàn. Ba nhóm, mỗi nhóm ứng một điều "tuyệt đối không làm" ở
# `docs/00-problem-statement.md`:
#   - dị ứng      -> không được khẳng định một món an toàn
#   - bịa món     -> không được bịa món hay giá
#   - rò rỉ       -> không được để lộ chỉ dẫn nội bộ
GATE_FAMILIES = {
    "allergen_avoid",
    "allergen_named_dish",
    "nonexistent_item",
    "unrelated",
}

# Tỷ lệ mong muốn cho tập phát triển, phần còn lại niêm phong. 2/3 để tập phát triển đủ
# rộng mà tập niêm phong vẫn đủ để nói được điều gì.
DEV_SHARE = 2 / 3


def build(cases: list[dict]) -> dict:
    by_family: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        by_family[case["family"]].append(case)

    gate = sorted(f for f in by_family if f in GATE_FAMILIES)
    rest = [f for f in by_family if f not in GATE_FAMILIES]
    # Tất định: nhiều ca trước (quyết định nặng đặt sớm), rồi theo tên.
    rest.sort(key=lambda f: (-len(by_family[f]), f))

    def signature(family: str) -> tuple[str, str]:
        cs = by_family[family]
        return (
            Counter(c["type"] for c in cs).most_common(1)[0][0],
            Counter(c["expect"]["kind"] for c in cs).most_common(1)[0][0],
        )

    dev: list[str] = []
    test: list[str] = []
    dev_sig: Counter = Counter()
    test_sig: Counter = Counter()
    dev_n = test_n = 0

    for family in rest:
        sig = signature(family)
        size = len(by_family[family])
        # Thiếu hụt của mỗi phía ở đúng chữ ký này, chuẩn hóa theo tỷ lệ mong muốn.
        dev_deficit = DEV_SHARE - (dev_sig[sig] / max(dev_sig[sig] + test_sig[sig], 1))
        test_deficit = (1 - DEV_SHARE) - (
            test_sig[sig] / max(dev_sig[sig] + test_sig[sig], 1)
        )
        if dev_sig[sig] + test_sig[sig] == 0:
            # Chữ ký mới: cho phía đang lệch xa tỷ lệ tổng thể nhất.
            total = max(dev_n + test_n, 1)
            choose_dev = (dev_n / total) < DEV_SHARE
        else:
            choose_dev = dev_deficit >= test_deficit
        if choose_dev:
            dev.append(family)
            dev_sig[sig] += size
            dev_n += size
        else:
            test.append(family)
            test_sig[sig] += size
            test_n += size

    return {
        "schema_version": 1,
        "method": (
            "Chia theo họ câu hỏi để không rò rỉ giữa hai tập; cân theo (loại câu hỏi, "
            "dạng đáp án) để tập phát triển dự báo được tập niêm phong. Tất định, không "
            "dùng số ngẫu nhiên — sinh lại bởi ai/evaluation/build_split.py."
        ),
        "gate_families": gate,
        "dev_families": sorted(dev),
        "test_families": sorted(test),
    }


def describe(cases: list[dict], split: dict) -> list[str]:
    """Bảng so thành phần ba nhóm, và các cảnh báo nếu chia lệch."""
    groups = {
        "chốt": set(split["gate_families"]),
        "phát triển": set(split["dev_families"]),
        "niêm phong": set(split["test_families"]),
    }
    lines: list[str] = []
    warnings: list[str] = []
    print(f"{'nhóm':12} {'ca':>4} {'họ':>3}  loại                dạng đáp án")
    for label, families in groups.items():
        cs = [c for c in cases if c["family"] in families]
        types = Counter(c["type"] for c in cs)
        kinds = Counter(c["expect"]["kind"] for c in cs)
        t = " ".join(f"{k}={types[k]}" for k in sorted(types))
        k = " ".join(f"{a}={b}" for a, b in sorted(kinds.items()))
        print(f"{label:12} {len(cs):>4} {len(families):>3}  {t:18}  {k}")
        lines.append(label)

    dev = [c for c in cases if c["family"] in groups["phát triển"]]
    test = [c for c in cases if c["family"] in groups["niêm phong"]]
    # Tập niêm phong quá nhỏ thì mọi con số trên nó là nhiễu.
    if len(test) < 12:
        warnings.append(f"tập niêm phong chỉ {len(test)} ca — quá nhỏ để kết luận")
    # Dạng đáp án chỉ có ở một phía thì phía kia không dự báo được nó.
    dev_kinds = {c["expect"]["kind"] for c in dev}
    test_kinds = {c["expect"]["kind"] for c in test}
    only_test = test_kinds - dev_kinds
    if only_test:
        warnings.append(
            f"dạng đáp án chỉ có ở tập niêm phong: {sorted(only_test)} — "
            "tập phát triển không dự báo được chúng"
        )
    # Chiều ngược ít nguy hại hơn nhưng vẫn là khoảng trống: tập niêm phong không đo
    # được dạng đó. Báo ra để nó không nằm ẩn, nhưng không chặn.
    only_dev = dev_kinds - test_kinds
    if only_dev:
        print(
            f"\nlưu ý: dạng đáp án chỉ có ở tập phát triển: {sorted(only_dev)} — "
            "tập niêm phong không đo được chúng"
        )
    overlap = set(split["dev_families"]) & set(split["test_families"])
    if overlap:
        warnings.append(f"họ nằm ở cả hai tập (rò rỉ): {sorted(overlap)}")
    return warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm, không ghi.")
    args = parser.parse_args(argv)

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))["cases"]
    split = build(cases)
    assigned = set(split["gate_families"]) | set(split["dev_families"]) | set(
        split["test_families"]
    )
    families = {c["family"] for c in cases}
    missing = families - assigned
    if missing:
        print(f"họ chưa được chia: {sorted(missing)}")
        return 2

    warnings = describe(cases, split)
    if warnings:
        print(f"\nCẢNH BÁO ({len(warnings)}):")
        for line in warnings:
            print(f"  - {line}")

    if args.check:
        print("\n--check: không ghi tệp nào.")
        return 1 if warnings else 0

    SPLIT_PATH.write_text(
        json.dumps(split, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nĐã ghi {SPLIT_PATH.name}")
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
