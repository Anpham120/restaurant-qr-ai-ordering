# -*- coding: utf-8 -*-
"""Giao diện chung cho ba cách truy hồi, và phần duy nhất cả ba dùng chung: cách tách từ.

Vì sao giao diện chỉ có `search(query, k)`
-----------------------------------------
Bản cũ trộn `RetrievalFilters` vào cùng lớp với phép xếp hạng, nên không ai nói được một đoạn
lên đầu vì **nó liên quan** hay vì **các đoạn khác bị lọc mất**. Hai chuyện đó cần đo riêng: lọc
là phép quyết định (đúng/sai), xếp hạng là phép so (tốt hơn/kém hơn). Gộp lại thì phép so mất
nghĩa.

Nên ở đây bộ truy hồi **chỉ** xếp hạng. Không lọc, không ngưỡng, không hậu xử lý.

Vì sao dùng chung `fold` với phần hiểu câu hỏi
---------------------------------------------
`understand.fold` rút dấu, hạ chữ thường và bỏ dấu câu. Nếu truy hồi tự viết một hàm tách từ
khác thì hai phần của cùng hệ thống sẽ có hai định nghĩa "cùng một từ" — và câu "mấy giờ mở cửa?"
khớp được ở một phần mà không khớp ở phần kia. Dùng chung là cách duy nhất để phép so BM25 với
embedding nói về cùng một tập từ.

Rút dấu là quyết định có đánh đổi, và nó ĐO ĐƯỢC: `run_retrieval_comparison.py --ablation` tắt
rút dấu rồi báo mức mất. Người Việt gõ không dấu rất thường, nên rút dấu là điều kiện để "mo cua"
khớp "mở cửa"; cái mất là "muối" và "muôi" thành cùng một từ.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# `understand.py` nằm ở `ai/app`, còn tệp này ở `ai/app/rag`. Dịch vụ chạy với `--app-dir app` nên
# `ai/app` đã ở trên `sys.path`; công cụ đánh giá thì import trực tiếp nên phải tự thêm.
_APP_DIR = str(Path(__file__).resolve().parents[1])
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from understand import fold  # noqa: E402

# Từ quá ngắn sau khi rút dấu gần như không mang thông tin phân biệt, nhưng KHÔNG bỏ chúng:
# "bò", "gà", "mì", "ốc" đều là 2 ký tự và đều là từ khóa quan trọng nhất của thực đơn này. Bản
# đầu của tôi bỏ từ dưới 3 ký tự và làm mất đúng những từ đó.
MIN_TOKEN_LEN = 1


def tokenize(text: str) -> list[str]:
    """Tách từ cho cả BM25 và embedding. Một định nghĩa, không hai."""
    return [t for t in fold(text).split() if len(t) >= MIN_TOKEN_LEN]


@dataclass(frozen=True)
class Hit:
    """Một đoạn được lấy, kèm điểm và hạng.

    `rank` bắt đầu từ 1, không từ 0: công thức RRF là `1/(k + rank)`, và rank 0 làm mẫu số của
    đoạn đầu bảng nhỏ hơn hẳn phần còn lại — sai lệch âm thầm mà kết quả vẫn "trông hợp lý".
    """

    chunk_id: str
    score: float
    rank: int


class Retriever(Protocol):
    """Ba cách truy hồi cùng hình dạng này, nên phép so không phụ thuộc cách cài đặt."""

    name: str

    def search(self, query: str, k: int = 5) -> list[Hit]:
        ...
