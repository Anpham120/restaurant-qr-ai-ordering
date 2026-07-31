# -*- coding: utf-8 -*-
"""Hợp nhất hai bảng xếp hạng bằng RRF (Reciprocal Rank Fusion).

Công thức
---------
    RRF(d) = Σ_r  1 / (k + rank_r(d))          k = 60

`rank_r(d)` là hạng của đoạn d trong bảng của bộ truy hồi r, tính từ **1**. Đoạn không có trong
bảng nào thì không góp gì.

Vì sao hợp nhất theo HẠNG mà không theo ĐIỂM
-------------------------------------------
Điểm BM25 và điểm cosine không cùng thang: BM25 không có trần trên (nó là tổng theo từ, nên câu
hỏi dài cho điểm lớn hơn), còn cosine nằm trong [-1, 1]. Cộng thẳng thì BM25 áp đảo; chuẩn hóa
min-max thì kết quả phụ thuộc **đoạn tệ nhất trong danh sách** — thêm một đoạn rác vào cuối bảng
là đổi điểm của đoạn đầu bảng. Hạng thì không có hai vấn đề đó.

Cái giá của việc dùng hạng, và phải nói ra: RRF **bỏ hết thông tin về khoảng cách**. Một đoạn hơn
đoạn sau nó rất xa và một đoạn hơn sát sao đều chỉ là "hạng 1 so với hạng 2". Nên RRF mạnh khi hai
bộ truy hồi có thang điểm không so được, và yếu khi một bộ chắc chắn hơn bộ kia rất nhiều.

Vì sao k = 60
-------------
Giá trị trong bài gốc của Cormack và cộng sự (2009). Nó quyết định độ dốc: k nhỏ thì hạng 1 áp đảo
(k=1 -> 1/2 so với 1/3, tức hạng 1 nặng gấp 1,5 lần hạng 2), k lớn thì mọi hạng gần như bằng nhau
(k=60 -> 1/61 so với 1/62, chênh 1,6%). k=60 nghĩa là **đồng thuận giữa hai bộ quan trọng hơn thứ
tự trong từng bộ** — một đoạn hạng 3 ở cả hai bảng thắng một đoạn hạng 1 chỉ ở một bảng:

    hạng 3 ở cả hai   1/63 + 1/63 = 0,03175
    hạng 1 ở một bảng 1/61        = 0,01639

Không chỉnh k theo tập đánh giá, cùng lý do với `k1`/`b` của BM25.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import Hit

RRF_K = 60


@dataclass
class HybridRetriever:
    """Bọc nhiều bộ truy hồi, hợp nhất bảng của chúng bằng RRF.

    Nhận `depth` riêng cho từng bảng con: nếu chỉ lấy `k` đoạn từ mỗi bộ rồi hợp nhất thì một đoạn
    xếp hạng 6 ở cả hai bảng sẽ **không bao giờ** vào kết quả, dù đồng thuận ở hạng 6 là tín hiệu
    mạnh hơn hạng 1 lẻ loi. Lấy sâu hơn `k` là điều làm cho RRF có tác dụng — bản đầu của tôi lấy
    đúng `k` và hybrid gần như trùng khớp với BM25.
    """

    retrievers: list = field(default_factory=list)
    name: str = "hybrid"
    depth: int = 20
    k_rrf: int = RRF_K

    def scores(self, query: str) -> dict[str, float]:
        acc: dict[str, float] = {}
        for r in self.retrievers:
            for hit in r.search(query, k=self.depth):
                acc[hit.chunk_id] = acc.get(hit.chunk_id, 0.0) + 1.0 / (self.k_rrf + hit.rank)
        return acc

    def search(self, query: str, k: int = 5) -> list[Hit]:
        ranked = sorted(self.scores(query).items(), key=lambda kv: (-kv[1], kv[0]))
        return [Hit(cid, score, r) for r, (cid, score) in enumerate(ranked[:k], 1)]
