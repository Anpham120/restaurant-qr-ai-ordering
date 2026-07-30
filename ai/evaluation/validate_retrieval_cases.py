# -*- coding: utf-8 -*-
"""Bộ kiểm tập đánh giá truy hồi — bắt ca viết sai TRƯỚC khi ai đó đo bằng nó.

Vì sao tập đánh giá cần bộ kiểm riêng
-------------------------------------
Một ca viết sai không làm chương trình lỗi. Nó chỉ lặng lẽ **luôn xanh** hoặc **luôn đỏ**, và cả
hai đều tệ hơn không có ca:

    luôn xanh   khóa đáp án đòi "mọi đoạn" -> mọi bộ truy hồi đều qua
    luôn đỏ     khóa đáp án trỏ vào chỗ không tồn tại -> người ta học cách bỏ qua ca đó

Bản cũ có **96 khóa đáp án trỏ sai chỗ** suốt nhiều tháng. Bộ kiểm này tồn tại để việc đó thành
lỗi thấy được.

Chín loại lỗi, mỗi loại một phép kiểm
-------------------------------------
1. thiếu trường bắt buộc
2. mã ca trùng
3. câu hỏi trùng (hai ca cùng câu -> một trong hai là dư)
4. điều kiện `expected` giải ra 0 đoạn (khóa trỏ vào chỗ không tồn tại)
5. điều kiện `forbidden` giải ra 0 đoạn (điều kiện vô nghĩa, luôn thỏa)
6. `expected` và `forbidden` GIAO NHAU (ca tự mâu thuẫn — không bộ nào qua được)
7. `expect_nothing` mà vẫn có `expected` (mâu thuẫn)
8. `expected` đòi quá nhiều đoạn (>1/3 kho -> "đúng" mất ý nghĩa)
9. thiếu `why` hoặc `why` quá ngắn để nói được lý do

Loại 6 là loại tinh nhất: nó xảy ra khi hai điều kiện dùng cách chọn khác nhau nhưng trỏ vào cùng
đoạn — không ai phát hiện bằng cách đọc, chỉ phát hiện bằng cách GIẢI cả hai rồi so.

    python ai/evaluation/validate_retrieval_cases.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from chunk_selectors import SelectorError, corpus, describe, select_chunk_ids, select_many  # noqa: E402

CASES_PATH = HERE / "retrieval_cases.json"

REQUIRED = ("id", "family", "query", "expected", "forbidden", "expect_nothing", "why")

# Trần cho `expected`. Một ca đòi nửa kho là ca không phân biệt được gì — mọi bộ truy hồi đều
# "đúng". 1/3 chọn theo cùng lối nghĩ với `MAX_ITEMS_IN_LIST` của thước đo câu trả lời: đủ rộng cho
# ca hợp lệ nhiều đoạn (`kb-multi-topic` đòi hai chủ đề) mà vẫn chặn ca vô nghĩa.
MAX_EXPECTED_SHARE = 1 / 3

MIN_WHY_WORDS = 8


def check(cases: list[dict]) -> list[str]:
    problems: list[str] = []
    tong_doan = len(corpus())
    tran = int(tong_doan * MAX_EXPECTED_SHARE)

    seen_id: dict[str, str] = {}
    seen_query: dict[str, str] = {}

    for case in cases:
        cid = case.get("id", "<thiếu id>")

        # 1. thiếu trường
        thieu = [k for k in REQUIRED if k not in case]
        if thieu:
            problems.append(f"{cid}: thiếu trường {thieu}")
            continue

        # 2. mã trùng
        if cid in seen_id:
            problems.append(f"{cid}: mã ca trùng")
        seen_id[cid] = cid

        # 3. câu hỏi trùng
        q = case["query"].strip().lower()
        if q in seen_query:
            problems.append(
                f"{cid}: câu hỏi trùng với {seen_query[q]} — một trong hai ca là dư"
            )
        seen_query[q] = cid

        # 9. why
        if len(case["why"].split()) < MIN_WHY_WORDS:
            problems.append(
                f"{cid}: `why` chỉ {len(case['why'].split())} từ. Ca không nói được LÝ DO thì "
                "người sau không biết nó chốt điều gì, và sẽ nới nó khi nó đỏ"
            )

        # 4, 5. điều kiện giải ra 0 đoạn
        try:
            exp = select_many(case["expected"]) if case["expected"] else set()
            for sel in case["forbidden"]:
                if not select_chunk_ids(sel):
                    problems.append(
                        f"{cid}: forbidden {describe(sel)} — điều kiện vô nghĩa, nó LUÔN thỏa"
                    )
            for sel in case["expected"]:
                if not select_chunk_ids(sel):
                    problems.append(
                        f"{cid}: expected {describe(sel)} — khóa đáp án trỏ vào chỗ không tồn tại"
                    )
            forb = select_many(case["forbidden"]) if case["forbidden"] else set()
        except SelectorError as exc:
            problems.append(f"{cid}: điều kiện chọn viết sai — {exc}")
            continue

        # 6. giao nhau
        giao = exp & forb
        if giao:
            problems.append(
                f"{cid}: expected và forbidden GIAO NHAU ở {len(giao)} đoạn "
                f"({sorted(giao)[:2]}) — ca tự mâu thuẫn, không bộ truy hồi nào qua được"
            )

        # 7. expect_nothing mâu thuẫn
        if case["expect_nothing"] and case["expected"]:
            problems.append(f"{cid}: `expect_nothing` nhưng vẫn có `expected` — mâu thuẫn")
        if not case["expect_nothing"] and not case["expected"]:
            problems.append(
                f"{cid}: không có `expected` mà `expect_nothing` là false — ca không đòi gì cả"
            )

        # 8. quá rộng
        if len(exp) > tran:
            problems.append(
                f"{cid}: expected đòi {len(exp)}/{tong_doan} đoạn (trần {tran}) — ca đòi quá "
                "nhiều thì mọi bộ truy hồi đều 'đúng' và ca không phân biệt được gì"
            )

    return problems


def main() -> int:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))
    cases = data["cases"]
    problems = check(cases)

    ho = collections.Counter(c["family"] for c in cases)
    rong = sum(1 for c in cases if c.get("expect_nothing"))
    print(f"ca                : {len(cases)}")
    print(f"họ                : {len(ho)}")
    print(f"expect_nothing    : {rong}")
    print(f"đoạn trong chỉ mục: {len(corpus())}")
    print(f"trần expected     : {int(len(corpus()) * MAX_EXPECTED_SHARE)} đoạn")

    if problems:
        print(f"\nVẤN ĐỀ ({len(problems)}):")
        for p in problems[:20]:
            print(f"  - {p}")
        return 1
    print("\nKhông có vấn đề.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
