# -*- coding: utf-8 -*-
"""Trả lời khách chỉ bằng cách tra thực đơn — không dùng mô hình sinh nào.

Vì sao bước này đứng trước mô hình
----------------------------------
Bản cũ có 8 đường xử lý tất định chồng lên nhau, và chỉ 33% câu trả lời do mã sinh ra —
phần còn lại phụ thuộc mô hình. Không ai nói được đường nào phụ trách việc gì, và hai
đường bị một cờ legacy tắt mà hệ thống vẫn hoạt động đúng.

Ở đây làm ngược lại: dựng phần tra bảng **trước**, đo xem nó trả lời được bao nhiêu, rồi
mới biết mô hình còn phải làm gì. Con số đó là số nền, và nó có hai tính chất mà câu trả
lời của mô hình không có: **đúng 100% về dữ liệu** và **giống nhau mọi lần chạy**.

Sáu nhánh, mỗi nhánh một việc
-----------------------------
Không có nhánh nào chồng nhánh nào, và thứ tự là thứ tự loại trừ:

1. ngoài bài toán      -> từ chối ngắn gọn
2. câu chính sách      -> nói thẳng chưa có dữ liệu
3. hỏi giá một món     -> nêu giá
4. so sánh hai món     -> nêu dữ kiện cả hai
5. món đắt/rẻ nhất     -> tính rồi nêu
6. còn lại             -> lọc thực đơn theo ràng buộc

Nhánh 6 sinh ra câu hỏi lại khi khách chưa nói gì đủ để lọc. Hỏi lại là câu trả lời đúng
ở đó, không phải thất bại.
"""
from __future__ import annotations

import re

from dataclasses import dataclass, field, replace

from pathlib import Path

from rag.chunker import KnowledgeError, verbatim_answers
from understand import DRINK_CATEGORIES, FOOD_CATEGORIES, Request

# Kho tri thức nằm TRONG `ai/`, nên nó luôn có mặt trong ảnh Docker. Trước đây nó là
# `backend/data/restaurant-facts.json`, ngoài phạm vi `COPY` của `ai/Dockerfile` — nên trong
# container mọi chủ đề chính sách trả "chưa có dữ liệu", im lặng. Xem `test_packaging.py`.
KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / "knowledge"


def load_facts() -> dict[str, str]:
    """Sự thật về nhà hàng theo chủ đề, trả NGUYÊN VĂN — mô hình không chạm vào chữ.

    Nguồn là các tài liệu `answer_mode: verbatim` trong `ai/knowledge/`. Kho tri thức có hai
    chế độ trả lời, và đây là chế độ tin mô hình **0%**:

        verbatim    giờ mở cửa, cách thanh toán, phụ phí, cách khai dị ứng — thông tin KHÔNG
                    được phép diễn đạt lại. Một chữ số lệch ở đây là sai sự thật về nhà hàng.
        synthesize  nội dung dài nhiều mặt, là đầu vào cho mô hình viết. Không đi qua hàm này.

    Ở đây truy hồi là **tra khóa**: chủ đề đã nhận ra ở bước hiểu câu hỏi chính là khóa. Không
    xếp hạng, không ngưỡng tương đồng, nên không có chỗ nào để chệch.

    Kho hỏng thì coi như chưa có — trả `{}` và hệ thống nói chưa có dữ liệu rồi chuyển nhân
    viên. Không được để một tài liệu viết sai làm sập luồng trả lời khách.
    """
    try:
        return verbatim_answers(KNOWLEDGE_PATH)
    except (KnowledgeError, OSError):
        return {}

# Số món nêu ra trong một câu liệt kê. Thước đo chặn ở 12 món ("đổ cả thực đơn ra không
# phải tư vấn"), còn ca đòi nhiều nhất là 5 món — nên 6 vừa đủ rộng mà vẫn gọn.
LIST_SIZE = 6

STAFF_NOTE = "Bạn nhắc nhân viên khi gọi món để bếp xác nhận lại giúp nhé."


@dataclass
class Reply:
    """Cùng hình dạng với `Answer` của thước đo, để chấm được trực tiếp."""

    text: str
    items: list[str] = field(default_factory=list)
    kind: str = "list"
    asks_back: bool = False
    branch: str = ""
    notes: list[str] = field(default_factory=list)


def money(value: int) -> str:
    return f"{value:,}".replace(",", ".") + "đ"


def phrase(item: dict) -> str:
    return f"{item['name']} ({money(item['price'])})"


def listing(items: list[dict]) -> str:
    return ", ".join(phrase(i) for i in items)


# Nhãn `party:*` đọc được cho khách. Nhóm này phủ 91/91 món và nó CHÍNH LÀ khẩu phần — xem chú
# thích ở `understand.py` về việc chủ đề `serving_size` bị bỏ.
#
# Chỉ ba nhãn dưới đây nói về SỐ NGƯỜI. `party:share`, `party:friends`, `party:family` nói về DỊP
# ĂN, không nói khẩu phần — trộn chúng vào thì câu trả lời thành "món này cho gia đình người ăn".
# Tên tiếng Việt của nhãn dị nguyên và độ cay, để câu trả lời NÓI RA thuộc tính khách hỏi.
#
# Vì sao cần: câu "Ốc hương rang bơ tỏi có sữa không?" từng nhận "thực đơn có ghi nhận thành phần
# bạn cần tránh trong Ốc hương rang bơ tỏi" — đúng nhưng **buộc khách tự suy ra thành phần nào**.
# Khách hỏi về sữa thì câu trả lời phải nói "sữa".
#
# Hai bảng này bị `test_answer.py` ép phải phủ ĐỦ nhãn của nhóm tương ứng trong `menu-tags.json`,
# nên thêm nhãn mới vào từ điển mà quên ở đây là test đỏ — không phải bảng viết tay rồi trôi.
_ALLERGEN_VI = {
    "allergen:seafood": "hải sản",
    "allergen:peanut": "đậu phộng",
    "allergen:egg": "trứng",
    "allergen:dairy": "sữa",
    "allergen:gluten": "gluten",
}

_SPICE_VI = {
    "spice:none": "không cay",
    "spice:mild": "cay nhẹ",
    "spice:medium": "cay vừa",
    "spice:hot": "cay đậm",
}


def _thuoc_ho(item: dict, ho_mon: list[str]) -> bool:
    """Món này có thuộc một trong những họ món khách gọi tên không.

    So theo TỪ ĐẦU của tên món, không phải chứa-ở-bất-kỳ-đâu. "Bún đậu mắm tôm" bắt đầu bằng "bun"
    nên nó là món bún; còn nếu so kiểu chứa thì một họ tên ngắn sẽ quét sang món khác chỉ vì trùng
    chữ — đúng lớp lỗi đụng chữ mà cả `understand.py` được thiết kế để tránh.
    """
    from understand import fold

    ten = fold(item["name"])
    return any(ten == h or ten.startswith(h + " ") for h in ho_mon)


def _spice_of(item: dict) -> str:
    tag = next((t for t in item["tags"] if t.startswith("spice:")), "")
    return _SPICE_VI.get(tag, "")


_SERVING_VI = {
    "party:solo": "một người",
    "party:two_three": "2–3 người",
    "party:three_five": "3–5 người",
}


_MARKDOWN_NHAN_MANH = re.compile(r"\*\*|__|`")
_GACH_DAU_DONG = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)


def chu_cho_khach(chunk) -> str:
    """Đoạn tri thức, viết lại cho KHÁCH ĐỌC. Không đổi nội dung, chỉ đổi cách trình bày.

    Vì sao cần: đoạn được trích ra là dán THÔ trước khi có hàm này
    -------------------------------------------------------------
    Hỏi stack thật "Phở với bún khác nhau thế nào?" và khách nhận:

        Phở, bún, mì, hủ tiếu — khác nhau thế nào — Khác nhau ở SỢI, không ở nước dùng Người mới
        thường nghĩ các món nước Việt khác nhau ở nước dùng. Thực tế điều phân biệt chúng trước
        tiên là **sợi**: - **Phở** — sợi dẹt, mềm, làm từ gạo. Nước dùng trong. - **Bún** — ...

    Nội dung ĐÚNG. Trình bày thì sai ba chỗ, và cả ba đến từ `" ".join(text.split())`:

        1. tên tài liệu + tiêu đề mục dính vào đầu câu ("Phở, bún, mì, hủ tiếu — khác nhau thế nào
           — Khác nhau ở SỢI...") — khách hỏi một câu và nhận về một cái nhan đề
        2. dấu `**` của markdown lọt nguyên vào chữ khách đọc
        3. gạch đầu dòng bị nối thành một đoạn dài, nên "- **Phở** — sợi dẹt" thành "... là **sợi**:
           - **Phở** — sợi dẹt"

    Chỗ 1 đáng nói nhất vì nó là hệ quả của một quyết định ĐÚNG ở chỗ khác: `chunker` cố ý gắn tiêu
    đề tài liệu vào `text` để đoạn **tự đủ ngữ cảnh khi truy hồi**. Đúng cho việc xếp hạng, sai cho
    việc đọc. Hai mục đích khác nhau trên cùng một chuỗi, và trước đây chỉ có một cách trình bày.

    Vì sao KHÔNG bỏ tiêu đề khỏi `chunk.text`: làm vậy là làm yếu truy hồi để làm đẹp trình bày —
    đổi một thứ đo được lấy một thứ không đo được. Tách hai mục đích ra là cách đúng.

    Điều hàm này KHÔNG làm: nó không viết lại câu, không tóm tắt, không diễn đạt lại. Nội dung tri
    thức phải giữ nguyên chữ của người viết tài liệu — đó là toàn bộ lý do đường này không đi qua mô
    hình sinh.
    """
    tho = chunk.text
    # Bỏ dòng tiền tố (tiêu đề tài liệu — tiêu đề mục). Nó luôn là dòng ĐẦU, xem `chunker`.
    dong = tho.split("\n", 1)
    than = dong[1] if len(dong) > 1 else dong[0]

    than = _MARKDOWN_NHAN_MANH.sub("", than)
    # Gạch đầu dòng thành câu riêng: thay "- " bằng chỗ ngắt, rồi nối bằng "; " để đọc liền mạch mà
    # vẫn thấy đây là một danh sách. Không giữ ký tự "-" vì khách đọc trên điện thoại thấy nó lạc.
    than = _GACH_DAU_DONG.sub("\n• ", than)

    y = [d.strip() for d in than.split("\n") if d.strip()]
    ra = " ".join(y)
    return " ".join(ra.split())


def _chon_muc(co_muc: list, question: str):
    """Mục sát nhất trong MỘT tài liệu. Embedding khi được, BM25 khi không.

    Không dựng chỉ mục mới: dùng lại vector của chỉ mục TOÀN KHO, vốn đã nạp sẵn lúc khởi động. Xem
    docstring của `_knowledge_chunk` cho lý do đầy đủ và cho hai trường hợp lùi về BM25.
    """
    from rag.bm25 import Bm25Index

    theo_id = {c.chunk_id: c for c in co_muc}
    index, cach = _bo_truy_hoi_toan_kho()

    if cach == "embedding" and index is not None:
        co_vector = set(getattr(index, "chunk_ids", ()) or ())
        # ĐỦ ứng viên phải có vector, không phải một phần. Chấm điểm trên tập con thiếu vài đoạn là
        # lặng lẽ loại chúng khỏi cuộc thi — và đoạn bị loại có thể là đoạn đúng.
        if theo_id.keys() <= co_vector:
            diem = index.scores(question)
            # Phá thế theo `chunk_id` TĂNG DẦN — cùng luật với `Bm25Index.search` và với bộ so
            # (`sorted(..., key=lambda kv: (-kv[1], kv[0]))`). Dùng `max` với khóa `(điểm, chunk_id)`
            # sẽ chọn id LỚN nhất khi hòa, tức hai đường xếp hạng phá thế ngược nhau — và một hệ
            # thống có hai luật phá thế là hệ thống không lặp lại được kết quả của chính nó.
            return min(co_muc, key=lambda c: (-diem.get(c.chunk_id, 0.0), c.chunk_id))

    hits = Bm25Index.build(co_muc).search(question, k=1)
    return theo_id[hits[0].chunk_id] if hits else co_muc[0]


def _knowledge_chunk(topic: str, question: str) -> str | None:
    """Đoạn của tài liệu `topic` trả lời `question` sát nhất, hoặc None nếu không có tài liệu.

    Truy hồi ở đây chỉ xếp hạng TRONG PHẠM VI một tài liệu — 3–8 đoạn, không phải 303. Chủ đề đã
    được nhận ra bằng TRA KHÓA ở bước hiểu câu hỏi, nên phần xếp hạng không quyết định *trả lời về
    cái gì*, chỉ quyết định *mục nào của tài liệu đó*. Đó là lý do không cần ngưỡng tương đồng:
    tài liệu nào cũng có ít nhất một mục, và mục sát nhất luôn tốt hơn không trả lời.

    ĐÃ ĐỔI SANG EMBEDDING, vì SỐ — và vì chính dòng này dặn phải đổi khi có số
    ------------------------------------------------------------------------
    Bản trước dùng BM25 với hai lý lẽ: "3–8 đoạn cùng chủ đề khác nhau ở TỪ KHÓA của từng mục, đúng
    chỗ BM25 mạnh", và "nó không thêm 2–3GB vào ảnh Docker". Kèm điều kiện xét lại: *có tập ca ĐỦ
    LỚN cho việc chọn đoạn trong phạm vi tài liệu*.

    Cả hai lý lẽ nay đã hết, và điều kiện đã xảy ra:

        tập ca      168 ca / 13 họ, hai tập chia theo họ (`chunk_selection_cases.json`)
        Top-1       niêm phong  bm25 0,750  ->  embedding 0,864     +11,4 điểm
                    riêng câu diễn đạt khác từ  0,636 -> 0,818      +18,2 điểm
        ảnh Docker  đã có embedding cho nhánh truy hồi toàn kho, nên phần "thêm 2–3GB" là 0

    Đây là chỗ lệch đáng nói nhất còn lại sau khi đổi bộ truy hồi toàn kho: bộ so 168 ca đo ĐÚNG
    đường này, còn đường này vẫn chạy BM25. Tức báo cáo nói một bộ, hệ thống chạy bộ khác — đúng lớp
    lỗi mà `/ready.retriever` được thêm vào để chặn.

    Và nó KHÔNG tốn thêm gì lúc chạy
    -------------------------------
    Cách hiển nhiên là dựng một `EmbeddingIndex` cho mỗi tài liệu — nhưng đo được là mã hóa 3–8 đoạn
    mất ~91ms MỖI LƯỢT, tức đắt hơn BM25 gần 1000 lần cho cùng một việc.

    Cách ở đây không dựng gì: chỉ mục TOÀN KHO đã có vector của cả 370 đoạn và đã nạp sẵn lúc khởi
    động. Xếp hạng trong một tài liệu chỉ là **giới hạn phép chấm điểm đó vào tập con** — cosine trên
    vector đã chuẩn hóa L2 nên điểm của một đoạn không phụ thuộc việc có bao nhiêu đoạn khác trong
    chỉ mục. Chi phí thật: **một** lần mã hóa CÂU HỎI, thứ nhánh truy hồi toàn kho cũng phải làm.

    Lùi về BM25 ở hai trường hợp, và cả hai đều nói ra qua `/ready.retriever`:
      1. không có `sentence-transformers`
      2. ứng viên có đoạn MỞ ĐẦU — chúng không nằm trong chỉ mục toàn kho (`doan_toan_kho` lọc
         `heading` rỗng), nên không có vector để chấm. Chỉ xảy ra với tài liệu không có mục nào.

    CHIẾN LƯỢC ĐÃ ĐO NHƯNG KHÔNG NHẬN (giữ lại, vẫn đúng): "ưu tiên mục có TIÊU ĐỀ trùng nhiều từ với
    câu hỏi nhất" — xem đoạn dưới.

    CHIẾN LƯỢC ĐÃ ĐO NHƯNG KHÔNG NHẬN: "ưu tiên mục có TIÊU ĐỀ trùng nhiều từ với câu hỏi nhất".
    Nó đạt 6/7 so với 5/7 của bản hiện tại trên 7 câu có khóa đáp án — nhưng **n=7 thì một ca lệch
    là 14%**, và trên 3 câu chưa có khóa đáp án nó chọn đoạn KÉM HƠN ở 2 câu. Chọn chiến lược trên
    7 điểm dữ liệu với biên 1 ca là đúng thứ dự án này có luật riêng để tránh.

    Nên nó được ghi lại chứ không nhận, và điều kiện để xét lại là có tập ca ĐỦ LỚN cho việc chọn
    đoạn trong phạm vi tài liệu — chứ không phải cảm giác rằng tiêu đề là tín hiệu tốt.

    Trả `None` khi không tìm được tài liệu, và chỗ gọi nói "chưa có dữ liệu". Kho hỏng thì coi như
    chưa có, cùng nguyên tắc với `load_facts()`.
    """
    try:
        from rag.bm25 import Bm25Index
        from rag.chunker import retrievable_chunks

        cua_tai_lieu = [
            c for c in retrievable_chunks(KNOWLEDGE_PATH) if topic in c.topic_keys
        ]
    except (KnowledgeError, OSError, ImportError):
        return None
    if not cua_tai_lieu:
        return None

    # BỎ đoạn MỞ ĐẦU (`heading` rỗng) khỏi tập ứng viên. 55/425 đoạn là mở đầu, và chúng mô tả TÀI
    # LIỆU chứ không trả lời câu nào — "Tài liệu này nói về cách ghép các món với nhau...". Đo
    # được: BM25 chọn đúng đoạn mở đầu ở 2 câu, và câu trả lời khi đó không trả lời gì.
    #
    # Đây là quy tắc CẤU TRÚC, không phải chỉnh tham số: một mục không có tiêu đề là phần dẫn nhập
    # của tài liệu. Nên nó không cần đo để biện minh — nhưng vẫn đo, và nó sửa đúng 2 ca.
    #
    # Giữ lại mở đầu làm dự phòng khi tài liệu KHÔNG có mục nào: thà trả phần dẫn nhập còn hơn nói
    # "chưa có dữ liệu" khi tài liệu có nội dung.
    co_muc = [c for c in cua_tai_lieu if c.heading] or cua_tai_lieu

    chon = _chon_muc(co_muc, question)
    return chu_cho_khach(chon)


def _bo_truy_hoi_toan_kho():
    """Bộ xếp hạng trên TOÀN KHO, dựng một lần cho cả tiến trình.

    Vì sao nhánh này tồn tại
    ------------------------
    Đề bài (`00-problem-statement.md` mục 3B) nói loại B "cần một kho tri thức, và cần **tìm đúng
    đoạn**". Nhưng trước nhánh này, tài liệu `synthesize` chỉ tới được qua CỤM TỪ VỰNG: `understand`
    nhận ra `knowledge_topic` rồi `_knowledge_chunk` xếp hạng 3–7 đoạn TRONG tài liệu đó.

    Hệ quả đo được: 60 tài liệu nhưng chỉ 33 cụm chủ đề, nên phần kho không có cụm là nội dung
    **không bao giờ tới tay khách** — im lặng, không lỗi. Và thêm tài liệu mới mà không thêm cụm thì
    chỉ làm kho to hơn chứ không làm trợ lý trả lời được thêm câu nào.

    Truy hồi toàn kho tháo đúng nút đó: tài liệu tới được vì NỘI DUNG của nó khớp câu hỏi, không vì
    ai đó nhớ thêm một cụm vào từ vựng.

    KHÔNG có ngưỡng tương đồng, và nhánh này được đặt ở đâu là lý do
    ---------------------------------------------------------------
    Nó đứng ngay TRƯỚC nhánh hỏi lại, tức nó chỉ chạy khi câu hỏi **không có ràng buộc nào** để lọc
    thực đơn và **không** ngoài phạm vi. Đó là đúng tập câu đang rơi vào "bạn muốn món ăn hay đồ
    uống?" — nên nhánh này không lấy câu nào của nhánh khác, và nó không cần ngưỡng để quyết định
    có nên trả lời: nếu tới được đây thì lựa chọn còn lại là hỏi lại, và một đoạn tri thức sát nhất
    tốt hơn một câu hỏi lại.

    Chọn embedding khi có, lùi về BM25 khi không
    -------------------------------------------
    Đo được trên tập chọn mục (168 ca, hai tập): embedding Top-1 0,864–0,921 so với BM25 0,750–0,803,
    và cách biệt lớn nhất ở câu diễn đạt khác từ (0,818–0,868 so với 0,636–0,684).

    Nhưng `sentence-transformers` không nằm trong `ai/requirements.txt` (nó kéo theo 2–3GB), nên
    trong container hiện tại nhánh này chạy BM25. Hàm trả về CẢ TÊN phương pháp để `Reply.branch`
    nói ra cái nào đã chạy — một hệ thống âm thầm lùi về bản kém hơn là hệ thống không đo được.
    """
    global _TOAN_KHO
    if _TOAN_KHO is not None:
        return _TOAN_KHO
    try:
        from rag.bm25 import Bm25Index
        from rag.chunker import doan_toan_kho

        # `doan_toan_kho` chứ không phải phép lọc viết tại đây: bước tính sẵn vector lúc build phải
        # dùng ĐÚNG tập này, và khi phép lọc được viết ở hai chỗ thì hai chỗ đã lệch nhau một lần
        # rồi — đệm vector im lặng không bao giờ khớp. Xem docstring của `doan_toan_kho`.
        doan = doan_toan_kho(KNOWLEDGE_PATH)
        if not doan:
            _TOAN_KHO = (None, "kho rỗng")
            return _TOAN_KHO
        try:
            from rag import embedding as EMB

            if EMB.available():
                _TOAN_KHO = (EMB.EmbeddingIndex.build(doan), "embedding")
                return _TOAN_KHO
        except ImportError:
            pass
        _TOAN_KHO = (Bm25Index.build(doan), "bm25")
    except (KnowledgeError, OSError, ImportError) as exc:
        _TOAN_KHO = (None, f"{type(exc).__name__}")
    return _TOAN_KHO


_TOAN_KHO: tuple[object, str] | None = None


_TU_MIEN: frozenset[str] | None = None


def _tu_thuoc_mien(items: list[dict]) -> frozenset[str]:
    """Tập từ thuộc MIỀN nhà hàng, SINH TỪ DỮ LIỆU — không viết tay.

    Nguồn: tên món, tên danh mục, nhãn tiếng Việt của từ điển nhãn, và tiêu đề mọi tài liệu tri
    thức. Bốn nguồn đó là toàn bộ vốn từ mà hệ thống có thể trả lời về, nên một câu không chạm từ
    nào trong đó là câu hệ thống không có gì để nói.

    Vì sao không viết tay danh sách: nó sẽ trôi khỏi thực đơn ngay lần thêm món, và một cổng dựa
    trên danh sách trôi sẽ chặn oan hoặc mở oan mà không ai biết. Sinh từ dữ liệu thì tập tự lớn
    lên cùng thực đơn và kho.

    Bỏ từ một ký tự và từ chức năng ngắn: chúng có trong mọi câu nên chúng làm cổng vô nghĩa.
    """
    from understand import fold

    BO = {"mon", "cua", "va", "cho", "co", "khong", "nao", "gi", "la", "cai", "voi", "de",
          "ban", "minh", "toi", "duoc", "the", "nay", "do", "o", "an", "uong"}
    tu: set[str] = set()
    for i in items:
        tu.update(fold(i["name"]).split())
        tu.update(fold(i.get("categoryName", "")).split())
    try:
        import json as _json

        nhan = _json.loads(
            (Path(__file__).resolve().parents[2] / "backend" / "data" / "menu-tags.json")
            .read_text(encoding="utf-8-sig")
        )["tags"]
        for meta in nhan.values():
            tu.update(fold(meta.get("label_vi", "")).split())
    except (OSError, ValueError, KeyError):
        pass
    try:
        from rag.chunker import retrievable_chunks

        for c in retrievable_chunks(KNOWLEDGE_PATH):
            tu.update(fold(c.heading or "").split())
    except (KnowledgeError, OSError, ImportError):
        pass
    return frozenset(t for t in tu if len(t) > 2 and t not in BO)


def thuoc_mien(question: str, items: list[dict]) -> bool:
    """Câu hỏi có chạm vào vốn từ của nhà hàng không.

    Cổng cho nhánh truy hồi toàn kho. Đo được vì sao cần: không có nó, "Bạn là model gì?" nhận về
    một đoạn nói về lẩu, và "Đội nào thắng trận tối qua?" nhận về một đoạn nói về cà phê — cả hai
    tệ hơn một câu hỏi lại rõ ràng.
    """
    global _TU_MIEN
    if _TU_MIEN is None:
        _TU_MIEN = _tu_thuoc_mien(items)
    from understand import fold

    return any(t in _TU_MIEN for t in fold(question).split())


def trang_thai_truy_hoi() -> dict:
    """Trạng thái ĐỌC ĐƯỢC của tầng truy hồi, để `/ready` báo ra.

    Vì sao cần: lỗi đệm-vector-không-khớp là IM LẶNG
    -----------------------------------------------
    Đã xảy ra thật. Bước build tính vector cho 425 đoạn, lúc chạy cần 370 (tập đã lọc `heading`), nên
    hàm băm lệch và container mã hóa lại toàn bộ mỗi lần khởi động — 60 giây. Hệ thống vẫn ĐÚNG, chỉ
    chậm, và log build in "đã ghi ... cho 425 đoạn" nên mọi dấu hiệu nói là đã có đệm.

    Cách duy nhất phát hiện lúc đó là bấm giờ container rồi thấy nó không giảm. Ba trường dưới đây
    biến nó thành thứ nhìn thấy ngay — cùng lý do `/ready` phải báo `model_key_set` riêng thay vì chỉ
    báo `model_configured`: một trạng thái nói thiếu điều kiện làm người đọc tin một điều chưa kiểm.
    """
    index, cach = _bo_truy_hoi_toan_kho()
    return {
        "retriever": cach,
        "retriever_chunks": len(getattr(index, "chunk_ids", []) or []),
        # `None` khi bộ đang dùng không phải embedding — khác `False`, vì `False` nghĩa là "có đệm mà
        # không dùng được", còn `None` nghĩa là "khái niệm này không áp dụng".
        "retriever_vectors_from_cache": getattr(index, "tu_dem", None) if cach == "embedding" else None,
    }


def ham_nong_truy_hoi() -> str:
    """Dựng chỉ mục toàn kho NGAY, và trả về tên phương pháp đang dùng.

    Vì sao phải hâm nóng thay vì để lười
    ------------------------------------
    Chỉ mục dựng lười nghĩa là **khách đầu tiên** trả giá nạp mô hình và mã hóa 425 đoạn. Đo được
    trên máy có embedding: bộ test nhảy từ 20 giây lên 124 giây chỉ vì một lần dựng chỉ mục. Với
    khách thật thì đó là một lượt chat treo hàng chục giây, và nó xảy ra đúng lần đầu — tức đúng
    lúc gây ấn tượng xấu nhất.

    Embedding NAY đã vào ảnh, nên chi phí đó đã chuyển sang lúc khởi động — đúng như dòng này viết
    từ trước. Đo được trong container: 97,3 giây, và 61,7 giây trong đó là mã hóa. Sau khi vector
    được tính sẵn lúc build, phần mã hóa còn 0,1 giây.
    """
    _, cach = _bo_truy_hoi_toan_kho()
    return cach


def doan_tri_thuc_lien_quan(question: str) -> tuple[str, str] | None:
    """Đoạn sát nhất trên toàn kho, kèm tên phương pháp đã dùng. None nếu không tra được."""
    index, cach = _bo_truy_hoi_toan_kho()
    if index is None:
        return None
    hits = index.search(question, k=1)
    if not hits:
        return None
    try:
        from rag.chunker import retrievable_chunks

        theo_id = {c.chunk_id: c for c in retrievable_chunks(KNOWLEDGE_PATH)}
    except (KnowledgeError, OSError):
        return None
    chon = theo_id.get(hits[0].chunk_id)
    return (chu_cho_khach(chon), cach) if chon else None


def select(request: Request, items: list[dict]) -> list[dict]:
    """Lọc thực đơn theo đúng những gì khách đã nói.

    Thứ tự áp ràng buộc không đổi kết quả (đều là phép AND), nhưng ràng buộc dị nguyên
    được áp **cuối** và không bao giờ bị nới — kể cả khi kết quả rỗng. Đó là fail-closed:
    thà nói "không có món nào phù hợp" còn hơn mời khách một món có thể gây dị ứng.
    """
    picked = list(items)
    # Phạm vi và loại trừ do bộ nhớ phiên điền — tham chiếu ngược vào danh sách khách vừa đọc.
    # Áp TRƯỚC mọi ràng buộc khác vì chúng thu tập ứng viên, không phải thêm điều kiện lên nhãn.
    if request.scope_item_ids:
        cho_phep = set(request.scope_item_ids)
        picked = [i for i in picked if i["id"] in cho_phep]
    if request.exclude_item_ids:
        bo = set(request.exclude_item_ids)
        picked = [i for i in picked if i["id"] not in bo]
    # HỌ MÓN khách gọi tên thắng danh mục.
    #
    # Khách hỏi "có phở không" nhận về cả bún, vì "phở" ánh xạ vào danh mục `cat_noodle` — mà danh
    # mục ấy tên là **"Phở & Bún"**. Đúng nhóm, sai câu hỏi: khách nêu tên một họ món cụ thể.
    #
    # Phép kiểm sức khỏe deploy bắt được, và nó bắt bằng một bất biến rất chặt: mọi thẻ giỏ của câu
    # hỏi phở phải là món CÓ CHỮ PHỞ trong tên. Bốn món bún trong giỏ làm nó đỏ — trong khi 103 lượt
    # golden, 140 ca và 87 lượt phiên đều xanh.
    #
    # Lọc theo tên THAY danh mục, không cộng thêm: "Phở chay nấm đông cô" nằm ở `cat_vegetarian`, và
    # nó VẪN là phở. Giao hai điều kiện thì mất đúng món mà khách sẽ thấy thiếu.
    if request.ho_mon:
        picked = [i for i in picked if _thuoc_ho(i, request.ho_mon)]
    elif request.categories:
        picked = [i for i in picked if i["categoryId"] in request.categories]
    elif request.wants == "food":
        picked = [i for i in picked if i["categoryId"] in FOOD_CATEGORIES]
    elif request.wants == "drink":
        picked = [i for i in picked if i["categoryId"] in DRINK_CATEGORIES]
    for tag in request.require_tags:
        picked = [i for i in picked if tag in i["tags"]]
    if request.budget_max is not None:
        if request.budget_strict:
            picked = [i for i in picked if i["price"] < request.budget_max]
        else:
            picked = [i for i in picked if i["price"] <= request.budget_max]
    for tag in request.avoid_tags:
        picked = [i for i in picked if tag not in i["tags"]]
    return picked


def _order(items: list[dict], prefer_tags: list[str], wants: str = "any") -> list[dict]:
    """Sắp cố định để câu trả lời giống nhau mọi lần chạy.

    Món mang nhãn ngữ cảnh khách nêu (dịp ăn) được đưa lên trước, nhưng món không mang
    nhãn đó **không bị loại**. Đó là cách dùng đúng cho nhóm nhãn không phủ hết 91 món:
    thiếu nhãn nghĩa là *chưa ghi nhận*, không phải *không phù hợp*.

    Khi khách CHƯA nói món ăn hay đồ uống, món ăn được xếp trước đồ uống
    -------------------------------------------------------------------
    Vì sao cần: 5 món rẻ nhất thực đơn đều là đồ uống (12.000–30.000đ) còn món ăn rẻ nhất là
    35.000đ. Nên sắp theo giá tăng dần làm đồ uống **luôn** đứng đầu, và câu "món nào không cay?"
    trả về sáu loại bia. Đo được: **13/119 ca** khách hỏi "món" mà nhận toàn đồ uống — và cả 13
    đều QUA đánh giá, vì khóa đáp án không cấm đồ uống.

    Đây là NGỮ CẢNH, không phải ràng buộc — cùng nguyên tắc với dịp ăn:

    - **xếp trước**, nên "món nào không cay" trả món ăn thay vì bia
    - **KHÔNG lọc**, nên "món nào rẻ hơn 20 nghìn" vẫn trả đồ uống, vì không món ăn nào dưới
      20.000đ và trả rỗng ở đó mới là sai

    Lọc cứng ở đây sẽ hỏng đúng ca thứ hai: khách hỏi thật, dữ liệu trả lời được, mà hệ thống nói
    "không có món nào phù hợp".

    Tráng miệng và trái cây cũng phải xếp sau, KHÔNG chỉ đồ uống
    -----------------------------------------------------------
    Bản đầu chỉ đẩy `DRINK_CATEGORIES` xuống cuối, và bỏ sót một khoảng: `cat_dessert` và
    `cat_fruit` không thuộc `FOOD_CATEGORIES` **cũng không thuộc** `DRINK_CATEGORIES` — 14 món nằm
    ngoài cả hai nhóm. Chúng giá 30.000–45.000đ, còn món ăn rẻ nhất 35.000đ, nên chúng lên đầu y
    như bia từng lên đầu.
    
    Đo được: câu "Cho mình vài món không cay" nêu **0/6 món mặn** — cả sáu là chè, bánh flan và
    trái cây. Câu "Gợi ý vài món dưới 60 nghìn" nêu 1/6. Cả hai đều ĐÚNG về nhãn (chè không cay,
    chè dưới 60 nghìn) nhưng khách đang chọn bữa ăn và không gọi được một bữa từ 5 món chè.
    
    Cùng một lớp lỗi với sáu chai bia, nên cùng một cách sửa: **xếp hạng, không lọc**. Ca
    `P-savoury-03` ("có món tráng miệng nào không cay không?") là chốt cho điều đó — nó đỏ ngay
    nếu ai sửa bằng cách bỏ tráng miệng khỏi kết quả.
    """
    def key(item: dict) -> tuple:
        matched = sum(1 for t in prefer_tags if t in item["tags"])
        # Ba bậc, không hai: món mặn trước, rồi tráng miệng/trái cây, rồi đồ uống. Bậc giữa tồn tại
        # vì "món ăn phụ" gần với bữa ăn hơn đồ uống — khách hỏi "món gì" mà nhận chè thì còn hiểu
        # được, nhận bia thì không.
        if wants != "any" or item["categoryId"] in FOOD_CATEGORIES:
            bac = 0
        elif item["categoryId"] in DRINK_CATEGORIES:
            bac = 2
        else:
            bac = 1
        return (-matched, bac, item["price"], item["id"])

    return sorted(items, key=key)


def respond(request: Request, items: list[dict]) -> Reply:
    by_id = {i["id"]: i for i in items}
    named = [by_id[i] for i in request.named_items if i in by_id]

    # 1. Ngoài bài toán.
    if request.off_topic:
        return Reply(
            text=(
                "Mình chỉ hỗ trợ về món ăn và đồ uống của nhà hàng thôi ạ. "
                "Bạn cần gợi ý món gì không?"
            ),
            kind="refuse",
            branch="off_topic",
        )

    # 2. Câu chính sách và câu dinh dưỡng — chưa có kho tri thức nào.
    if request.policy_topic is not None:
        if request.policy_topic == "internal":
            return Reply(
                text=(
                    "Mình không cung cấp thông tin nội bộ của nhà hàng ạ. "
                    "Mình hỗ trợ bạn chọn món thì tiện hơn."
                ),
                kind="refuse",
                branch="internal",
            )
        if request.policy_topic == "no_size":
            # Món có thể có thật, nhưng thực đơn không có khái niệm size. Nêu giá cho
            # "size lớn" là bịa ra một thứ không tồn tại.
            item = named[0] if named else None
            head = f"{phrase(item)}. " if item is not None else ""
            return Reply(
                text=(
                    f"{head}Thực đơn chưa ghi nhận tùy chọn size cho món này, nên mình "
                    f"chưa có dữ liệu về giá theo size ạ. {STAFF_NOTE}"
                ),
                items=[item["id"]] if item is not None else [],
                kind="no_data",
                branch="no_size",
            )
        known = load_facts().get(request.policy_topic)
        if known:
            return Reply(
                text=f"{known} Nếu cần rõ hơn, bạn hỏi nhân viên giúp mình nhé.",
                kind="fact",
                branch=f"facts:{request.policy_topic}",
            )
        # Nêu tên món CHỈ khi khách trỏ vào nó bằng THAM CHIẾU, không nêu khi khách tự gõ tên.
        #
        # Phân biệt này không phải để một ca xanh — nó là hai tình huống khác nhau:
        #
        #   khách gõ "Phở bò tái nạm bao nhiêu calo?"  họ ĐÃ biết mình hỏi món nào. Nhắc lại tên
        #                                              không thêm gì, và trong một câu "chưa có dữ
        #                                              liệu" thì nó đọc như một lời MỜI món.
        #   khách gõ "món đó cho mấy người ăn?"        họ KHÔNG biết hệ thống hiểu "món đó" là món
        #                                              nào. Không nêu tên thì họ không phát hiện
        #                                              được khi hệ thống trỏ sai.
        #
        # Bản đầu của tôi nêu tên trong CẢ HAI, và `O-nodata-01` đỏ đúng vì lý do thứ nhất: một ca
        # "chưa có dữ liệu" không được nêu món. Thước đo bắt được, và nó bắt đúng.
        tro_bang_tham_chieu = named and request.reference_index is not None
        head = f"{phrase(named[0])}. " if tro_bang_tham_chieu else ""
        return Reply(
            text=(
                f"{head}Mình chưa có dữ liệu về việc này ạ. "
                f"{STAFF_NOTE}"
            ),
            items=[named[0]["id"]] if tro_bang_tham_chieu else [],
            kind="no_data",
            branch=f"policy:{request.policy_topic}",
        )

    # 2c. Khẩu phần của MỘT món đã nêu tên (hoặc trỏ tới bằng tham chiếu ngược).
    #
    # Trả lời từ nhãn `party:*` của chính món, không từ tri thức chung — hỏi về một món thì đáp án
    # là nhãn của món đó. Nhóm `party` phủ 91/91 nên nhánh này luôn có gì để nói.
    if request.asks_serving and named:
        item = named[0]
        muc = [_SERVING_VI[t] for t in ("party:solo", "party:two_three", "party:three_five")
               if t in item["tags"]]
        if muc:
            return Reply(
                text=f"{phrase(item)} phù hợp cho {', '.join(muc)} ạ.",
                items=[item["id"]],
                kind="fact",
                branch="serving_named_dish",
            )

    # 2d. Chủ đề tri thức NHIỀU MỤC. Khác nhánh 2 ở chỗ tài liệu có nhiều mục nên phải chọn mục.
    #
    # Đặt SAU nhánh chính sách (nguyên văn) và SAU nhánh món-đã-nêu-tên, TRƯỚC nhánh lọc. Thứ tự đó
    # là thứ tự loại trừ và nó quan trọng:
    #
    #   trước nhánh lọc  vì 4 trong 10 câu tri thức từng rơi vào nhánh lọc và nhận về danh sách món
    #   sau nhánh 2      vì chủ đề nguyên văn chính xác tuyệt đối, còn ở đây phải CHỌN mục
    #
    # Câu trả lời là đoạn tri thức NGUYÊN VĂN, không nhờ mô hình viết lại. Tài liệu được viết để
    # đọc được, và một chữ số lệch trong câu về nhà hàng là sai sự thật — cùng lý do với 24 chủ đề
    # nguyên văn. Mô hình có thể viết hay hơn, nhưng "hay hơn" không đáng đổi bằng "có thể bịa".
    # Hỏi khẩu phần mà KHÔNG nêu món nào -> câu hỏi về cả thực đơn, trả bằng tri thức chung.
    chu_de_tri_thuc = request.knowledge_topic
    if chu_de_tri_thuc is None and request.asks_serving:
        chu_de_tri_thuc = "portion_timing"

    if chu_de_tri_thuc is not None:
        doan = _knowledge_chunk(chu_de_tri_thuc, request.text)
        if doan:
            return Reply(
                text=f"{doan} Nếu cần rõ hơn, bạn hỏi nhân viên giúp mình nhé.",
                kind="fact",
                branch=f"knowledge:{chu_de_tri_thuc}",
            )
        return Reply(
            text=f"Mình chưa có dữ liệu về việc này ạ. {STAFF_NOTE}",
            kind="no_data",
            branch=f"knowledge_missing:{chu_de_tri_thuc}",
        )

    # 2b. Khách hỏi một món cụ thể mà thực đơn không có. Phải nói không có, tuyệt đối
    #     không được xác nhận hay bịa giá cho nó.
    if request.unknown_item:
        return Reply(
            text=(
                "Thực đơn của nhà hàng chưa có món đó nên mình chưa có dữ liệu về nó ạ. "
                "Bạn cho mình biết bạn thích vị gì để mình gợi ý món gần nhất nhé?"
            ),
            kind="no_data",
            branch="unknown_item",
            asks_back=True,
        )

    # 3. Hỏi giá một món đã nêu tên.
    if request.asks_price and len(named) == 1 and not request.is_comparison:
        item = named[0]
        return Reply(
            text=f"{item['name']} giá {money(item['price'])} ạ.",
            items=[item["id"]],
            kind="fact",
            branch="price_lookup",
        )

    # 4. So sánh hai món đã nêu tên.
    #
    # Nhận CẢ `asks_comparison` — cách hỏi TIẾP NỐI ("món nào cay hơn?") không nhắc lại tên món, và
    # `session.py` lấy lại cặp món của câu so sánh gần nhất. Không nới ở đây thì cặp món đã lấy lại
    # rơi xuống nhánh `item_detail` và câu trả lời nói về MỘT món — trả lời một câu so sánh bằng
    # thông tin của một bên.
    if (request.is_comparison or request.asks_comparison) and len(named) == 2:
        first, second = named
        gap = abs(first["price"] - second["price"])
        cheaper = first if first["price"] <= second["price"] else second
        # Nêu CẢ độ cay, không chỉ giá.
        #
        # Câu "món nào CAY HƠN?" từng nhận về so sánh GIÁ — đúng dữ liệu, sai câu hỏi. Và ca đánh
        # giá cho câu đó vẫn xanh, vì tiêu chí `tags_include` của nó là mã chết trong thước đo.
        #
        # Cách sửa là nêu cả hai thuộc tính chứ không đoán khách đang so chiều nào: `spice` phủ
        # 91/91 nên luôn nói được, và một câu trả lời nêu đủ giá lẫn độ cay trả lời được cả hai
        # cách hỏi mà không cần phân loại câu hỏi — bớt một chỗ có thể đoán sai.
        cay = [f"{i['name']} {_spice_of(i)}" for i in (first, second) if _spice_of(i)]
        them = f" Về độ cay: {', '.join(cay)}." if cay else ""
        return Reply(
            text=(
                f"{phrase(first)} và {phrase(second)}. "
                f"Chênh nhau {money(gap)}, {cheaper['name']} nhẹ ví hơn.{them} "
                "Bạn muốn mình nói thêm về khẩu vị của từng món không?"
            ),
            items=[first["id"], second["id"]],
            kind="compare",
            branch="compare",
        )

    # 5. Món đắt nhất / rẻ nhất, trong đúng phạm vi khách nêu.
    if request.asks_extreme is not None:
        pool = select(request, items) or items
        item = min(pool, key=lambda i: i["price"]) if request.asks_extreme == "cheapest" \
            else max(pool, key=lambda i: i["price"])
        label = "rẻ nhất" if request.asks_extreme == "cheapest" else "đắt nhất"
        # NÓI RÕ phạm vi khi phạm vi bị thu hẹp.
        #
        # Câu "Món đắt nhất là Cháo lòng Sài Gòn, giá 45.000đ" là một khẳng định TUYỆT ĐỐI sai,
        # dù cả tên món lẫn giá đều có thật: nó chỉ đúng trong phạm vi ngân sách đang có hiệu lực.
        # Với khách, một câu như vậy không khác gì bịa — nên câu trả lời phải mang theo phạm vi
        # của chính nó.
        #
        # Đo bằng số món, không bằng việc dò xem ràng buộc nào đang bật: hễ phạm vi nhỏ hơn cả
        # thực đơn thì nói ra, nên thêm ràng buộc mới về sau không cần sửa chỗ này.
        # `str.capitalize()` KHÔNG dùng được ở đây: nó hạ chữ toàn bộ phần sau, nên "Tôm hùm nướng
        # mỡ hành" thành "tôm hùm nướng mỡ hành". Tên món là dữ liệu, không phải văn xuôi — không
        # hàm chữ nào được chạy qua nó. Tiêu chí `must_name_item` của bộ chạy phiên bắt đúng lỗi
        # này, vì nó so tên món tra từ thực đơn chứ không so chuỗi viết tay.
        mo_dau = "Trong phạm vi bạn nêu, m" if len(pool) < len(items) else "M"
        return Reply(
            text=f"{mo_dau}ón {label} là {item['name']}, giá {money(item['price'])} ạ.",
            items=[item["id"]],
            kind="fact",
            branch=f"extreme:{request.asks_extreme}",
        )

    # 5b. Khách khẳng định một mức giá cho món đã nêu tên — ĐÍNH CHÍNH theo thực đơn.
    #
    # Đây là chốt "không nhận tiền đề sai": con số sai do KHÁCH đưa ra, và im lặng rồi trả lời
    # chuyện khác là để khách tin con số sai đó. Nhánh này chỉ đọc giá trong thực đơn nên nó không
    # thể bịa; việc nó thêm vào là nói thẳng hai con số có khớp nhau hay không.
    if named and request.asserted_price is not None:
        item = named[0]
        if item["price"] == request.asserted_price:
            noi = f"Đúng ạ, {phrase(item)} theo thực đơn."
        else:
            noi = (f"Thực đơn ghi {phrase(item)}, không phải "
                   f"{money(request.asserted_price)} ạ.")
        return Reply(
            text=f"{noi} {STAFF_NOTE}",
            items=[item["id"]],
            kind="fact",
            branch="price_assertion",
        )

    # 6a. Câu hỏi về dị nguyên của một món đã nêu tên.
    if named and request.asks_allergy:
        item = named[0]
        present = [t for t in request.avoid_tags if t in item["tags"]]
        # NÊU TÊN thành phần, không nói chung "thành phần bạn cần tránh". Khách hỏi về sữa thì
        # câu trả lời phải nói "sữa" — nếu không, họ phải tự suy ra, và ở câu về dị ứng thì bắt
        # khách suy luận là chỗ tệ nhất để tiết kiệm chữ.
        # Nêu MỌI dị nguyên thực đơn ghi nhận cho món này, không chỉ cái khách vừa hỏi.
        #
        # Người hỏi "món này có đậu phộng không?" đang hỏi VÌ LÝ DO DỊ ỨNG. Nói thêm rằng món đó
        # cũng có hải sản không tốn gì và có thể quan trọng với họ; im lặng về nó thì họ phải hỏi
        # từng thành phần một, và mỗi câu hỏi bỏ sót là một chỗ để sai.
        #
        # Tiêu chí này được viết trong ca `S-allergen-07` từ lâu — "câu trả lời tốt nêu luôn hải
        # sản dù khách chỉ hỏi đậu phộng" — nhưng thước đo BỎ QUA khóa `tags_include`, nên nó chưa
        # bao giờ được ép. Một tiêu chí không được thực thi là một yêu cầu đã viết mà chưa làm.
        moi_dn = [t for t in item["tags"] if t.startswith("allergen:")]
        ten_moi = [_ALLERGEN_VI.get(t, t.split(":")[-1]) for t in moi_dn]
        if present:
            return Reply(
                text=(
                    f"Thực đơn ghi nhận {phrase(item)} CÓ {', '.join(ten_moi)} — "
                    f"nên mình không gợi ý món này. {STAFF_NOTE}"
                ),
                items=[item["id"]],
                kind="fact",
                branch="allergen_named_dish",
            )
        # Chiều phủ định: nói rõ KHÔNG có thứ khách hỏi, rồi nêu những dị nguyên món đó THỰC SỰ có.
        hoi = [_ALLERGEN_VI.get(t, t.split(":")[-1]) for t in request.avoid_tags]
        ve = f" {', '.join(hoi)}" if hoi else " thành phần đó"
        con = f" Món này có ghi nhận {', '.join(ten_moi)}." if ten_moi else ""
        return Reply(
            text=(
                f"Thực đơn không ghi nhận{ve} trong {phrase(item)}.{con} "
                f"Mình chỉ đọc được phần thực đơn ghi. {STAFF_NOTE}"
            ),
            items=[item["id"]],
            kind="fact",
            branch="allergen_named_dish",
        )

    # 6b. Khách nêu tên món mà không hỏi gì cụ thể — nêu dữ kiện món đó.
    #
    # `reference_index is not None` là ngoại lệ cần thiết, không phải nới lỏng: khi khách nói "cái
    # đó có cay không?" thì `require_tags` vẫn còn `spice:none` **kéo từ bộ nhớ** của lượt trước
    # ("món nào không cay"). Không có ngoại lệ này thì điều kiện `not request.require_tags` sai, và
    # hệ thống trả về một DANH SÁCH mới thay vì trả lời về đúng món khách đang trỏ vào — đo được ở
    # `context-reference-02`.
    #
    # Ràng buộc kéo từ bộ nhớ là để LỌC DANH SÁCH; nó không được biến câu hỏi về một món thành câu
    # hỏi về cả thực đơn.
    # `refers_to_focus` cần ĐÚNG ngoại lệ như `reference_index`, và vì đúng lý do đã ghi ở trên:
    # câu "cái đó có cay không?" mang `require_tags` kéo từ bộ nhớ ("món nào không cay" ở lượt
    # trước), nên điều kiện `not request.require_tags` sai và hệ thống liệt kê lại danh sách thay vì
    # trả lời về món khách đang trỏ vào. Bỏ sót ngoại lệ này làm `context-reference-02` đỏ.
    if named and (
        request.reference_index is not None
        or request.refers_to_focus
        or (not request.require_tags and not request.categories)
    ):
        item = named[0]
        spice_vi = _spice_of(item)
        tail = f" Món này {spice_vi}." if spice_vi else ""
        return Reply(
            text=f"{phrase(item)}.{tail}",
            items=[item["id"]],
            kind="fact",
            branch="item_detail",
        )

    # 6c. Lọc thực đơn.
    # `wants` chỉ tính là "khách đã nói gì" khi CHÍNH KHÁCH nói, không khi mô hình đoán.
    #
    # `wants` một mình là ràng buộc yếu — thu 56/91 món (ăn) hoặc 21/91 (uống) — nhưng nó đủ để
    # tắt câu hỏi lại. Nên một `wants` do mô hình đoán biến câu hoàn toàn mơ hồ thành 6 món tùy ý,
    # và trả lời tự tin bằng phỏng đoán tệ hơn nói không biết. Đo được ở "Cho mình 2 món": mã tất
    # định hỏi lại đúng, mô hình trả `wants: food` và hệ thống liệt kê 6 món bất kỳ.
    #
    # Không chặn `wants` của mô hình ở chỗ khác: khi có ràng buộc khác đi cùng thì nó vẫn LỌC bình
    # thường. Chỉ chặn đúng một chuyện — nó không được một mình thay lời khách.
    khach_neu_wants = request.wants != "any" and not request.wants_from_model
    # Câu "HAI THỨ NÀY KHÁC NHAU THẾ NÀO" không có ràng buộc lọc nào — mọi từ trong câu là CHỦ THỂ.
    #
    # "Phở với bún khác nhau thế nào?" nêu `cat_noodle`; "Lẩu với nướng khác nhau thế nào?" nêu
    # `cat_hotpot` và `method:grilled`. Đọc chúng thành ràng buộc thì câu thứ nhất nhận 6 món và câu
    # thứ hai nhận "chưa tìm được món nào thỏa hết" — cả hai đều trả lời sai câu hỏi.
    #
    # Bản đầu của tôi chỉ bỏ `categories` và giữ `require_tags`, với lý do "nhãn vẫn là ràng buộc
    # thật". Lý do đó SAI, và câu lẩu-với-nướng chỉ ra chỗ sai: trong câu hỏi khác nhau, `method:grilled`
    # cũng là chủ thể chứ không phải điều kiện. Một quy tắc nửa vời ở đây tệ hơn không có quy tắc, vì
    # nó đúng ở ví dụ tôi nghĩ ra và sai ở ví dụ tôi chưa nghĩ tới.
    #
    # Chỉ áp dụng khi KHÔNG có tên món cụ thể: "Cơm tấm khác cơm chiên chỗ nào?" nêu tên món, và
    # nhánh so sánh hai món đã xử lý trước bước này.
    said_something = False if request.loai_mon_la_chu_de else bool(
        request.require_tags
        or request.prefer_tags
        or request.avoid_tags
        or request.categories
        or request.budget_max is not None
        or khach_neu_wants
    )
    if not said_something:
        # 6b-bis. TRUY HỒI TOÀN KHO trước khi hỏi lại.
        #
        # Câu tới được đây là câu không có ràng buộc nào để lọc thực đơn — tức lựa chọn còn lại là
        # hỏi lại. Một đoạn tri thức sát nhất tốt hơn một câu hỏi lại, và đây là chỗ DUY NHẤT trong
        # `respond()` mà điều đó đúng: mọi nhánh trước đã có thứ cụ thể hơn để trả lời.
        #
        # Không có ngưỡng tương đồng: VỊ TRÍ của nhánh làm việc của ngưỡng. Xem `_bo_truy_hoi_toan_kho`.
        #
        # NHƯNG loại trừ đúng một nhóm: khách XIN GỢI Ý MÓN mà chưa nêu ràng buộc. Đề bài mục 5 nói
        # hỏi lại ở câu thật sự mơ hồ là ĐÚNG, và trả một đoạn tri thức cho câu "cho mình món ngon"
        # là trả lời sai câu hỏi. Không có phép loại trừ này thì cả 6 ca `clarify` của tập đánh giá
        # rơi vào nhánh truy hồi — đo được ngay khi thêm nhánh: 134/140.
        # Hai điều kiện, và điều kiện thứ hai là bản sửa của một hồi quy do chính nhánh này gây ra.
        #
        #   xin_goi_y    khách xin gợi ý món mà chưa nêu gì -> HỎI LẠI là đúng (đề bài mục 5)
        #   thuoc_mien   câu không chạm vốn từ nhà hàng     -> không có gì để trả lời
        #
        # Không có điều kiện thứ hai, golden 103 lượt bắt được 5 câu ngoài phạm vi nhận về một đoạn
        # tri thức ngẫu nhiên: "Bạn là model gì?" -> đoạn về lẩu; "Đội nào thắng trận tối qua?" ->
        # đoạn về cà phê cho trẻ em. Cả hai tệ hơn hỏi lại.
        xin_goi_y = request.asks_suggestion or request.wants_similar
        co_the_tra = thuoc_mien(request.text, items)
        tim = None if (xin_goi_y or not co_the_tra) else doan_tri_thuc_lien_quan(request.text)
        if tim is not None:
            doan, cach = tim
            return Reply(
                text=f"{doan} Nếu cần rõ hơn, bạn hỏi nhân viên giúp mình nhé.",
                kind="fact",
                branch=f"knowledge_corpus:{cach}",
            )
        return Reply(
            # Nêu PHẠM VI trước khi hỏi lại.
            #
            # Nhánh này nhận hai loại câu rất khác nhau: câu mơ hồ nhưng đúng chủ đề ("tư vấn giúp
            # mình với") và câu ngoài phạm vi mà từ khóa không bắt được. Với loại thứ hai, hỏi
            # "bạn muốn món ăn hay đồ uống" là một câu trả lời trớ trêu.
            #
            # Nêu phạm vi phục vụ được cả hai mà không cần phân loại câu hỏi — và phân loại chính
            # là chỗ sẽ đoán sai, vì không có cách nào liệt kê hết kiến thức ngoài nhà hàng.
            text=(
                "Mình tư vấn món ăn và đồ uống của nhà hàng ạ. Để gợi ý đúng ý bạn, cho mình biết "
                "bạn muốn món ăn hay đồ uống, đi mấy người, và tầm giá khoảng bao nhiêu ạ?"
            ),
            kind="clarify",
            asks_back=True,
            branch="clarify",
        )

    picked = _order(select(request, items), request.prefer_tags, request.wants)
    if not picked:
        # Rỗng vì LOẠI TRỪ, hay rỗng vì RÀNG BUỘC? Hai chuyện khác nhau và phải trả lời khác nhau.
        #
        # Golden qua stack thật bắt được: khách xem ba lượt danh sách rồi nói "Cho mình món khác đi",
        # và nhận "Mình chưa tìm được món nào thỏa hết những điều bạn nêu ạ" — trong khi có món thỏa
        # ràng buộc, chỉ là chúng đã được nêu ở ba lượt trước.
        #
        # Danh sách loại trừ là một phép LỊCH SỰ: nó tránh gợi lại món khách vừa từ chối. Nó KHÔNG
        # phải ràng buộc an toàn. Nên khi nó là nguyên nhân duy nhất làm kết quả rỗng, việc đúng là
        # bỏ nó ra và NÓI RÕ, chứ không phải báo không có món nào.
        #
        # Phân biệt này quan trọng vì nó là ranh giới không được nhòe: ràng buộc dị nguyên, cay, giá,
        # chế độ ăn thì **không bao giờ** được nới — kể cả khi kết quả rỗng, vì nới chúng là mời khách
        # một món có thể gây hại. Loại trừ thì nới được, vì nới nó chỉ dẫn tới việc nhắc lại một món
        # khách đã thấy.
        khong_loai_tru = replace(request, exclude_item_ids=[])
        con_lai = _order(select(khong_loai_tru, items), request.prefer_tags, request.wants)
        if con_lai:
            # KHÔNG nêu lại danh sách. Khách vừa nói "cho mình món khác đi", nên nhắc lại đúng những
            # món họ vừa từ chối là trả lời ngược câu hỏi — và golden có tiêu chí
            # `must_not_repeat_turn` đúng để chặn việc đó.
            #
            # Bản đầu của nhánh này nêu lại, và golden bắt ngay. Việc đúng là nói ĐÃ HẾT rồi mời bỏ
            # bớt một điều kiện: khách còn đường đi tiếp, và không món nào bị nhắc lại.
            #
            # `items` rỗng nên không có thẻ giỏ — đúng, vì đây là câu hỏi lại chứ không phải câu gợi ý.
            return Reply(
                text=(
                    f"Mình đã nêu hết {len(con_lai)} món thỏa điều bạn cần rồi ạ. Bạn muốn mình bỏ "
                    "bớt một điều kiện để có thêm lựa chọn không?"
                ),
                kind="clarify",
                asks_back=True,
                branch="exhausted_after_exclusions",
            )
        return Reply(
            text=(
                "Mình chưa tìm được món nào thỏa hết những điều bạn nêu ạ. "
                f"{STAFF_NOTE}"
            ),
            kind="no_data",
            branch="empty_result",
        )

    shown = picked[:LIST_SIZE]
    lead = "Mời bạn tham khảo" if not request.avoid_tags else \
        "Thực đơn không ghi nhận thành phần bạn cần tránh ở những món này"
    text = f"{lead}: {listing(shown)}."
    if request.avoid_tags:
        text += f" {STAFF_NOTE}"
    if len(picked) > len(shown):
        text += f" Còn {len(picked) - len(shown)} món nữa, bạn muốn xem thêm không?"
    return Reply(
        text=text,
        items=[i["id"] for i in shown],
        kind="list",
        asks_back=len(picked) > len(shown),
        branch="filter",
    )
