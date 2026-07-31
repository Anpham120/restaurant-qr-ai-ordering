# -*- coding: utf-8 -*-
"""Tính sẵn vector của kho tri thức, gọi lúc BUILD ảnh Docker.

    python -m rag.precompute            # cần AI_EMBEDDING_CACHE trỏ vào tệp đích

Vì sao là một mô-đun chứ không phải một dòng `python -c` trong Dockerfile
------------------------------------------------------------------------
Bản đầu là một biểu thức inline trong Dockerfile, và nó đã sai theo cách im lặng nhất có thể: nó gọi
`retrievable_chunks(...)` (425 đoạn) trong khi lúc chạy hệ thống xếp hạng tập ĐÃ LỌC `heading`. Hai
tập khác nhau -> hàm băm nội dung khác nhau -> đệm không khớp -> **tính lại toàn bộ mỗi lần khởi
động**, 60 giây, trong khi log build in "đã ghi ... cho 425 đoạn" và mọi dấu hiệu nói là đã có đệm.

Đệm làm đúng thiết kế (khóa lệch thì tính lại, tuyệt đối không dùng vector sai), nên nó im lặng làm
điều đúng và che mất việc nó chưa từng được dùng. Chỉ đo thời gian khởi động thật mới thấy.

Một mô-đun sửa được điều đó bằng CẤU TRÚC: nó gọi `doan_toan_kho()` — cùng hàm mà `answer.py` gọi —
nên hai bên không thể lệch nữa. Dockerfile chỉ còn `python -m rag.precompute`, không còn chỗ để viết
lại phép lọc.

Vì sao in ra số đoạn và hàm băm
------------------------------
Bước build phải để lại dấu vết ĐỐI CHIẾU ĐƯỢC với lúc chạy. Nếu sau này khởi động vẫn chậm thì so
hai con số này với con số lúc chạy là biết ngay đệm có khớp hay không, thay vì phải đoán.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Chạy được cả khi `ai/app` chưa ở trong `sys.path` (Dockerfile gọi từ `/app`).
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from rag.chunker import doan_toan_kho  # noqa: E402
from rag.embedding import _khoa, PASSAGE_PREFIX, ghi_dem  # noqa: E402

KNOWLEDGE = _HERE.parents[1] / "knowledge"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]) if argv else KNOWLEDGE

    if not os.environ.get("AI_EMBEDDING_CACHE"):
        print(
            "Chưa đặt AI_EMBEDDING_CACHE. Không tự chọn đường dẫn mặc định: ghi vào một chỗ đoán ra "
            "thì lúc chạy đọc chỗ khác, và hậu quả là im lặng mã hóa lại mỗi lần khởi động."
        )
        return 2

    doan = doan_toan_kho(root)
    if not doan:
        print(f"Kho rỗng ở {root} — không có gì để tính. Đây là lỗi, không phải trường hợp bình thường.")
        return 1

    duong = ghi_dem(doan)
    texts = [PASSAGE_PREFIX + c.text for c in doan]
    print(f"đã ghi {duong}")
    print(f"  số đoạn : {len(doan)}")
    print(f"  khóa    : {_khoa(texts, normalize=True, use_prefix=True)[:16]}…")
    print("  Lúc chạy `answer.py` phải in đúng hai con số này, nếu không thì đệm KHÔNG được dùng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
