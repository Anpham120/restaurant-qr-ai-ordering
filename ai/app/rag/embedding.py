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


_MODEL_CACHE: dict[str, object] = {}


def _load_model():
    """Nạp mô hình MỘT lần cho cả tiến trình.

    Bản trước gọi `SentenceTransformer(MODEL_NAME)` trong mỗi `build()`. Điều đó không lộ ra vì bộ so
    trên toàn kho dựng đúng MỘT chỉ mục — nhưng bài toán chọn mục trong tài liệu dựng một chỉ mục cho
    MỖI tài liệu, và 18 tài liệu × 2 phương pháp = 36 bản mô hình trong một tiến trình. Kết quả:
    **segfault**, không phải chậm.

    Một triển khai thật cũng phải nạp một lần lúc khởi động, nên đây là sửa đúng chỗ chứ không phải
    một mẹo để phép đo chạy được.
    """
    if MODEL_NAME not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer

        _MODEL_CACHE[MODEL_NAME] = SentenceTransformer(MODEL_NAME)
    return _MODEL_CACHE[MODEL_NAME]


# --------------------------------------------------------------- vector tính sẵn lúc build
#
# Vì sao cần: ĐO ĐƯỢC, không phải phỏng đoán
# ------------------------------------------
# Đo trong container thật, từ lúc container `StartedAt` tới lúc uvicorn nhận request:
#
#     import torch          2,2s
#     nạp mô hình          10,6s
#     đọc 425 đoạn          0,0s
#     MÃ HÓA 425 đoạn      61,7s   <- 64% của cả thời gian khởi động
#     ------------------------------
#     khởi động thật       97,3s
#
# 61,7 giây đó tính đi tính lại **cùng một kết quả** mỗi lần container khởi động, vì kho tri thức
# nằm CỐ ĐỊNH trong ảnh. Nên nó thuộc lúc build, không thuộc lúc chạy.
#
# 97 giây khởi động còn có hậu quả thứ hai, tệ hơn chậm: `HEALTHCHECK` của Dockerfile đặt
# `start_period=15s`, `interval=30s`, `retries=3`. Nghĩa là lần kiểm thứ ba rơi vào ~105 giây — dịch
# vụ này kịp sẵn sàng ở 97 giây, tức **suýt** bị đánh `unhealthy`. Và `api` có
# `depends_on: ai-service: condition: service_healthy`, nên một máy chậm hơn 8% làm cả stack không
# lên. Đây là loại lỗi chỉ chạy thật mới thấy.
#
# Vì sao khóa là HÀM BĂM NỘI DUNG, không phải tên tệp hay ngày sửa
# ---------------------------------------------------------------
# Vector lệch khỏi kho là lỗi IM LẶNG và nặng nhất có thể ở đây: hệ thống vẫn trả 5 đoạn, vẫn có
# điểm, chỉ trả SAI đoạn — và không log nào nói gì. Nên khóa phải là chính nội dung đã mã hóa.
#
# Băm cả `normalize` và `use_prefix`: hai cờ đó ĐỔI vector. Thiếu chúng trong khóa thì phép ablation
# "tắt chuẩn hóa" sẽ lặng lẽ đọc lại vector ĐÃ chuẩn hóa và báo rằng tắt nó không mất gì — một phép
# đo tự bác bỏ chính nó.
_DEM_PATH_ENV = "AI_EMBEDDING_CACHE"


def _khoa(texts: list[str], *, normalize: bool, use_prefix: bool) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(f"{MODEL_NAME}|{normalize}|{use_prefix}|{len(texts)}\n".encode("utf-8"))
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _duong_dem():
    import os
    from pathlib import Path

    p = os.environ.get(_DEM_PATH_ENV)
    return Path(p) if p else None


def doc_dem(texts: list[str], *, normalize: bool, use_prefix: bool):
    """Vector đã tính sẵn, hoặc `None`.

    Trả `None` — tức tính lại — trong MỌI trường hợp không chắc chắn: không có biến môi trường,
    không có tệp, khóa không khớp, tệp hỏng. Không có nhánh nào "dùng tạm" một bộ vector không khớp.
    """
    path = _duong_dem()
    if path is None or not path.exists():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if data.get("khoa") != _khoa(texts, normalize=normalize, use_prefix=use_prefix):
        return None
    vecs = data.get("vectors")
    if not isinstance(vecs, list) or len(vecs) != len(texts):
        return None
    return vecs


def ghi_dem(chunks, *, normalize: bool = True, use_prefix: bool = True) -> str:
    """Tính vector rồi ghi ra tệp đệm. Gọi lúc BUILD, không lúc chạy.

    Trả về đường dẫn đã ghi, để bước build in ra được.
    """
    path = _duong_dem()
    if path is None:
        raise RuntimeError(
            f"Chưa đặt {_DEM_PATH_ENV}. Không tự chọn đường dẫn mặc định: ghi vào một chỗ đoán ra "
            "thì lúc chạy đọc chỗ khác, và hậu quả là im lặng tính lại 61 giây mỗi lần khởi động "
            "trong khi mọi người tin là đã có đệm."
        )
    import json

    model = _load_model()
    texts = [(PASSAGE_PREFIX if use_prefix else "") + c.text for c in chunks]
    raw = model.encode(texts, batch_size=32, show_progress_bar=False)
    vectors = [
        EmbeddingIndex._l2(list(map(float, v))) if normalize else list(map(float, v)) for v in raw
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "khoa": _khoa(texts, normalize=normalize, use_prefix=use_prefix),
                "mo_hinh": MODEL_NAME,
                "so_doan": len(texts),
                "vectors": vectors,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return str(path)


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

    # Vector đến từ đệm tính sẵn lúc build, hay vừa được mã hóa lại?
    #
    # Trường này tồn tại vì lỗi đệm-không-khớp là IM LẶNG: hệ thống vẫn đúng, chỉ chậm thêm 60 giây
    # mỗi lần khởi động, và cách duy nhất phát hiện là bấm giờ container. Một cờ đọc được qua
    # `/ready` biến nó thành thứ nhìn thấy ngay — cùng lý do `/ready` phải báo `model_key_set` thay
    # vì chỉ báo `model_configured`.
    tu_dem: bool = False
    _model: object = None

    @staticmethod
    def _l2(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else list(vec)

    @classmethod
    def build(cls, chunks, *, normalize: bool = True, use_prefix: bool = True) -> "EmbeddingIndex":
        index = cls(normalize=normalize, use_prefix=use_prefix)
        index._model = _load_model()
        index.chunk_ids = [c.chunk_id for c in chunks]
        texts = [
            (PASSAGE_PREFIX if use_prefix else "") + c.text for c in chunks
        ]

        # Đọc vector đã tính sẵn nếu có VÀ khớp kho. Xem `doc_dem`/`ghi_dem` để biết vì sao.
        dem = doc_dem(texts, normalize=normalize, use_prefix=use_prefix)
        if dem is not None:
            index.vectors = dem
            index.tu_dem = True
            return index

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
