# -*- coding: utf-8 -*-
"""Sinh tập ca CHỌN MỤC TRONG TÀI LIỆU — bài toán mà hệ thống thật đang giải.

    python ai/scripts/build_chunk_selection_cases.py
    python ai/scripts/build_chunk_selection_cases.py --check

Vì sao cần một tập RIÊNG
------------------------
`retrieval_cases.json` (138 ca) đo việc chọn **tài liệu** trên toàn kho 303 đoạn. Nhưng ở runtime,
`answer.py::_knowledge_chunk` chỉ xếp hạng **trong một tài liệu**: chủ đề đã được nhận ra bằng TRA
KHÓA ở bước hiểu câu hỏi, nên truy hồi quyết định *mục nào của tài liệu đó*, không quyết định *trả
lời về cái gì*.

Hai bài toán khác nhau, và kết quả của bài toán này KHÔNG suy ra được từ bài toán kia:

  - Toàn kho:      303 đoạn, 60 chủ đề, phân biệt bằng CHỦ ĐỀ
  - Trong tài liệu: 3–7 đoạn, một chủ đề, phân biệt bằng MỤC ĐÍCH của từng mục

Cho tới trước tập này, việc chọn BM25 cho runtime dựa trên một suy luận ("phạm vi hẹp cùng chủ đề
nên khác nhau ở từ khóa") chứ không dựa trên phép đo — trong khi phép đo trên toàn kho lại cho thấy
embedding THẮNG (Hit@5 0,921 so với 0,711). Tập này tồn tại để quyết bằng số.

TRẦN CỦA TẬP NẰM Ở KHO, KHÔNG Ở CÔNG SỨC
-----------------------------------------
Đo được trên kho hiện tại: 60 tài liệu nhưng chỉ **15 bộ tiêu đề khác nhau**, và **45 tài liệu dùng
chung MỘT khuôn** (`Tổng quan` / `Danh sách món` / `Dị nguyên trong nhóm này` / `Gợi ý chọn`).

Nên một tập sinh đủ trên kho sẽ trông như ~246 ca mà thực chất là **một quyết định 4 lựa chọn lặp 45
lần** cộng 60 quyết định thật. Đó là cái bẫy "n lớn mà phủ hẹp".

Tập này xử lý bằng cách TÁCH HAI NHÓM và báo cáo riêng:

  written    12 tài liệu, 60 mục, mỗi tài liệu một cấu trúc RIÊNG  -> con số chính
  derived    khuôn dùng chung, lấy mẫu 6 tài liệu                  -> báo cáo RIÊNG, không gộp

Gộp hai nhóm lại sẽ làm nhóm `derived` — vốn là một quyết định dễ, lặp lại — kéo con số chung lên và
che mất kết quả trên nhóm `written`. Muốn tập LỚN HƠN thật thì phải viết thêm tài liệu có cấu trúc
riêng; đó là việc của dữ liệu, không phải của phép đo.

HAI DẠNG CÂU HỎI, VÀ ĐÓ LÀ CHỖ BA PHƯƠNG PHÁP KHÁC NHAU
--------------------------------------------------------
Mỗi mục có ĐÚNG hai câu hỏi:

  A  dùng từ CÓ TRONG mục          -> BM25 nên thắng; nếu nó không thắng ở đây thì có lỗi
  B  diễn đạt khác, KHÔNG trùng từ -> embedding nên thắng nếu nó thật sự hiểu nghĩa

Một tập chỉ có dạng A sẽ luôn kết luận "BM25 đủ rồi" — và kết luận đó là hệ quả của cách viết ca, chứ
không phải của hệ thống. Đây là lý do tỷ lệ A/B là 1:1 và cố định, không phải tùy tay người viết.

Khóa đáp án là `chunk_id`, tra từ kho lúc sinh. Mã đoạn đổi thì bộ sinh DỪNG chứ không sinh ra một
khóa đáp án trỏ vào chỗ trống.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

from rag.chunker import retrievable_chunks  # noqa: E402

KNOWLEDGE = REPO_ROOT / "ai" / "knowledge"
OUT_PATH = REPO_ROOT / "ai" / "evaluation" / "chunk_selection_cases.json"

# Khuôn dùng chung của tài liệu `derived`. Khai tường minh để bộ sinh KIỂM được rằng nó vẫn là khuôn
# dùng chung — nếu kho đổi và khuôn này không còn, bộ sinh dừng thay vì lấy mẫu sai nhóm.
KHUON_DERIVED = ("Tổng quan", "Danh sách món", "Dị nguyên trong nhóm này", "Gợi ý chọn")

# Sáu tài liệu `derived` lấy mẫu. Chọn trải trên NHIỀU NHÓM NHÃN khác nhau (flavour, health, method,
# region, occasion, ingredient) chứ không lấy sáu tài liệu cùng nhóm: nếu lấy cùng nhóm thì mẫu càng
# hẹp hơn tổng thể mà nó đại diện.
MAU_DERIVED = (
    "kb.flavour.sour.v1",
    "kb.health.light.v1",
    "kb.method.grilled.v1",
    "kb.region.central.v1",
    "kb.occasion.date.v1",
    "kb.ingredient.beef.v1",
)

# Câu hỏi cho khuôn `derived`. Bốn mục, hai dạng — dùng chung cho cả sáu tài liệu, với `{ten}` là
# tên nhóm đọc từ tiêu đề tài liệu.
#
# Dạng B ở đây khó viết cho khác hẳn, vì bốn mục của khuôn vốn đã rất khác nhau về từ khóa. Đó chính
# là lý do nhóm này được báo cáo RIÊNG: nó là bài toán dễ, và trộn nó vào số chung là tự cho điểm.
CAU_DERIVED = {
    "Tổng quan": (
        "Nhóm {ten} có bao nhiêu món và giá từ bao nhiêu?",
        "Cho mình biết quy mô của nhóm {ten}",
    ),
    "Danh sách món": (
        "Danh sách món {ten} gồm những gì?",
        "Kể tên từng món trong nhóm {ten}",
    ),
    "Dị nguyên trong nhóm này": (
        "Dị nguyên trong nhóm {ten} là gì?",
        "Nhóm {ten} có thành phần nào người dị ứng cần biết?",
    ),
    "Gợi ý chọn": (
        "Gợi ý chọn món trong nhóm {ten}",
        "Nên lấy món nào của nhóm {ten} thì hợp?",
    ),
}

# ============================ 12 tài liệu `written`, 60 mục ============================
#
# Mỗi phần tử: (chunk_id, câu dạng A, câu dạng B)
#
# Dạng A dùng từ có trong mục. Dạng B nói cùng nhu cầu bằng từ KHÁC — và đây là phần khó viết, vì
# một câu B còn trùng từ khóa sẽ làm dạng B không đo được điều nó khai. Nguyên tắc khi viết: đọc
# tiêu đề mục, rồi hỏi lại bằng cách một người khách thật sẽ hỏi khi họ KHÔNG biết tài liệu có mục
# nào.
CAU_WRITTEN: list[tuple[str, str, str]] = [
    # --- allergy_guidance: 5 mục -----------------------------------------------------
    ("kb.written.allergy_guidance.v1#1",
     "Trợ lý làm được gì với thông tin dị ứng?",
     "Phần dị nguyên nào đã được ghi vào hệ thống rồi?"),
    ("kb.written.allergy_guidance.v1#2",
     "Trợ lý KHÔNG làm được gì về dị ứng?",
     "Bao nhiêu món chưa có thông tin thành phần gây ứng?"),
    ("kb.written.allergy_guidance.v1#3",
     "Mình cần làm thêm việc gì khi gọi món?",
     "Có nên trao đổi trực tiếp với người phục vụ không?"),
    ("kb.written.allergy_guidance.v1#4",
     "Dị nguyên của mình không nằm trong năm loại thì sao?",
     "Mình bị ứng mè và đậu nành, hệ thống xử lý thế nào?"),
    ("kb.written.allergy_guidance.v1#5",
     "Chế độ ăn không phải dị ứng thì thế nào?",
     "Ăn chay có được xếp cùng loại với ứng thức ăn không?"),
    # --- beverage_pairing: 7 mục -----------------------------------------------------
    ("kb.written.beverage_pairing.v1#1",
     "Quy tắc quan trọng nhất khi gợi ý đồ uống là gì?",
     "Khách nhờ chọn thức ăn thì có nên kèm thức uống không?"),
    ("kb.written.beverage_pairing.v1#2",
     "Món cay thì đi với đồ uống gì?",
     "Ăn thứ gì nồng vị ớt thì nên dùng gì kèm cho dịu?"),
    ("kb.written.beverage_pairing.v1#3",
     "Món nướng và món nhiều dầu mỡ đi với đồ uống gì?",
     "Ăn thứ gì ngậy béo thì dùng gì cho đỡ nặng?"),
    ("kb.written.beverage_pairing.v1#4",
     "Món nước như phở bún thì đi với gì?",
     "Đã có nước dùng rồi thì cần thêm thức uống nhiều không?"),
    ("kb.written.beverage_pairing.v1#5",
     "Món chay và món thanh nhẹ đi với đồ uống gì?",
     "Đồ thanh mát thì dùng gì kèm để không lấn vị?"),
    ("kb.written.beverage_pairing.v1#6",
     "Đồ uống cho trẻ em thì chọn gì?",
     "Bé nhỏ thì dùng thức gì, tránh thứ gì?"),
    ("kb.written.beverage_pairing.v1#7",
     "Món tráng miệng đi với đồ uống gì?",
     "Ăn đồ ngọt cuối bữa thì dùng gì cho cân lại?"),
    # --- budget_planning: 5 mục ------------------------------------------------------
    ("kb.written.budget_planning.v1#0",
     "Thực đơn có mấy mức giá?",
     "Các món được phân thành bao nhiêu bậc tiền?"),
    ("kb.written.budget_planning.v1#1",
     "Cách nói ngân sách nào được hiểu?",
     "Nói 'rẻ hơn 200 nghìn' khác 'dưới 200 nghìn' ở đâu?"),
    ("kb.written.budget_planning.v1#2",
     "Ngân sách cho nhóm thì nói thế nào?",
     "Số tiền em đưa là cho cả bàn hay tính đầu người?"),
    ("kb.written.budget_planning.v1#3",
     "Tiết kiệm mà vẫn đủ bữa thì làm sao?",
     "Muốn đỡ tốn mà vẫn no thì có cách nào?"),
    ("kb.written.budget_planning.v1#4",
     "Giá trên thực đơn có phải giá cuối không?",
     "Có phụ phí phục vụ hay bắt buộc tiền tip không?"),
    # --- combo_pairing: 6 mục -------------------------------------------------------
    ("kb.written.combo_pairing.v1#1",
     "Nguyên tắc chung của một bữa Việt là gì?",
     "Một mâm cơm cân đối thường gồm mấy phần?"),
    ("kb.written.combo_pairing.v1#2",
     "Ghép món cho một người thì thế nào?",
     "Em đi ăn một mình thì lấy mấy thứ là đủ?"),
    ("kb.written.combo_pairing.v1#3",
     "Ghép món cho hai đến ba người thì thế nào?",
     "Nhóm ba đứa thì chia thứ tự lấy ra sao?"),
    ("kb.written.combo_pairing.v1#4",
     "Ghép món cho nhóm bốn người trở lên thì thế nào?",
     "Bàn đông cỡ năm sáu đứa thì bố trí thế nào?"),
    ("kb.written.combo_pairing.v1#5",
     "Điều cần tránh khi ghép món là gì?",
     "Kết hợp kiểu nào thì bị lặp vị và dở bữa?"),
    ("kb.written.combo_pairing.v1#6",
     "Khi khách có ràng buộc thì ghép món thế nào?",
     "Thứ tự ưu tiên giữa dị ứng, chế độ ăn và khẩu vị là gì?"),
    # --- dietary_limits: 4 mục ------------------------------------------------------
    ("kb.written.dietary_limits.v1#1",
     "Thực đơn ghi nhận được ăn chay thế nào?",
     "Có bao nhiêu lựa chọn không dùng thịt, và có kèm trứng sữa không?"),
    ("kb.written.dietary_limits.v1#2",
     "Thực đơn ghi nhận năm loại dị nguyên nào?",
     "Năm thành phần gây ứng nào đã được đưa vào dữ liệu?"),
    ("kb.written.dietary_limits.v1#3",
     "Chế độ nào thực đơn KHÔNG ghi nhận?",
     "Halal, kosher, keto thì hệ thống trả lời được không?"),
    ("kb.written.dietary_limits.v1#4",
     "Vì sao không đoán chế độ ăn?",
     "Nhãn 'ít calo' dựa trên phân tích hay cảm nhận người nhập?"),
    # --- faq_extended: 7 mục --------------------------------------------------------
    ("kb.written.faq_extended.v1#1",
     "Món nào ngon nhất?",
     "Đâu là thứ đáng thử nhất theo đánh giá chung?"),
    ("kb.written.faq_extended.v1#2",
     "Có món nào đặc biệt hôm nay không?",
     "Bữa nay bếp có gì mới ra so với thường ngày?"),
    ("kb.written.faq_extended.v1#3",
     "Món này có bao nhiêu calo?",
     "Số liệu dinh dưỡng của từng thứ có được lưu không?"),
    ("kb.written.faq_extended.v1#4",
     "Món này làm từ gì?",
     "Phần mô tả có liệt kê đủ mọi thành phần không?"),
    ("kb.written.faq_extended.v1#5",
     "Có thể đổi món hoặc bớt thành phần không?",
     "Em muốn bỏ một nguyên liệu ra thì được không?"),
    ("kb.written.faq_extended.v1#6",
     "Món nào rẻ nhất, đắt nhất?",
     "Khoảng tiền trải từ đâu tới đâu, và mức giữa là bao nhiêu?"),
    ("kb.written.faq_extended.v1#7",
     "Nhà hàng có món của vùng nào?",
     "Bếp nấu theo phong cách của những địa phương nào?"),
    # --- first_visit: 5 mục ---------------------------------------------------------
    ("kb.written.first_visit.v1#0",
     "Thực đơn được tổ chức thế nào?",
     "Các nhóm được sắp theo thứ tự gì, có theo chữ cái không?"),
    ("kb.written.first_visit.v1#1",
     "Lần đầu tới thì nên thử gì trước?",
     "Người mới chưa quen thì bắt đầu từ đâu cho an toàn?"),
    ("kb.written.first_visit.v1#2",
     "Khoảng giá của thực đơn thế nào?",
     "Phần lớn các thứ nằm quanh mức tiền nào?"),
    ("kb.written.first_visit.v1#3",
     "Món đặc sản vùng miền thì sao?",
     "Cùng một tên ở hai địa phương có khác vị không?"),
    ("kb.written.first_visit.v1#4",
     "Điều nên nói ngay với trợ lý là gì?",
     "Bốn thông tin nào nói trước thì đỡ phải hỏi qua lại?"),
    # --- meal_sets: 4 mục -----------------------------------------------------------
    ("kb.written.meal_sets.v1#1",
     "Bữa trưa cần gì?",
     "Giữa ngày thì nên chọn kiểu gì cho gọn và không nặng?"),
    ("kb.written.meal_sets.v1#2",
     "Bữa tối cần gì?",
     "Buổi muộn đi cả nhóm thì kiểu nào hợp nhất?"),
    ("kb.written.meal_sets.v1#3",
     "Có bảy món lẩu nào và khi nào chọn món nào?",
     "Các nồi nhúng có mấy loại, giá và vị khác nhau ra sao?"),
    ("kb.written.meal_sets.v1#4",
     "Món nào cần đặt trước?",
     "Thứ gì phải báo sớm vì bếp chuẩn bị lâu?"),
    # --- ordering_guide: 4 mục ------------------------------------------------------
    ("kb.written.ordering_guide.v1#1",
     "Gọi bao nhiêu món cho nhóm?",
     "Số lượng nên lấy tính theo đầu người thế nào?"),
    ("kb.written.ordering_guide.v1#2",
     "Thứ tự gọi món cho nhóm là gì?",
     "Nên hỏi điều gì trước, chốt điều gì sau?"),
    ("kb.written.ordering_guide.v1#3",
     "Nhóm có người ăn chay thì sao?",
     "Trong bàn có người không dùng thịt thì bố trí thế nào?"),
    ("kb.written.ordering_guide.v1#4",
     "Nhóm có trẻ em hoặc người lớn tuổi thì sao?",
     "Có bé nhỏ và ông bà đi cùng thì cần lưu ý gì?"),
    # --- portion_timing: 3 mục ------------------------------------------------------
    ("kb.written.portion_timing.v1#0",
     "Khẩu phần được mô tả bằng mấy nhãn?",
     "Một suất thường đủ cho mấy miệng ăn?"),
    ("kb.written.portion_timing.v1#1",
     "Thời gian chờ món thế nào?",
     "Có biết thứ nào ra bàn trước thứ nào không?"),
    ("kb.written.portion_timing.v1#2",
     "Món mang đi thì thế nào?",
     "Có đóng gói đem về được không, và nhà hàng có giao tận nơi?"),
    # --- qr_ordering: 5 mục ---------------------------------------------------------
    ("kb.written.qr_ordering.v1#0",
     "Quét mã và mở phiên thế nào?",
     "Sau khi chụp mã ở bàn thì điều gì xảy ra?"),
    ("kb.written.qr_ordering.v1#1",
     "Trò chuyện với trợ lý thế nào?",
     "Cần gõ đúng dấu không, và nói gì thì gợi ý sát hơn?"),
    ("kb.written.qr_ordering.v1#2",
     "Trợ lý gợi ý món, ai quyết định?",
     "Hệ thống có tự đưa thứ gì vào giỏ hộ em không?"),
    ("kb.written.qr_ordering.v1#3",
     "Bộ nhớ mất khi nào?",
     "Người tới sau quét cùng mã có thấy cuộc nói của em không?"),
    ("kb.written.qr_ordering.v1#4",
     "Khi trợ lý không trả lời được thì sao?",
     "Gặp câu ngoài dữ liệu thì hệ thống làm gì?"),
    # --- sharing_etiquette: 5 mục ---------------------------------------------------
    ("kb.written.sharing_etiquette.v1#0",
     "Bữa Việt là bữa chia chung nghĩa là gì?",
     "Khác gì với kiểu mỗi người một suất riêng?"),
    ("kb.written.sharing_etiquette.v1#1",
     "Cơm trắng gọi riêng thế nào?",
     "Thứ tinh bột ăn kèm tính theo bàn hay theo đầu người?"),
    ("kb.written.sharing_etiquette.v1#2",
     "Món lẩu là món của cả bàn nghĩa là sao?",
     "Nồi nhúng có cần mỗi người một cái không?"),
    ("kb.written.sharing_etiquette.v1#3",
     "Thứ tự món ra bàn thế nào?",
     "Bếp đưa lên theo lúc nấu xong hay theo lúc em kêu?"),
    ("kb.written.sharing_etiquette.v1#4",
     "Gọi thêm giữa bữa có được không?",
     "Đang ăn mà thấy thiếu thì kêu tiếp có sao không?"),
]


def build() -> dict:
    chunks = retrievable_chunks(KNOWLEDGE)
    theo_id = {c.chunk_id: c for c in chunks}
    theo_doc: dict[str, list] = collections.defaultdict(list)
    for c in chunks:
        theo_doc[c.doc_id].append(c)

    cases: list[dict] = []

    # --- nhóm `written`: con số CHÍNH -------------------------------------------------
    for chunk_id, cau_a, cau_b in CAU_WRITTEN:
        c = theo_id.get(chunk_id)
        if c is None:
            raise SystemExit(
                f"khóa đáp án trỏ vào đoạn KHÔNG TỒN TẠI: {chunk_id!r}. Kho đã đổi — sửa bảng câu "
                "hỏi, đừng để khóa đáp án trỏ vào chỗ trống."
            )
        doc = c.doc_id
        anh_em = [x.chunk_id for x in theo_doc[doc] if x.heading and x.chunk_id != chunk_id]
        if not anh_em:
            raise SystemExit(f"{doc} chỉ có một mục — việc chọn mục không có nghĩa")
        ho = doc.split(".")[2] if doc.count(".") >= 2 else doc
        for dang, cau in (("A", cau_a), ("B", cau_b)):
            cases.append({
                "id": f"cs-{ho}-{chunk_id.split('#')[1]}-{dang}",
                "family": f"cs-{ho}",
                "nhom": "written",
                "dang": dang,
                "doc_id": doc,
                "query": cau,
                "expected_chunk_id": chunk_id,
                "candidates": sorted([chunk_id, *anh_em]),
                "why": (
                    f"Mục {c.heading!r} của {doc}. "
                    + ("Dạng A dùng từ CÓ TRONG mục — BM25 nên thắng ở đây, và nếu nó không thắng "
                       "thì có lỗi ở phần xếp hạng chứ không phải ở cách viết ca."
                       if dang == "A" else
                       "Dạng B nói cùng nhu cầu bằng từ KHÁC — đây là chỗ embedding phải hơn nếu "
                       "nó thật sự hiểu nghĩa. Một tập chỉ có dạng A sẽ luôn kết luận 'BM25 đủ "
                       "rồi', và kết luận đó là hệ quả của cách viết ca.")
                ),
            })

    # --- nhóm `derived`: báo cáo RIÊNG ------------------------------------------------
    for doc in MAU_DERIVED:
        cs = theo_doc.get(doc)
        if not cs:
            raise SystemExit(f"không có tài liệu mẫu {doc!r} trong kho")
        heads = tuple(x.heading for x in cs if x.heading)
        if heads != KHUON_DERIVED:
            raise SystemExit(
                f"{doc} không còn dùng khuôn dùng chung (nó có {list(heads)}). Mẫu này chỉ có nghĩa "
                "khi nó đại diện cho khuôn — chọn tài liệu khác hoặc bỏ nhóm này."
            )
        # Tên nhóm lấy từ tiêu đề tài liệu, phần trước dấu gạch dài.
        ten = cs[0].text.split("—")[0].strip() if "—" in cs[0].text else doc
        for x in cs:
            if not x.heading:
                continue
            cau_a, cau_b = CAU_DERIVED[x.heading]
            anh_em = [y.chunk_id for y in cs if y.heading and y.chunk_id != x.chunk_id]
            for dang, cau in (("A", cau_a), ("B", cau_b)):
                cases.append({
                    "id": f"cs-derived-{doc.split('.')[1]}-{doc.split('.')[2]}-"
                          f"{x.chunk_id.split('#')[1]}-{dang}",
                    "family": "cs-derived-template",
                    "nhom": "derived",
                    "dang": dang,
                    "doc_id": doc,
                    "query": cau.format(ten=ten),
                    "expected_chunk_id": x.chunk_id,
                    "candidates": sorted([x.chunk_id, *anh_em]),
                    "why": (
                        f"Khuôn dùng chung của 45 tài liệu `derived`, mục {x.heading!r}. "
                        "Nhóm này là MỘT quyết định lặp lại nhiều lần, nên nó được báo cáo RIÊNG "
                        "và KHÔNG gộp vào con số chính — gộp vào sẽ để một bài toán dễ kéo con số "
                        "chung lên."
                    ),
                })

    written = [c for c in cases if c["nhom"] == "written"]
    derived = [c for c in cases if c["nhom"] == "derived"]
    return {
        "schema_version": 1,
        "authored": "Sinh bởi ai/scripts/build_chunk_selection_cases.py — đừng sửa tay tệp này.",
        "provenance": [
            "Bài toán: CHỌN MỤC TRONG MỘT TÀI LIỆU — đúng việc `answer.py::_knowledge_chunk` làm.",
            "",
            "Khác `retrieval_cases.json` (138 ca), vốn đo việc chọn TÀI LIỆU trên toàn kho. Kết quả",
            "của bài toán này không suy ra được từ bài toán kia: toàn kho phân biệt bằng CHỦ ĐỀ,",
            "trong tài liệu phân biệt bằng MỤC ĐÍCH của từng mục.",
            "",
            f"TRẦN của tập nằm ở kho: 60 tài liệu nhưng chỉ 15 bộ tiêu đề khác nhau, và 45 tài liệu",
            "dùng chung MỘT khuôn. Nên hai nhóm được tách và báo cáo riêng:",
            f"  written  {len(written)} ca trên 12 tài liệu, mỗi tài liệu một cấu trúc riêng -> số CHÍNH",
            f"  derived  {len(derived)} ca, khuôn dùng chung, lấy mẫu 6 tài liệu -> báo cáo RIÊNG",
            "",
            "Muốn tập LỚN HƠN thật thì phải viết thêm tài liệu có cấu trúc riêng — việc của dữ liệu,",
            "không phải của phép đo.",
            "",
            "Mỗi mục có ĐÚNG hai câu hỏi, tỷ lệ cố định 1:1:",
            "  A  dùng từ CÓ TRONG mục          -> BM25 nên thắng",
            "  B  diễn đạt khác, không trùng từ -> embedding nên thắng nếu nó thật sự hiểu nghĩa",
            "",
            "Một tập chỉ có dạng A sẽ luôn kết luận 'BM25 đủ rồi', và kết luận đó là hệ quả của cách",
            "viết ca chứ không phải của hệ thống.",
        ],
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kiểm, không ghi.")
    args = parser.parse_args(argv)

    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    cases = data["cases"]
    written = [c for c in cases if c["nhom"] == "written"]
    derived = [c for c in cases if c["nhom"] == "derived"]

    print(f"ca            : {len(cases)}  ({len(written)} written + {len(derived)} derived)")
    print(f"họ            : {len({c['family'] for c in cases})}")
    print(f"tài liệu       : {len({c['doc_id'] for c in cases})}")
    print(f"dạng A / dạng B: {sum(1 for c in cases if c['dang'] == 'A')} / "
          f"{sum(1 for c in cases if c['dang'] == 'B')}")
    ung_vien = [len(c["candidates"]) for c in cases]
    print(f"số ứng viên/ca : {min(ung_vien)}–{max(ung_vien)} "
          f"(trung bình {sum(ung_vien) / len(ung_vien):.1f})")

    if args.check:
        if not OUT_PATH.exists() or OUT_PATH.read_text(encoding="utf-8-sig") != text:
            print("\n--check: tệp khác kết quả sinh lại. Chạy lại script.")
            return 1
        print("\n--check: khớp.")
        return 0

    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"\nĐã ghi {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
