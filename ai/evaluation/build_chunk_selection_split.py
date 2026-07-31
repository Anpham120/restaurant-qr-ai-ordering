# -*- coding: utf-8 -*-
"""Chia tập chọn mục thành PHÁT TRIỂN và NIÊM PHONG, tất định.

    python ai/evaluation/build_chunk_selection_split.py
    python ai/evaluation/build_chunk_selection_split.py --check

Chia theo HỌ, không theo ca. Mỗi họ là một tài liệu, và hai dạng câu hỏi của cùng một mục nằm cùng
họ — nên chia theo ca sẽ để dạng A của một mục vào tập phát triển và dạng B của đúng mục đó vào tập
niêm phong. Lúc đó tập niêm phong không còn độc lập: cùng một đoạn văn, cùng một khóa đáp án.

Vì sao cần niêm phong ở đây
---------------------------
Tập này tồn tại để CHỌN bộ xếp hạng cho runtime. Nếu xem hết 168 ca rồi chọn cái thắng thì con số
thắng đó là con số đã dùng để chọn — nó không còn là ước lượng cho câu hỏi "bộ này sẽ làm tốt cỡ
nào trên câu chưa thấy".

Bài học đã trả giá một lần: tập niêm phong của bộ truy hồi toàn kho bị mở ngày 2026-07-30 để chốt
phép so, và từ đó mọi con số trên 40 ca đó không còn là held-out. Tập này mở đúng MỘT lần, và ngày
mở được ghi vào tệp chia.

Chia tất định bằng băm SHA-256 của tên họ, không dùng số ngẫu nhiên — cùng đầu vào cho cùng kết quả
trên mọi máy, và không cần lưu seed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
CASES_PATH = HERE / "chunk_selection_cases.json"
OUT_PATH = HERE / "chunk_selection_split.json"

# Tỷ lệ niêm phong. Chọn 1/3 vì tập chỉ có 13 họ: 1/4 cho ra 3 họ và một họ lệch là 33% của tập
# niêm phong. 1/3 cho ~4 họ, vẫn ít nhưng đủ để một kết luận "hơn rõ" không đảo chiều vì một ca.
#
# Con số này là điểm yếu ĐÃ BIẾT của tập, không phải một lựa chọn tối ưu: 13 họ là trần của kho.
NIEM_PHONG_MOI = 3  # 1 trong mỗi 3 họ


def bam(ten: str) -> int:
    return int(hashlib.sha256(ten.encode("utf-8")).hexdigest(), 16)


def build() -> dict:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))
    cases = data["cases"]
    hos = sorted({c["family"] for c in cases})

    # Họ `cs-derived-template` LUÔN vào tập phát triển, không bao giờ niêm phong.
    #
    # Vì sao tách riêng: nó là một quyết định lặp lại, nên nó không đại diện cho câu chưa thấy —
    # niêm phong nó là niêm phong một thứ ta đã biết câu trả lời. Và nếu nó rơi vào tập niêm phong
    # thì 48/168 ca của tập niêm phong là bản sao của nhau.
    DERIVED = "cs-derived-template"
    con_lai = [h for h in hos if h != DERIVED]

    niem_phong = sorted(h for h in con_lai if bam(h) % NIEM_PHONG_MOI == 0)
    phat_trien = sorted(set(con_lai) - set(niem_phong)) + [DERIVED]

    def dem(hs: list[str]) -> int:
        return sum(1 for c in cases if c["family"] in hs)

    return {
        "schema_version": 1,
        "authored": "Sinh bởi ai/evaluation/build_chunk_selection_split.py — đừng sửa tay.",
        "how": [
            "Chia theo HỌ (mỗi họ một tài liệu), băm SHA-256 tên họ, tất định.",
            "",
            "Chia theo họ chứ không theo ca: hai dạng câu hỏi của CÙNG một mục nằm cùng họ, nên chia",
            "theo ca sẽ để dạng A và dạng B của đúng một đoạn văn nằm ở hai tập — và lúc đó tập niêm",
            "phong không còn độc lập.",
            "",
            f"`{DERIVED}` LUÔN ở tập phát triển: nó là một quyết định lặp lại, nên niêm phong nó là",
            "niêm phong một thứ đã biết câu trả lời, và nó sẽ chiếm gần một phần ba tập niêm phong",
            "bằng những ca là bản sao của nhau.",
        ],
        "sealed_opened": True,
        "sealed_opened_date": "2026-07-30",
        "sealed_opened_note": (
            "Mở MỘT lần ngày 2026-07-30 để chốt bộ xếp hạng cho runtime. Kết quả trên 44 ca niêm "
            "phong, nhóm `written`, Top-1: bm25 0,750 · embedding 0,864 · hybrid 0,886. Riêng dạng "
            "B (diễn đạt khác): bm25 0,636 · embedding 0,818 · hybrid 0,818. "
            "Cùng chiều với tập phát triển (bm25 0,803 · embedding 0,921 · hybrid 0,908), nên kết "
            "luận 'embedding và hybrid hơn BM25' đứng được trên cả hai tập. "
            "Chênh lệch giữa embedding và hybrid đảo chiều giữa hai tập và luôn nhỏ hơn hai ca — "
            "dữ liệu này KHÔNG chọn được giữa hai cái đó. "
            "TỪ NAY con số trên 44 ca này không còn là held-out. Không sửa hệ thống theo chúng, và "
            "câu hỏi tiếp theo cần một tập MỚI."
        ),
        "dev_families": phat_trien,
        "test_families": niem_phong,
        "dev_cases": dem(phat_trien),
        "test_cases": dem(niem_phong),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    print(f"phát triển : {len(data['dev_families'])} họ / {data['dev_cases']} ca")
    print(f"niêm phong : {len(data['test_families'])} họ / {data['test_cases']} ca")
    print(f"  {data['test_families']}")

    if args.check:
        if not OUT_PATH.exists() or OUT_PATH.read_text(encoding="utf-8-sig") != text:
            print("\n--check: tệp khác kết quả sinh lại.")
            return 1
        print("\n--check: khớp.")
        return 0
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"\nĐã ghi {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
