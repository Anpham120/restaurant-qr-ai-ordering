# -*- coding: utf-8 -*-
"""Truy hồi bằng embedding — xếp hạng theo Ý NGHĨA thay vì theo từ trùng.

Vì sao thư viện là TÙY CHỌN, không bắt buộc
------------------------------------------
`sentence-transformers` kéo theo `torch` và chiếm khoảng 2–3GB. Bước 5 của dự án đã **bỏ** nhóm
thư viện đó sau khi đo rằng 24 chủ đề không cần xếp hạng theo độ tương đồng, và ảnh Docker giảm
tương ứng. Đưa lại vào `ai/requirements.txt` là quyết định phải **có số mới được làm**:

    nếu embedding thắng rõ trên tập đánh giá   -> đưa vào, ghi rõ cái giá 2–3GB
    nếu không                                  -> KHÔNG đưa vào, và nói ra vì sao

Nên tệp này import "mềm": thiếu thư viện thì `available()` trả False và phép so chạy tiếp với hai
phương pháp còn lại, có ghi rõ là đã bỏ qua. **Bỏ qua âm thầm mới là điều cấm** — một phép so báo
"BM25 thắng" mà thực ra chưa từng chạy embedding là con số dối.

Mô hình nào, và vì sao
---------------------
`intfloat/multilingual-e5-small` — 384 chiều, có tiếng Việt, ~120MB. Họ E5 đòi **tiền tố**:

    "query: ..."     cho câu hỏi
    "passage: ..."   cho đoạn trong kho

Thiếu tiền tố thì mô hình vẫn chạy và vẫn trả vector — chỉ kém đi. Đây là loại lỗi tệ nhất của
phần này: không có thông báo nào, chỉ có điểm thấp hơn mà không ai biết vì sao. Nên `test_rag.py`
có ca chốt rằng tiền tố được thêm.

Chuẩn hóa vector là bắt buộc với cosine
--------------------------------------
Sau chuẩn hóa L2 thì `cosine(a,b) = a·b`, nên phép so chỉ còn một phép nhân ma trận. Không chuẩn
hóa mà vẫn lấy tích vô hướng thì đoạn DÀI được lợi thế chỉ vì vector nó dài hơn — và
`run_retrieval_comparison.py --ablation` đo đúng mức mất đó.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .base import Hit

MODEL_NAME = "intfloat/multilingual-e5-small"
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

_LOAD_ERROR: str | None = None


def available() -> bool:
    """Có chạy được embedding không. KHÔNG nạp mô hình — chỉ kiểm thư viện có mặt."""
    global _LOAD_ERROR
    try:
        import sentence_transformers  # noqa: F401
    except Exception as exc:  # ImportError, và cả lỗi khi torch cài dở
        _LOAD_ERROR = f"{type(exc).__name__}: {exc}"
        return False
    return True


def why_unavailable() -> str:
    return _LOAD_ERROR or "chưa kiểm"


@dataclass
class EmbeddingIndex:
    """Vector của từng đoạn, đã chuẩn hóa L2.

    Giữ vector dưới dạng `list[list[float]]` chứ không phải mảng numpy: numpy nằm trong nhóm thư
    viện đã bỏ, và phần này phải chạy được khi chỉ có `sentence-transformers` (nó tự kéo numpy,
    nhưng mã ở đây không phụ thuộc vào việc đó). Với 303 đoạn × 384 chiều thì Python thuần đủ
    nhanh, và độ trễ được ĐO chứ không đoán.
    """

    name: str = "embedding"
    chunk_ids: list[str] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)
    normalize: bool = True
    use_prefix: bool = True
    _model: object = None

    @staticmethod
    def _l2(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else list(vec)

    @classmethod
    def build(cls, chunks, *, normalize: bool = True, use_prefix: bool = True) -> "EmbeddingIndex":
        from sentence_transformers import SentenceTransformer

        index = cls(normalize=normalize, use_prefix=use_prefix)
        index._model = SentenceTransformer(MODEL_NAME)
        index.chunk_ids = [c.chunk_id for c in chunks]
        texts = [
            (PASSAGE_PREFIX if use_prefix else "") + c.text for c in chunks
        ]
        raw = index._model.encode(texts, batch_size=32, show_progress_bar=False)
        index.vectors = [
            index._l2(list(map(float, v))) if normalize else list(map(float, v)) for v in raw
        ]
        return index

    def _encode_query(self, query: str) -> list[float]:
        text = (QUERY_PREFIX if self.use_prefix else "") + query
        vec = list(map(float, self._model.encode([text], show_progress_bar=False)[0]))
        return self._l2(vec) if self.normalize else vec

    def scores(self, query: str) -> dict[str, float]:
        q = self._encode_query(query)
        return {
            cid: sum(a * b for a, b in zip(q, v))
            for cid, v in zip(self.chunk_ids, self.vectors)
        }

    def search(self, query: str, k: int = 5) -> list[Hit]:
        """`k` đoạn giống nhất.

        Khác BM25 ở một điểm quan trọng cho phép so: embedding **luôn** cho điểm cho MỌI đoạn, nên
        nó luôn trả về đủ `k` đoạn dù câu hỏi ngoài phạm vi hoàn toàn. BM25 trả về rỗng khi không
        chung từ nào. Đó là lý do `forbidden@5` và họ `kb-out-of-scope` là chỉ số quan trọng hơn
        Hit@5: một bộ luôn trả 5 đoạn không bao giờ "trượt", nó chỉ trả sai.
        """
        ranked = sorted(self.scores(query).items(), key=lambda kv: (-kv[1], kv[0]))
        return [Hit(cid, score, r) for r, (cid, score) in enumerate(ranked[:k], 1)]
