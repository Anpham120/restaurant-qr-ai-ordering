# -*- coding: utf-8 -*-
"""BM25 Okapi — xếp hạng đoạn theo trùng TỪ. Chỉ dùng thư viện chuẩn.

Công thức, viết ra để kiểm được bằng tay
---------------------------------------
Với truy vấn Q và đoạn D:

    score(D, Q) = Σ_{t ∈ Q}  IDF(t) · ( f(t,D) · (k1 + 1) )
                                      ------------------------------------
                                      f(t,D) + k1 · (1 - b + b · |D|/avgdl)

    IDF(t) = ln( 1 + (N - n(t) + 0.5) / (n(t) + 0.5) )

    f(t,D)  số lần t xuất hiện trong D        n(t)  số đoạn chứa t
    |D|     độ dài đoạn (số từ)               N     tổng số đoạn
    avgdl   độ dài trung bình

`k1 = 1.5` và `b = 0.75` là giá trị mặc định của tài liệu gốc Robertson/Sparck-Jones. Chúng KHÔNG
được chỉnh theo tập đánh giá: chỉnh tham số theo tập rồi báo kết quả trên cùng tập đó là tự lừa,
và tập niêm phong ở đây chỉ được mở một lần nên không có chỗ để chỉnh.

Dạng IDF nào, và vì sao dạng này
--------------------------------
Dạng `ln(1 + (N - n + 0.5)/(n + 0.5))` luôn dương. Dạng gốc `ln((N - n + 0.5)/(n + 0.5))` cho IDF
**âm** khi một từ xuất hiện ở hơn nửa số đoạn — và điểm âm nghĩa là chứa từ đó làm đoạn TỤT hạng.
Với kho này thì đó không phải chuyện lý thuyết: chữ "món" và "nhà hàng" có ở gần như mọi đoạn.

Điều BM25 KHÔNG làm được, và phải nói ra trước khi đo
----------------------------------------------------
Nó chỉ đếm từ trùng. Nên nó không hiểu:

    số        "món nào dưới 50.000đ" — "50.000" là một từ, không phải một lượng
    diễn đạt  "quán mở lúc nào" so với "giờ mở cửa" — không chung từ nào ngoài "mo"
    phủ định  "món KHÔNG cay" và "món cay" cho điểm gần như nhau

Ba điều này là lý do phép so với embedding có nghĩa, và là lý do tập đánh giá có họ `kb-number`.
"""
from __future__ import annotations

import collections
import math
from dataclasses import dataclass, field

from .base import Hit, tokenize

# Tham số gốc của BM25. Không chỉnh theo tập đánh giá — xem docstring.
K1 = 1.5
B = 0.75


@dataclass
class Bm25Index:
    """Chỉ mục BM25 dựng một lần rồi tra nhiều lần.

    Dựng chỉ mục là O(tổng số từ), tra là O(số từ truy vấn × số đoạn chứa từ đó) nhờ chỉ mục
    nghịch đảo — nên nó KHÔNG quét cả kho mỗi lần tra. Với 303 đoạn thì quét cả kho cũng nhanh,
    nhưng chỉ mục nghịch đảo là điều làm cho con số độ trễ nói được điều gì về quy mô lớn hơn.
    """

    name: str = "bm25"
    chunk_ids: list[str] = field(default_factory=list)
    doc_len: list[int] = field(default_factory=list)
    avgdl: float = 0.0
    # từ -> [(chỉ số đoạn, số lần xuất hiện)]
    postings: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)

    @classmethod
    def build(cls, chunks) -> "Bm25Index":
        """`chunks` là bất kỳ dãy vật có `.chunk_id` và `.text`."""
        index = cls()
        postings: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)

        for i, chunk in enumerate(chunks):
            tokens = tokenize(chunk.text)
            index.chunk_ids.append(chunk.chunk_id)
            index.doc_len.append(len(tokens))
            for term, freq in collections.Counter(tokens).items():
                postings[term].append((i, freq))

        n = len(index.chunk_ids)
        index.avgdl = (sum(index.doc_len) / n) if n else 0.0
        index.postings = dict(postings)
        index.idf = {
            term: math.log(1 + (n - len(pl) + 0.5) / (len(pl) + 0.5))
            for term, pl in postings.items()
        }
        return index

    def scores(self, query: str) -> dict[str, float]:
        """Điểm thô cho mọi đoạn có điểm khác 0. Đoạn không chung từ nào thì KHÔNG có trong dict.

        Trả về dict thưa chứ không phải mảng đầy: đoạn 0 điểm và đoạn không xuất hiện là hai
        chuyện khác nhau khi hợp nhất với embedding, và hợp nhất là chỗ dễ lẫn hai thứ đó.
        """
        acc: dict[int, float] = collections.defaultdict(float)
        for term in tokenize(query):
            postings = self.postings.get(term)
            if not postings:
                continue
            idf = self.idf[term]
            for i, freq in postings:
                norm = K1 * (1 - B + B * self.doc_len[i] / self.avgdl) if self.avgdl else K1
                acc[i] += idf * (freq * (K1 + 1)) / (freq + norm)
        return {self.chunk_ids[i]: s for i, s in acc.items()}

    def search(self, query: str, k: int = 5) -> list[Hit]:
        """`k` đoạn điểm cao nhất.

        Phá thế bằng `chunk_id` khi điểm bằng nhau. Không phá thế thì thứ tự phụ thuộc thứ tự
        chèn vào dict, và hai lần chạy trên hai phiên bản Python có thể ra hai bảng khác nhau —
        con số đo được sẽ không lặp lại.
        """
        ranked = sorted(self.scores(query).items(), key=lambda kv: (-kv[1], kv[0]))
        return [Hit(cid, score, r) for r, (cid, score) in enumerate(ranked[:k], 1)]
