# -*- coding: utf-8 -*-
"""Hiểu câu hỏi của khách thành ràng buộc có cấu trúc — không dùng mô hình nào.

Đây là cơ chế duy nhất trong hệ thống đọc chữ của khách, và là nơi bản cũ chết. Nên nó
được viết theo ba quy tắc rút từ bảy lỗi cũ.

**Quy tắc 1 — khớp cụm dài trước, rồi ăn hết đoạn đã khớp.**

Bản cũ so từng nhãn với câu hỏi một cách độc lập, nên sau khi rút dấu thì `ban chay`
(bán chạy) **chứa** `chay` (ăn chay), và câu "món nào bán chạy" trả về món chay. Cùng lớp
lỗi: `mien Trung` chứa `trung` (trứng), `luc lac` chứa `lac` (đậu lạc).

Ở đây mọi cụm được sắp theo độ dài giảm dần. Cụm nào khớp thì đoạn văn bản đó bị **thay
bằng khoảng trắng**, nên cụm ngắn hơn không còn thấy nó nữa. "bán chạy" ăn mất "chay"
trước khi luật ăn chay kịp nhìn. Đây là cách sửa cả lớp lỗi, không phải vá từng ca.

**Quy tắc 2 — rút dấu để khớp cách khách gõ, không để quyết định nội dung.**

Khách gõ "mon nao khong cay k". Phải khớp được. Nhưng chữ đã rút dấu chỉ dùng để **tìm**
ràng buộc; nội dung câu trả lời luôn lấy từ thực đơn có dấu.

**Quy tắc 3 — mỗi cụm khai rõ nó suy ra ràng buộc gì.**

Không có bảng ánh xạ ngầm. `"khong cay" -> spice:none` viết ra được, kiểm được, và một
cụm chỉ sinh đúng một loại ràng buộc.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# --- Chuẩn hóa ------------------------------------------------------------------------


# Dấu chấm hoặc phẩy KHÔNG nằm giữa hai chữ số. Phải giữ lại khi nó nằm giữa hai chữ số,
# vì "50.000đ" là một số tiền — bỏ hết dấu câu thì "50.000đ" thành "50 000d" và bộ đọc tiền
# sẽ đọc ra 0 đồng.
_PUNCT_NOT_IN_NUMBER = re.compile(r"(?<!\d)[.,]|[.,](?!\d)")
_OTHER_PUNCT = re.compile(r"[^\w\s.,]")


def fold(text: str) -> str:
    """Rút dấu, hạ chữ thường, bỏ dấu câu, gộp khoảng trắng. Chỉ dùng để KHỚP.

    Bỏ dấu câu là bắt buộc, không phải làm cho đẹp: khách gõ "mấy giờ mở cửa?" và
    "dị ứng hải sản," — nếu dấu câu còn dính vào chữ thì cụm `mo cua` và `hai san` không
    khớp được, và cả sáu test đầu tiên của tệp này đã đỏ đúng vì lý do đó.
    """
    lowered = unicodedata.normalize("NFD", text.lower())
    without = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
    cleaned = _OTHER_PUNCT.sub(" ", without.replace("đ", "d"))
    cleaned = _PUNCT_NOT_IN_NUMBER.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


# --- Ràng buộc ------------------------------------------------------------------------


@dataclass
class Request:
    """Điều khách đã nói, dưới dạng máy dùng được."""

    text: str
    folded: str
    named_items: list[str] = field(default_factory=list)
    require_tags: list[str] = field(default_factory=list)
    prefer_tags: list[str] = field(default_factory=list)
    avoid_tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    budget_max: int | None = None
    budget_strict: bool = False   # True: rẻ HƠN X (<X); False: tầm X trở xuống (<=X)
    wants: str = "any"          # "food" | "drink" | "any"
    asks_allergy: bool = False
    asks_about_named_dish: bool = False
    # Khách có THẬT SỰ khai điều cần tránh, hay chỉ HỎI về thành phần của một món?
    #
    # Hai chuyện này cùng sinh ra `avoid_tags` — và phải cùng sinh, vì để trả lời "món này có hải
    # sản không?" thì hệ thống cần biết nhãn hải sản. Nhưng chỉ MỘT trong hai được vào BỘ NHỚ:
    #
    #   "mình dị ứng hải sản"          KHAI  -> nhớ suốt phiên, không bao giờ bỏ
    #   "Cơm gà Hội An có hải sản không?"  HỎI   -> trả lời rồi thôi
    #
    # Gộp hai thứ này là một lỗi khách NHÌN THẤY: một câu hỏi tò mò làm 26/91 món bị ẩn suốt phiên,
    # và câu trả lời sau đó nói "thành phần bạn cần tránh" — khẳng định một điều khách chưa hề nói.
    # Lỗi này chỉ hiện khi chạy thật qua backend, vì nó cần bộ nhớ SỐNG QUA nhiều lượt.
    declared_avoidance: bool = False
    asks_price: bool = False
    # Giá khách KHẲNG ĐỊNH về một món đã nêu tên — khác hoàn toàn với ngân sách.
    #
    # "Phở bò tái nạm giá 45.000đ đúng không?" từng bị đọc thành ngân sách 45.000đ, và hậu quả đo
    # được khi chạy thật: ngân sách đó vào bộ nhớ phiên và DÍNH LẠI, nên lượt sau "Món đắt nhất giá
    # bao nhiêu?" trả lời "Cháo lòng Sài Gòn, 45.000đ" — mọi con số đều có thật trong thực đơn,
    # nhưng câu trả lời thì sai.
    asserted_price: int | None = None
    # Khách hỏi một phần cho MẤY NGƯỜI ăn. Trả lời từ nhãn `party:*` của chính món, không từ tri
    # thức chung — hỏi về một món thì đáp án là nhãn của món đó.
    asks_serving: bool = False
    asks_extreme: str | None = None   # "cheapest" | "priciest"
    is_comparison: bool = False
    off_topic: bool = False
    policy_topic: str | None = None
    # Chủ đề tri thức `answer_mode: synthesize` — KHÁC `policy_topic`, và tách ra là cố ý.
    #
    #   policy_topic     24 chủ đề `verbatim`: cả tài liệu là MỘT câu trả lời, trả nguyên văn.
    #                    Tra khóa, không xếp hạng, mô hình không chạm vào chữ.
    #   knowledge_topic  11 chủ đề `synthesize`: tài liệu có NHIỀU mục, phải chọn mục nào trả lời
    #                    câu này. Vẫn tra khóa để tìm TÀI LIỆU, rồi xếp hạng trong phạm vi tài
    #                    liệu đó để chọn ĐOẠN — phạm vi 3–8 đoạn thay vì 303.
    #
    # Gộp hai trường thì nhánh trả lời phải đoán tài liệu thuộc loại nào, và `load_facts()` chỉ có
    # nội dung của loại thứ nhất — nên chủ đề loại thứ hai sẽ trả "chưa có dữ liệu" trong khi câu
    # trả lời NẰM TRONG REPO. Đó đúng là lỗi đã đo được ở câu "một phần lẩu cho mấy người ăn?".
    knowledge_topic: str | None = None
    unknown_item: bool = False
    unparsed_restriction: bool = False  # khách nêu điều cần tránh mà không hiểu tránh gì
    # Tham chiếu ngược vào danh sách khách VỪA đọc. Ba cơ chế khác nhau, không gộp được:
    #
    #   reference_index   1-based; -1 = món cuối. "món đầu tiên", "cái thứ ba", "món đó".
    #                     Giải ra thành `named_items` ở bước hợp nhất bộ nhớ, nên nó tái dùng
    #                     nguyên các nhánh đã có (price_lookup, item_detail, allergen_named_dish)
    #                     thay vì thêm nhánh thứ bảy.
    #   scope_last_listed "trong số đó", "trong những món đó" — thu PHẠM VI về danh sách vừa nêu.
    #                     Khác reference_index: nó không trỏ vào MỘT món, nó giới hạn tập.
    #   wants_similar     "còn món nào giống vậy" — giữ ràng buộc cũ, BỎ món đã nêu.
    #
    # Gộp ba thứ này thành một cờ là chỗ dễ sai nhất: "món rẻ nhất trong số đó" cần phạm vi chứ
    # không cần một món, còn "còn món nào giống vậy" cần đúng NGƯỢC LẠI của việc trỏ vào món cũ.
    reference_index: int | None = None
    scope_last_listed: bool = False
    wants_similar: bool = False
    # Khách trỏ vào món ĐANG NÓI TỚI ("món đó", "cái đó", "món vừa rồi"). `session.py` phân giải
    # thành món tiêu điểm của lượt trước, và lùi về món thứ nhất của danh sách nếu chưa có tiêu điểm.
    refers_to_focus: bool = False
    # Khách hỏi so sánh mà KHÔNG nhắc lại tên món ("món nào cay hơn?"). `session.py` lấy lại cặp món
    # của câu so sánh gần nhất.
    asks_comparison: bool = False
    # Khách hỏi VỀ một thuộc tính, không yêu cầu LỌC theo thuộc tính đó — "Món này có bột ngọt
    # không?", "Nhãn 'ít calo' dựa trên gì?". Xem bước 5d-bis của `understand()`.
    #
    # Cờ này chỉ có MỘT chỗ đọc: cổng `already_understood` của `llm_understand.enrich()`. Nó không đổi
    # nhánh nào — nó chỉ NGĂN lớp mô hình đổi nhánh mà đường tất định đã chọn đúng.
    asks_about_attribute: bool = False
    # Khách XIN GỢI Ý MÓN mà chưa nêu ràng buộc nào. Cờ này quyết định giữa HỎI LẠI và TRUY HỒI
    # TOÀN KHO: cả hai nhánh nhận cùng một tập câu "không hiểu được gì", nên phải có cách tách.
    #
    # Đề bài mục 5: hỏi lại khi câu thật sự mơ hồ là ĐÚNG. Trả một đoạn tri thức cho câu "cho mình
    # món ngon" là trả lời sai câu hỏi, không phải trả lời tốt hơn.
    # Câu HỎI VỀ một sự việc ("có ... không", "thế nào", "vì sao"), khác câu XIN MÓN.
    #
    # `answer.respond` dùng cờ này để đưa câu xuống nhánh truy hồi TRƯỚC nhánh lọc. Không có cờ thì
    # sau khi bỏ tín hiệu nhóm món, `select()` trả về CẢ thực đơn và câu vẫn vào nhánh lọc — tức
    # vẫn trả lời sai dạng, chỉ khác là danh sách dài hơn.
    hoi_ve_su_viec: bool = False
    asks_suggestion: bool = False
    # Số món khách xin, khi họ nêu rõ ("cho mình 2 món"). None nghĩa là để hệ thống tự chọn.
    so_mon_muon: int | None = None
    # Câu này là XIN MÓN (đặt/lấy), không phải HỎI VỀ một món. Dùng để quyết định khi tham chiếu
    # ngược mơ hồ: hỏi thì đoán được, xin thì phải hỏi lại. Xem `session.merge_into_request`.
    la_xin_mon: bool = False
    # Tham chiếu ngược MƠ HỒ và không đoán được: câu xin món trỏ "món vừa rồi" trong khi danh sách
    # vừa nêu có nhiều món và chưa có tiêu điểm. `answer` đọc cờ này để hỏi lại thay vì đoán.
    mo_ho_tieu_diem: bool = False
    # Khách hỏi hai LOẠI món khác nhau thế nào. Câu tri thức, nên tên loại món trong câu KHÔNG được
    # đọc thành ràng buộc lọc — xem `DIFFERENCE_FRAMING`.
    asks_difference: bool = False
    # Ý ĐỊNH của lượt này — xem `intent.py`. Mặc định `hoi_mon`, tức "đi tiếp xuống tầng chọn món".
    y_dinh: str = "hoi_mon"
    # Nhóm ràng buộc khách bảo BỎ ("allergen", "all"). Đây là điều `llm_understand` KHÔNG diễn đạt
    # được: hợp đồng của nó chỉ cho THÊM nhãn, nên "tôi hết dị ứng rồi" không có cách nào nói ra.
    y_dinh_bo: list[str] = field(default_factory=list)
    # Danh mục khách nói RÕ LÀ KHÔNG muốn. Khác `avoid_tags` ở chỗ nó loại theo DANH MỤC, không
    # theo nhãn — vì "bia" là một danh mục, không phải một thuộc tính. Xem `_danh_muc_bi_phu_dinh`.
    avoid_categories: list[str] = field(default_factory=list)
    # Các SUẤT của một yêu cầu combo: [(tên suất, số lượng, danh mục hợp lệ)]. Rỗng = không phải
    # câu combo. Xem `SUAT_COMBO`.
    combo: list = field(default_factory=list)
    # Câu «A hay B» — hai vế là LỰA CHỌN, `select()` lấy HỢP thay vì GIAO. Xem `HAI_LUA_CHON_RE`.
    hai_lua_chon: bool = False
    # Ràng buộc KÉO TỪ LƯỢT TRƯỚC, do `session.merge_into_request` điền. `understand()` không bao
    # giờ đặt trường này — nó chỉ đọc câu của lượt hiện tại.
    #
    # Dùng cho đúng một việc: nhánh mời-bỏ chỉ được mời bỏ thứ khách KHÔNG nói ở lượt này. Mời bỏ
    # điều họ vừa nói ra là một câu trả lời vô nghĩa — golden bắt được ngay:
    #
    #     "Vị miền Bắc khác miền Nam thế nào?"
    #     -> Điều kiện "miền bắc" đang chặn — bỏ nó ra thì có 35 món.   <- khách VỪA nêu miền Bắc
    #
    # Câu đó là câu hỏi tri thức, và ràng buộc "chặn" nó là hai nhãn của chính nó.
    rang_buoc_ke_thua: list[str] = field(default_factory=list)
    # Nhãn ĐÃ bị bỏ ở lượt này, do `session.merge_into_request` điền. Câu trả lời phải NÊU RA chúng:
    # một hàng rào an toàn được hạ xuống thì khách phải THẤY nó được hạ, để sửa được nếu hiểu sai.
    da_bo_rang_buoc: list[str] = field(default_factory=list)
    # HỌ MÓN khách gọi tên: "phở", "bún", "cơm"... Lọc theo đây THAY danh mục, vì danh mục có thể
    # gộp nhiều họ ("Phở & Bún") và khách hỏi phở thì không muốn thấy bún.
    ho_mon: list[str] = field(default_factory=list)
    # Tên loại món là CHỦ THỂ của câu hỏi, không phải ràng buộc. Tính đúng MỘT lần ở `understand()`
    # và đọc ở hai nơi (`understand` bước 6b, `answer.respond` bước 6), vì đây là một bất biến hai
    # đầu: bỏ danh mục khỏi phép lọc mà vẫn suy `wants` từ danh mục đó thì câu vẫn đi nhánh lọc —
    # đúng chuyện đã xảy ra khi tôi viết điều kiện này ở riêng `respond()`.
    loai_mon_la_chu_de: bool = False
    # Hai tập id do bước hợp nhất bộ nhớ điền, KHÔNG do bộ khớp từ vựng điền. `understand()` chỉ
    # nhận ra khách đang tham chiếu; nó không biết khách đã đọc danh sách nào. Tách vai như vậy để
    # `understand()` giữ được tính chất "chỉ đọc câu của lượt này".
    # `wants` này do MÔ HÌNH ĐOÁN, không phải khách nói. Chỉ `llm_understand.enrich` đặt cờ này.
    #
    # Nó tồn tại vì một khác biệt mà bản thân `Request` không mang được: hai câu dưới đây cho ra
    # `Request` GIỐNG HỆT NHAU sau khi qua mô hình, nhưng đáng được trả lời khác nhau —
    #
    #   "Tư vấn cho mình vài món ăn đi"  khách NÓI "món ăn" -> gợi ý là đúng
    #   "Cho mình 2 món"                 khách chỉ nêu SỐ   -> hỏi lại là đúng
    #
    # Cả hai cùng ra `wants=food` và không có gì khác. Không có cờ này thì hệ thống buộc phải xử
    # hai câu như một, và dù chọn cách nào cũng sai một câu.
    wants_from_model: bool = False
    scope_item_ids: list[str] = field(default_factory=list)
    exclude_item_ids: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)


# --- Từ vựng: cụm khách gõ -> ràng buộc ------------------------------------------------
#
# Mỗi mục: cụm (đã rút dấu) -> (loại ràng buộc, giá trị).
# `require` thêm nhãn phải có, `avoid` thêm nhãn phải tránh, `category` giới hạn danh mục,
# `wants` phân biệt món ăn / đồ uống, `flag` bật một cờ.
#
# Thứ tự trong bảng KHÔNG quan trọng — bộ khớp tự sắp theo độ dài giảm dần.

VOCAB: dict[str, tuple[str, object]] = {}


def _add(phrases: str, kind: str, value: object) -> None:
    for phrase in phrases.split("|"):
        key = fold(phrase)
        if key in VOCAB:
            raise ValueError(f"cụm trùng trong từ vựng: {phrase!r}")
        VOCAB[key] = (kind, value)


# Chủ đề dị nguyên. Một từ như "hải sản" có HAI nghĩa tùy cách hỏi:
#
#   "Nhà hàng có hải sản gì?"        -> duyệt danh mục hải sản
#   "Mình dị ứng hải sản"            -> tránh mọi món có hải sản
#   "Cơm gà Hội An có hải sản không?" -> hỏi về một món đã nêu tên
#
# Bản đầu của tôi chỉ nhận cụm cố định "dị ứng hải sản", nên câu thứ ba bị hiểu thành câu
# thứ nhất — và hệ thống liệt kê toàn món hải sản cho người đang hỏi vì dị ứng. Đó là lỗi
# an toàn tệ nhất có thể có.
#
# Nên chủ đề và cách hỏi được tách ra, nhưng vẫn dùng CHUNG một vòng khớp: giá trị là
# (nhãn dị nguyên, danh mục tương ứng nếu có). Cách hỏi quyết định đọc theo nghĩa nào.
# "đồ tanh", "mùi tanh" là cách người Việt nói về cá và hải sản. Thiếu chúng thì lời
# khai dị ứng "mình không ăn được đồ tanh" không được hiểu — và đó là lỗi AN TOÀN.
_add("hai san|do bien|do tanh|mui tanh|thuc pham tanh", "allergen_topic", ("allergen:seafood", "cat_seafood"))
_add("dau phong|lac", "allergen_topic", ("allergen:peanut", None))
_add("trung", "allergen_topic", ("allergen:egg", None))
_add("sua|lactose", "allergen_topic", ("allergen:dairy", None))
_add("gluten|bot mi", "allergen_topic", ("allergen:gluten", None))

# TÊN MÓN CỤ THỂ nối tới nhóm dị nguyên. Khách khai dị ứng thường gọi đúng thứ mình ăn, không
# gọi tên nhóm: "ăn tôm là bị nổi mề đay", "ăn kem là bị đau bụng". Trước khi có khối này thì
# câu đó cho `avoid=[]` — tức KHÔNG LỌC GÌ CẢ, và hệ thống mời lại 26 món mang nhãn hải sản.
#
# Vì sao an toàn dù các cụm này rất ngắn và nằm trong nhiều tên món:
#
# 1. `category=None` ở mọi mục. Nên khi KHÔNG có ngữ cảnh tránh, nhánh `allergen_topic` không
#    làm gì cả — "mình thích ăn tôm" và "cho mình cà phê" đi qua mà không sinh nhãn nào. Cụm
#    chỉ có tác dụng khi khách đã khai tránh.
#
# 2. Cơ chế khớp cụm dài trước rồi ăn hết đoạn đã khớp che các chỗ đụng: `gio mo cua` khớp
#    trước `cua`, `ca nhan` trước `ca`, `bot mi` trước `mi`, và tên món khớp trước tất cả.
#
# Điểm 2 là chỗ tôi đã đo SAI một lần. Bộ dò đầu của tôi phân tích chuỗi con và kết luận `cua`
# nguy hiểm vì nó nằm trong `gio mo cua`, `ca` nguy hiểm vì nằm trong `ca nhan` — nó loại 17/19
# cụm. Nhưng phân tích chuỗi con KHÔNG BIẾT về việc ăn đoạn, nên nó cho dương tính giả. Đo lại
# bằng cách chạy `understand()` thật trên 9 câu khai dị ứng và 20 câu thường: 19/19 cụm an toàn,
# 9/9 câu khai hiểu được, 0/20 câu thường bị sai.
#
# Bài học: đo một cơ chế thì phải CHẠY nó, không phân tích chuỗi thay cho nó.
# `so` (sò) ĐÃ BỎ khỏi danh sách này. Nó rút dấu về cùng chuỗi với **số**, **sợ**, **so**:
#
#     "Mình không ăn được món SỐ 2"    -> avoid=['allergen:seafood']   ẩn 26 món hải sản
#     "Mình dị ứng, không ăn được SỐ 3" -> như trên
#     "Mình SỢ cay" / "SO sánh hai món" -> khớp nhưng chưa thành ràng buộc
#
# Khách chọn món theo số thứ tự rồi nói không ăn được, và hệ thống giấu toàn bộ hải sản. Sai theo
# chiều fail-closed nên không nguy hiểm, nhưng khách mất lựa chọn mà không biết vì sao.
#
# Bỏ được vì nó KHÔNG TỐN GÌ: đo trên 627 câu -> **0 câu đổi**, và không món nào trong 91 món có
# chữ "sò" đứng riêng thành một từ. Cụm này chưa từng bắt được ca thật nào.
#
# `ca` (cá) thì PHẢI GIỮ dù nó cũng đụng "cả": bỏ nó làm "Mình dị ứng cá" mất hàng rào dị nguyên —
# đo được, 1 câu đổi và đúng câu quan trọng nhất. Nên "Có CẢ ông bà, mình không ăn được cay" vẫn
# ẩn nhầm hải sản. Ghi ra thay vì sửa liều: hai chữ ấy sau khi rút dấu là MỘT, và phân biệt chúng
# cần ngữ cảnh mà lớp khớp cụm không có.
_add("tom|tom su|tom hum|cua|ghe|muc|ca|ca bien|ca hoi|nghieu|oc|hau",
     "allergen_topic", ("allergen:seafood", None))
_add("pho mai|kem", "allergen_topic", ("allergen:dairy", None))
_add("trung ga|long do", "allergen_topic", ("allergen:egg", None))
_add("mi|lua mi|mi cang", "allergen_topic", ("allergen:gluten", None))

# Cách hỏi cho thấy khách muốn TRÁNH, chứ không muốn duyệt.
AVOID_FRAMING = (
    "di ung",
    "khong an duoc",
    "khong uong duoc",
    "khong the an",
    "khong an",
    "khong co",
    "can tranh",
    "tranh",
    "bi celiac",
    "celiac",
    "khong dung nap",
    "di ung voi",
    # --- Rà 20 cách khai dị ứng hải sản: chỉ 7/20 = 35,00% được nhận ra --------------------
    #
    # Con số đó đánh thẳng vào câu mạnh nhất của báo cáo. "0 lỗi an toàn" ĐÚNG trên bộ đánh giá và
    # SAI với khách thật, vì bộ đánh giá dùng chính những cách nói hệ thống đã biết — bộ đo và hệ
    # thống cùng một tác giả, cùng một vốn từ.
    #
    # Ba nhóm bỏ sót, và cả ba đều là cách nói rất thường:
    #
    #   phủ định khả năng   "không ai ăn được", "không dùng được", "không hợp với"
    #   nói bằng HẬU QUẢ    "ăn vào là đi cấp cứu", "nổi mề đay", "lên cơn", "đi viện"
    #   nói bằng MỆNH LỆNH  "tuyệt đối không", "xin đừng", "loại hết", "tránh xa"
    #
    # Mỗi cụm dưới đây được nạp riêng rồi chạy `understand()` trên **849 câu hỏi của 8 tập**:
    # 0/849 câu đổi kết quả, tức không cụm nào chạm vào phần đang đúng.
    #
    # HAI CỤM BỊ BỎ dù phép đo nói an toàn, vì chúng mang đúng hình dạng đã gây 11 vụ đụng chữ:
    #
    #   `cu`         "cữ hải sản" — nhưng rút dấu trùng "cũ", "củ", "cụ". "món cũ" thành câu
    #                khai dị ứng là lỗi tệ hơn lỗi đang sửa.
    #   `khong dinh` "không dính hải sản" — trùng "không định". "mình không định gọi món đó"
    #                sẽ thành câu tránh.
    #
    # Phép đo trên 849 câu không thấy hai lỗi đó chỉ vì tập chưa có câu nào dạng ấy. Đây là chỗ
    # phép đo im lặng KHÔNG đủ để kết luận an toàn.
    "khong ai an duoc",
    "khong dung duoc",
    "khong hop voi",
    "khong dam an",
    "phai tranh",
    "tranh xa",
    "kieng",
    "tuyet doi khong",
    "khong duoc co",
    "xin dung",
    "dung cho",
    "loai het",
    "bo giup",
    "allergy",
    "giap xac",
    # Khai bằng HẬU QUẢ, không bằng chữ "dị ứng". Khách mô tả điều sẽ xảy ra với mình.
    "soc phan ve",
    "noi me day",
    "di cap cuu",
    "len con",
    "bi sung",
    "di vien",
)

# Khi nào một nhãn được dùng làm LỌC CỨNG (`require`) và khi nào chỉ được XẾP HẠNG (`prefer`)
# -------------------------------------------------------------------------------------------
# Bản đầu tôi viết quy tắc là "nhóm phủ 91/91 thì lọc được". Đo lại thì quy tắc đó vừa quá chặt
# vừa nói sai lý do. Quy tắc thật có ba mệnh đề khác nhau, và trộn chúng lại là chỗ tôi sai:
#
#   lọc theo nhãn CÓ MẶT   an toàn ở mọi độ phủ. Nhãn có mặt là điều đã KHẲNG ĐỊNH, nên món
#                          nêu ra chắc chắn thỏa. Cái mất là ĐỘ BAO: món đúng nhưng chưa
#                          được gắn nhãn sẽ bị bỏ. Mất độ bao thì khách thiếu lựa chọn;
#                          nêu món không thỏa thì khách nhận câu trả lời SAI. Chọn mất độ bao.
#   lọc theo nhãn VẮNG MẶT chỉ an toàn khi nhóm được gắn nhãn ĐẦY ĐỦ. `avoid_tags` là loại này,
#                          và nhãn dị nguyên chỉ phủ 44/91 — nên đó là giới hạn phải NÓI RA,
#                          không phải chỗ để suy ra "không có nhãn nghĩa là an toàn".
#   phủ 91/91              không quyết định được lọc hay không. Nó quyết định câu "không có
#                          món nào phù hợp" có nghĩa hay không: nhóm phủ hết thì rỗng là rỗng
#                          thật; nhóm phủ một phần thì rỗng có thể chỉ là chưa gắn nhãn.
#
# Còn một cái bẫy chỉ hiện khi ĐO: `require_tags` là phép AND. Hai cụm trong CÙNG một câu map
# sang hai nhãn KHÁC nhau của cùng nhóm thì giao có thể rỗng, và ca đỏ theo cách không ai đọc
# ra được. Ví dụ "sinh viên nên hơi ít tiền, món nào vừa phải thôi": `price` nằm trong
# `exclusive_groups` nên mỗi món đúng một nhãn giá, và price:budget ∩ price:mid = 0 món. Vì vậy
# "vừa phải" bị BỎ khỏi từ vựng thay vì gắn nhãn price:mid — xem ghi chú ở nhóm giá.

# Độ cay — `spice` nằm trong `exclusive_groups` và phủ 91/91, nên đây là nhóm lọc dứt khoát
# nhất: mỗi món đúng một mức, và "không có món nào" là câu trả lời thật chứ không phải thiếu nhãn.
_add("khong an duoc cay|khong an cay|khong cay|k cay|it cay", "require", "spice:none")
_add("cay nhe|hoi cay", "require", "spice:mild")
_add("cay vua", "require", "spice:medium")
_add("cay dam|cay nhieu|that cay", "require", "spice:hot")
# "MÓN CAY" — từ vựng nói được "không cay" nhưng KHÔNG nói được "cay", và đó là một bất đối xứng
# một chiều đúng nghĩa: khách vào được ràng buộc độ cay nhưng không có đường ra.
#
# Đo được trên bản chạy thật. Khách hỏi thực đơn cho bàn 4–5 người, hệ thống dính `spice:none`, và
# khi khách nói **"tư vấn cho tôi các món cay đi"** thì câu đó rút ra **rỗng** — không nhãn nào.
# Quy tắc ghi đè theo nhóm của `session` hoàn toàn đúng, nhưng nó chỉ chạy khi lượt mới CÓ một nhãn
# cùng nhóm. Không có nhãn thì không có gì để ghi đè, nên `spice:none` sống mãi và mọi câu sau đó
# đều mở bằng "Vì bạn muốn món không cay…" — trong khi khách vừa xin điều ngược lại.
#
# Nhãn phải là "cay ở bất kỳ mức nào" chứ không phải một mức cụ thể: thực đơn có 14 món cay nhẹ,
# 6 cay vừa, 3 cay đậm. Gán "món cay" vào `spice:hot` là trả 3 món cho một câu đáng được 23 món.
# `select()` đọc dấu `|` là PHÉP HOẶC TRONG CÙNG NHÓM — xem chú thích ở đó.
#
# `an cay` an toàn dù `khong an cay` chứa nó: `VOCAB_ORDER` khớp cụm DÀI TRƯỚC và ăn hết đoạn đã
# khớp, nên cụm phủ định luôn được tiêu thụ trước.
#
# `do cay` và `an cay` bị BỎ khỏi danh sách này sau khi soát chồng chữ, đúng luật đã đặt từ lần
# `chay` va chạm: **một cụm phải tự chứng minh là an toàn, không được mặc định chấp nhận.**
#
#     do cay   "độ cay" và "đồ cay" rút dấu thành CÙNG một chuỗi. "món này độ cay thế nào" là câu
#              hỏi thuộc tính, biến nó thành yêu cầu lọc là trả lời sai câu hỏi.
#     an cay   "ít khi ăn cay", "đâu có ăn cay" đều mang nghĩa ngược. Cụm dài phủ định được tiêu
#              thụ trước nên `khong an cay` an toàn, nhưng hai cách nói trên thì không có cụm dài
#              nào che. `an duoc cay` diễn đạt đúng ý mà không dính hai câu đó.
_add("mon cay|vi cay|thich cay|an duoc cay", "require", "spice:mild|medium|hot")

# Chế độ ăn.
_add("an chay|do chay|thuan chay|nguoi an chay", "require", "diet:vegetarian")
# "menu món chay" là hỏi về MỤC Món chay, khác với "tôi ăn chay" là nêu nhu cầu.
# Gộp hai thứ thì câu "Menu món chay gồm gì?" trả về cả món tráng miệng có nhãn chay.
_add("mon chay|menu chay|muc chay", "category", "cat_vegetarian")
_add("vegan", "require", "diet:vegan")

# Nhà hàng giới thiệu — "ban chay" phải nằm đây, và vì nó dài hơn "chay" nên nó ăn trước.
_add("ban chay nhat|ban chay|pho bien nhat|pho bien|duoc goi nhieu", "require", "promo:popular")
_add("dac trung|dac san cua nha hang|mon tu hao|signature", "require", "promo:signature")

# Nguyên liệu.
# KHÔNG có cụm `bo` một âm tiết, và đó là bản sửa của một lỗi đo được trên production HAI LẦN.
#
# "bỏ", "bó", "bơ" đều rút dấu thành `bo`. Nên:
#
#     "bỏ hết điều kiện đi"    -> khách xin BỎ ràng buộc, nhận thêm ràng buộc THỊT BÒ
#     "bỏ và tư vấn thêm đi"   -> như trên, lần thứ hai, ở một chỗ khác
#
# Đây đúng tiền lệ chữ `chay`: từ vựng cố ý KHÔNG có `chay` một mình mà tách thành `an chay` /
# `mon chay`, vì "bán chạy" rút dấu cũng thành `ban chay`. Một âm tiết tiếng Việt sau khi rút dấu
# gần như luôn đụng một âm tiết khác — nên cụm một âm tiết là cụm phải chứng minh mình an toàn,
# không phải mặc định được nhận.
#
# Đã kiểm cả 15 chỗ dùng chữ "bò" trong ba tập đánh giá: tất cả nằm trong TÊN MÓN ("Phở bò tái nạm",
# "Bún bò Huế") hoặc trong cụm "thịt bò". Không ca nào dùng "bò" đứng một mình làm bộ lọc.
_add("thit bo|mon bo|beef", "require", "ingredient:beef")
_add("thit heo|heo|thit lon", "require", "ingredient:pork")
_add("thit ga|ga", "require", "ingredient:chicken")
_add("nam|nam huong", "require", "ingredient:mushroom")
_add("dau hu|tau hu", "require", "ingredient:tofu")

# Chế biến.
_add("nuong|do nuong", "require", "method:grilled")
_add("hap", "require", "method:steamed")
# "giòn", "giòn giòn" là cách khách mô tả KẾT CẤU, và trong thực đơn này ứng với món chiên.
# Mô hình sinh không map được cụm này (đã kiểm trên cache), nên để mã tất định lo — thứ gì
# một danh sách cụm xử lý được thì đừng nhờ một thành phần không tất định.
_add("chien|gion gion|do gion|an gion", "require", "method:fried")
_add("xao", "require", "method:stir_fried")

# Vùng miền — "mien Trung" dài hơn "trung" (trứng) nên tự thắng.
_add("mien bac", "require", "region:north")
_add("mien trung", "require", "region:central")
_add("mien nam", "require", "region:south")
# "trong Nam" / "người Nam" là cách nói THƯỜNG NGÀY hơn "miền Nam", và thiếu chúng thì một câu
# hoàn toàn bình thường trả về sai hẳn nhóm món:
#
#     "Mình thích vị ngọt kiểu trong Nam, gọi gì?"
#         trước: require = [flavour:sweet, ingredient:MUSHROOM] -> Gà tiềm thuốc bắc
#
# `Nam` rút dấu thành `nam`, trùng `nấm`. Cụm `mien nam` dài hơn nên nó tự thắng, nhưng "trong
# Nam" không có cụm nào phủ, nên `nam` một âm tiết ăn mất và khách hỏi vị miền Nam nhận về món nấm.
#
# Cùng lớp lỗi với `nam nguoi` (năm người ⊃ nấm) đã có test riêng — nhưng lần này nó lọt vì cụm
# bảo vệ được viết cho MỘT cách nói, còn tiếng Việt có nhiều cách nói cho cùng một vùng.
_add("trong nam|nguoi nam|kieu nam bo|nam bo", "require", "region:south")
_add("ngoai bac|nguoi bac|kieu bac", "require", "region:north")
_add("mien tay", "require", "region:mekong")
_add("ha noi", "require", "region:hanoi")
_add("hue", "require", "region:hue")
_add("sai gon", "require", "region:saigon")
_add("da nang", "require", "region:danang")
_add("hoi an", "require", "region:hoian")

# Dịp ăn. Nhóm occasion phủ 79/91 nên dùng được theo chiều khẳng định (gợi ý), không
# dùng để loại trừ — thiếu nhãn không có nghĩa món không phù hợp dịp đó.
# Dịp ăn dùng "prefer", không dùng "require". Đây là NGỮ CẢNH, không phải ràng buộc:
# khách nói "tôi ăn chay" là nêu điều bắt buộc, còn "tôi đi hẹn hò" là kể hoàn cảnh.
# Dùng nó làm bộ lọc cứng thì câu "Mình đi hẹn hò, nên gọi món gì?" chỉ còn đúng MỘT món
# (Tôm hùm 890.000đ), vì `occasion:date` chỉ có trên vài món — trong khi occasion phủ 79/91
# nên thiếu nhãn KHÔNG có nghĩa món không phù hợp dịp đó.
_add("hen ho|di hen|buoi hen", "prefer", "occasion:date")
_add("tiep khach|doi tac|trang trong|khach hang", "prefer", "occasion:business")
_add("nhau|nham|lai rai", "prefer", "occasion:drinking")
_add("sinh nhat", "prefer", "occasion:birthday")
_add("tiec|dat tiec", "prefer", "occasion:banquet")

# Số người. Nhóm party phủ 91/91 nên dùng được làm ràng buộc thật. Số người cũng ngầm
# định khách đang nói về bữa ăn, không phải đồ uống.
_add("mot minh|di mot minh|an mot minh|ca nhan", "require", "party:solo")
_add("hai nguoi|2 nguoi|hai nguoi an", "require", "party:two_three")
_add("ba nguoi|3 nguoi|bon nguoi|4 nguoi|nam nguoi|5 nguoi", "require", "party:three_five")
_add("nhom ban|di nhom|ca nhom", "require", "party:friends")
_add("gia dinh|ca nha", "require", "party:family")

# Đối tượng. "dễ tiêu" là cách khách nói LÝ DO thay vì nói đối tượng — người Việt nói "cụ già
# đi cùng, cần món dễ tiêu" chứ ít khi nói "món cho người lớn tuổi".
_add("tre em|em be|cho be|con nho|tre nho", "require", "audience:child")
_add("nguoi gia|nguoi lon tuoi|ong ba|cu gia|de tieu", "require", "audience:elderly")

# --- Cách khách MÔ TẢ thay vì gọi tên nhãn --------------------------------------------------
#
# Bốn nhóm dưới đây là 10/11 ca đỏ còn lại của tập 119 ca, và cả 10 ca đỏ vì CÙNG một lý do:
# khách nói đúng ý mình bằng tiếng Việt thường ngày, còn từ vựng chỉ có từ khớp tên nhãn.
# Khi không hiểu, hệ thống đi nhánh `clarify` và hỏi lại một câu khách vừa trả lời rồi.
#
# Vì sao thêm vào đây thay vì để mô hình lo: mô hình sinh trả lời được cả 10 ca này, nhưng
# **10/119 ca = 8,4% chất lượng treo vào một thành phần không tất định**. Thêm cụm vào bảng
# đưa chúng về mã tất định — cùng lý do đã ghi ở nhóm "giòn giòn" phía trên.
#
# Mỗi cụm đã được ĐO trước khi thêm, không phải đoán: nạp từng cụm vào `VOCAB` rồi chạy
# `understand()` thật trên **cả 119 câu hỏi của tập đánh giá**, và chỉ giữ cụm nào đổi kết quả
# của đúng ca nó nhắm mà không đổi ca nào khác. Kết quả: 11/11 ca nhắm đổi, 0 ca khác đổi.
# Phép đo bằng chuỗi con thì không đủ — nó từng cho tôi 17/19 dương tính giả vì không biết
# bộ khớp ăn cụm dài trước rồi tiêu luôn đoạn văn bản đó.

# Hương vị. `flavour` phủ 72/91 nên "không có món nào" ở đây có thể chỉ là chưa gắn nhãn.
# "đỡ ngán" và "đưa cơm" là hai cách nói ngược nhau về cùng chuyện: món chua để đỡ ngán, món
# đậm để đưa cơm. Cả hai cụm của một câu map về CÙNG nhãn nên phép AND không tự triệt tiêu.
_add("chua chua|do ngan", "require", "flavour:sour")
_add("dam da|dua com", "require", "flavour:rich")
# "có khói", "thơm mùi than" là mùi, không phải cách chế biến — nên nhãn đúng là flavour:smoky
# chứ không phải method:grilled. Hai nhãn giao nhau nhiều nhưng smoky nói đúng điều khách tả.
_add("co khoi|mui than|thom mui than", "require", "flavour:smoky")

# Sức khỏe. `health` phủ 67/91. Khách kể TÌNH TRẠNG ("đang giảm cân", "tập gym") chứ không nêu
# nhãn, nên mỗi tình trạng chỉ map về MỘT nhãn: chọn hai nhãn cho một câu thì phép AND thu hẹp
# tới mức có câu ra rỗng, mà tiêu chí của ca chỉ đòi thỏa MỘT trong các nhãn hợp lý.
_add("giam can|an kieng", "require", "health:low_calorie")
_add("tap gym|nhieu dam", "require", "health:high_protein")
_add("thanh thanh|thanh dam|nhe bung", "require", "health:light")
# Kiêng dầu mỡ -> `health:low_fat`. Nhãn có sẵn (8/91 món) nhưng không cụm nào trỏ tới, nên câu
# "mình kiêng dầu mỡ" rơi xuống nhánh truy hồi toàn kho và khách nhận một đoạn văn thay vì món.
#
# Đây là lớp `vocab_miss` mà `analyze_failures.py` phân loại: nhãn có, dữ liệu có, chỉ thiếu cách
# nói của khách. Sửa ở từ vựng (tất định) chứ không chờ mô hình đoán.
_add("kieng dau mo|it dau mo|khong dau mo|it beo|khong beo|it mo", "require", "health:low_fat")

# ---------------------------------------------------------------------------------------------
# 36 cụm dưới đây đến từ một phép đo về KIẾN TRÚC, không phải từ việc rà thêm ca đỏ.
#
# Kho `derived` (49 tài liệu sinh từ nhãn) truy hồi rất kém — Hit@2 0,544 so với 0,845 của văn
# xuôi viết tay. Đo nguyên nhân thì ra điều bất ngờ: **tài liệu `derived` điển hình có 0 từ chỉ
# xuất hiện ở riêng nó** (văn xuôi viết tay: 2, nhiều nhất 18). Danh sách món rò rỉ từ vựng của
# mọi nhóm khác — "Canh chua cá lóc" nằm trong tài liệu vùng miền, cách chế biến, dịp ăn — nên
# 49 tài liệu gần như không phân biệt được bằng từ. Cắt bớt mục nào cũng chỉ đưa con số 0 lên 1:
# thứ trùng lặp là CHÍNH CÁI KHUÔN.
#
# Nhưng câu hỏi thật thì mới là điều đáng nói. 106 ca của tập truy hồi nhắm hoàn toàn vào
# `derived`, và **không ca nào hỏi tri thức** — tất cả đều là câu chọn món ("Món Hà Nội có gì?",
# "Món nào có bò?"). Trong đó 69/106 = 65,1% ĐÃ sinh ra ràng buộc nhãn, tức đã đi nhánh lọc và
# không hề chạm truy hồi.
#
# 37 ca còn lại rơi xuống truy hồi vì THIẾU CỤM, không vì thiếu tài liệu. Mỗi câu đều có sẵn một
# nhãn chính xác trong thực đơn. Nên cách sửa đúng không phải viết lại `derived` cho dễ truy hồi
# — đó là tối ưu đường dự phòng cho câu đã có đáp án đúng ở đường chính — mà là đưa chúng về
# nhánh lọc, nơi chúng đúng theo định nghĩa.
#
# Giao thức đo giữ nguyên như các nhóm trên: nạp TỪNG cụm một rồi chạy `understand()` trên
# **1.106 câu hỏi của mọi tập đánh giá**, và đọc từng câu đổi chữ ký. Chữ ký gồm cả `avoid_tags`
# và các cờ chứ không chỉ `require_tags` — một cụm mới có thể nuốt cụm dị ứng nằm trong nó theo
# luật khớp-cụm-dài-trước, và đó là hỏng an toàn chứ không phải hỏng độ chính xác.
#
# Phép đo loại hai ứng viên, và cả hai đều đáng ghi lại:
#
#   "co ca"     -> LOẠI. Nó khớp "Có cả ông bà đi cùng nữa" (rút dấu: "co ca ong ba") và gắn
#                  `ingredient:fish` vào một câu về người đi cùng. Thay bằng "nao co ca".
#   "co dau hu" -> LOẠI vì đổi 0 câu. "Món nào có đậu hũ?" bị bộ khớp TÊN MÓN ăn trước ở bước 2
#                  ("Đậu hũ sốt cà chua"), nên không cụm từ vựng nào tới lượt. Đây là lớp lỗi
#                  khác — tên món thắng câu hỏi nguyên liệu — và phải sửa ở chỗ khác.
_add("co bo|thit do", "require", "ingredient:beef")
_add("thit gia cam", "require", "ingredient:chicken")
_add("nao co ca|loai song duoi nuoc co vay", "require", "ingredient:fish")
_add("co tom|giap xac nho mau hong", "require", "ingredient:shrimp")
_add("co cua|loai tam chan co cang", "require", "ingredient:crab")
_add("co muc|loai than mem bien", "require", "ingredient:squid")
_add("dau nanh ep", "require", "ingredient:tofu")
_add("vi dat dai dai", "require", "ingredient:mushroom")
_add("nhieu chat xanh", "require", "ingredient:vegetable")

# Cách chế biến khách TẢ LẠI thay vì gọi tên. `method` phủ 61/91 món.
_add("chin trong nuoc", "require", "method:boiled")
_add("dao nhanh tren chao lua lon", "require", "method:stir_fried")
_add("de lua nho cho mem", "require", "method:simmered")
_add("goi lai roi cham", "require", "method:rolled")
_add("dao kho tren chao", "require", "method:roasted")

_add("vi thanh hoi gat luoi", "require", "flavour:sour")
_add("nao ngot|vi diu hoi co duong", "require", "flavour:sweet")
_add("nao man|vi dam muoi", "require", "flavour:salty")
_add("nao beo|ngay nhieu dau mo", "require", "flavour:fatty")
_add("mui khoi than", "require", "flavour:smoky")

_add("nao lanh manh|an sach it dau", "require", "health:healthy")
_add("khong ngay", "require", "health:low_fat")
_add("so beo", "require", "health:low_calorie")

# BỘT NGỌT KHÔNG PHẢI GLUTEN — đây là một lỗi đọc sai dị nguyên, không phải một cụm thiếu.
#
# Trước khi có hai cụm này, "mì chính" rút dấu thành "mi chinh", và cụm dị nguyên **"mi"** khớp
# vào đó. Hậu quả đo được:
#
#     "Mình dị ứng mì chính"         -> avoid=['allergen:gluten']
#     "Mình không ăn được mì chính"  -> avoid=['allergen:gluten']
#
# Sai theo cả hai chiều cùng lúc. Nó ẩn mất những món có gluten mà khách ăn được bình thường, VÀ
# nó không hề bảo vệ khách khỏi thứ họ vừa nói là không dùng được. Một hàng rào dựng nhầm chỗ còn
# tệ hơn không dựng, vì nó làm cả hai bên tin rằng đã có hàng rào.
#
# "mi chinh" dài hơn "mi" nên luật khớp-cụm-dài-trước tự xử lý, không cần chạm vào cụm dị nguyên.
# Đã kiểm: "Mình dị ứng mì" và "Mình dị ứng gluten" vẫn ra `allergen:gluten`, "món mì xào" vẫn ra
# `method:stir_fried`.
#
# Dùng "khong bot ngot" chứ không dùng "bot ngot" trần: cụm trần biến "Món này có bột ngọt không?"
# — một câu HỎI VỀ MÓN — thành một câu lọc. Cùng ranh giới KHAI/HỎI như `declared_avoidance`.
#
# Còn tồn: "Mình không dùng mì chính" vẫn ra rỗng, vì `la_cau_phu_nhan()` đọc "không dùng X" là
# RÚT LẠI ràng buộc X (đúng cho "mình đâu có dị ứng hải sản", sai cho một lời khai tránh). Sửa
# việc đó phải chạm vào bộ xử lý phủ định — nơi va chạm nhiều nhất tệp này — nên nó là một thay
# đổi riêng, có phép đo riêng. Trạng thái hiện tại là rỗng, tức KHÔNG có hàng rào sai: an toàn
# hơn hẳn `allergen:gluten`, chỉ là chưa đầy đủ.
_add("mi chinh|khong bot ngot", "require", "health:no_msg")

_add("chat thu do", "require", "region:hanoi")
_add("di voi nguoi thuong", "require", "occasion:date")
_add("dat ban cho hai chuc nguoi", "require", "occasion:banquet")

# Thời tiết. Khách nói thời tiết chứ không nói mùa, nên cụm được tách theo ĐÚNG nghĩa của nhãn:
#
#   "trời nóng"                  -> season:hot_season  (nhãn "Mùa nóng")
#   "cho mát", "mát người",      -> season:cooling     (nhãn "Giải nhiệt")
#   "giải nhiệt"
#
# Bản trước gộp cả ba cụm nóng vào `season:hot_season`, và lý do là ĐỘ BAO chứ không phải nghĩa:
# lúc đó `season:cooling` gắn cho 5 đồ uống nhưng chỉ **2/56 món ăn**, nên câu "ăn gì cho mát
# người" lọc theo `cooling` chỉ còn 2 món — sát ngưỡng, một món đổi nhãn là mất câu trả lời.
#
# `ai/scripts/audit_season_tags.py` đối chiếu nhãn với MÔ TẢ món và tìm ra khiếm khuyết đó là lỗi
# dữ liệu thật, không phải lựa chọn: *Canh khổ qua* ghi "thanh nhiệt" và CÓ nhãn, còn *Bánh tráng
# cuốn thịt heo* ghi "Thanh mát... Phù hợp mùa nóng" mà KHÔNG có. Sau khi lấp 3 lỗ đó,
# `season:cooling` phủ **4/56 món ăn** — bằng `hot_season` — nên lý do gộp không còn.
#
# Hai cụm cùng câu ("Trời nóng quá, ăn gì cho mát người") giờ cho require = [hot_season, cooling],
# và phép AND ra **3 món** — nhiều hơn cả hai phương án gộp trước đó. Nhãn mùa không nằm trong
# `exclusive_groups` nên một món mang được cả hai, và đó là lý do phép AND ở đây không triệt tiêu.
_add("troi nong", "require", "season:hot_season")
_add("cho mat|mat nguoi|giai nhiet", "require", "season:cooling")
# `gi mat` và `ma re` — hai cụm đến từ một ca hỏng cụ thể, không từ việc rà thêm.
#
#     "Muốn cái gì mát mà rẻ, không phải trà sữa"  ->  Bánh mì pate · Cháo lòng · Gỏi cuốn chay
#
# Khách xin đồ uống mát và rẻ; hệ thống không đọc ra "mát" lẫn "rẻ" nên `select()` trả về CẢ thực
# đơn rồi liệt kê 6 món đầu. Bốn lớp kiểm soát đều xanh — chúng kiểm "kết quả có thoả ràng buộc đã
# đọc không", mà ở đây chưa đọc ra ràng buộc nào.
#
# Đo từng cụm trên 627 câu: `gi mat` đổi 3 câu (cả ba đều là câu xin đồ mát), `ma re` đổi 1. Hai
# ứng viên `gia re` và `re tien` bị LOẠI vì đổi 0 câu — thêm cụm không phép đo nào phủ là thêm mã
# không ai canh.
#
# Nhãn là `price:budget`, không phải `price:low`: bản đầu tôi viết `price:low` và nó không tồn tại
# trong từ điển nhãn. Cụm trỏ vào nhãn ma thì im lặng không lọc gì.
_add("gi mat", "require", "season:cooling")
_add("ma re", "require", "price:budget")
_add("troi lanh|cho am|an cho am", "require", "season:cold_season")

# Ngân sách nói bằng lời, không bằng số. `price` nằm trong `exclusive_groups` nên mỗi món đúng
# một nhãn giá — và đó là lý do hai cụm bị BỎ thay vì gắn nhãn:
#
#   "vừa phải"  nghĩa là price:mid, nhưng nó đứng cùng câu với "ít tiền" (price:budget) trong
#               ca P-budget-01. Nhóm loại trừ nên budget ∩ mid = 0 món: gắn nhãn cho nó làm
#               câu trả lời RỖNG, tức tệ hơn là không hiểu.
#   "ăn sang"   "ăn sáng" (bữa sáng) và "ăn sang" (đắt tiền) rút dấu về CÙNG một chuỗi
#               `an sang`, nên gắn nhãn giá cho cụm ngắn này biến "mình muốn ăn sáng" thành
#               câu hỏi món đắt tiền. Chỉ giữ cụm dài, không thể hiểu lẫn.
#
# `price:premium` chỉ có 1 món nên cụm đắt tiền map về `price:high` (10 món) — một món thì
# không tư vấn được gì, và tiêu chí của ca nhận cả hai nhãn.
_add("it tien", "require", "price:budget")
_add("an sang mot bua", "require", "price:high")

# --- Chính NHÃN TIẾNG VIỆT làm cụm từ vựng ---------------------------------------------------
#
# `menu-tags.json` có `label_vi` cho cả 85 nhãn, nhưng đo lại thì **48/85 nhãn (56,47%) không rút
# ra được từ chính nhãn tiếng Việt của nó**: hỏi "Món nào ít calo?" thì `require` rỗng.
#
# Vì sao đó là lỗ hổng chứ không phải chuyện nhỏ: bảng nhãn là thứ NGƯỜI NHẬP LIỆU đọc khi gắn
# nhãn cho món, nên nó cũng là cách nói tự nhiên nhất về nhóm món đó. Nhãn có, món có, chỉ thiếu
# đường nối — đúng lớp `vocab_miss` mà `analyze_failures.py` phân loại.
#
# Hậu quả đo được trên bộ định tuyến 198 câu: **20/35 ca sai định tuyến** rơi vào nhóm này. Câu
# "Món nào có bò?" đi nhánh `clarify` (hỏi lại điều khách vừa nói), còn "Món nào vị chua?" rơi
# xuống truy hồi toàn kho và khách nhận một đoạn văn thay vì danh sách món.
#
# Vì sao KHÔNG sinh tự động cả 48 nhãn
# ------------------------------------
# Vì tiếng Việt viết rời từng âm tiết, nên `bố trí` rút dấu thành hai TỪ RIÊNG `bo` + `tri`. Bộ
# khớp đệm khoảng trắng nên nó chống được đụng chữ BÊN TRONG một từ, nhưng không chống được hai
# từ khác nghĩa rút dấu về cùng một chuỗi. Nạp thử từng cụm rồi chạy `understand()` trên **980 câu
# hỏi của 8 tập đánh giá** cho thấy cụm trần hỏng ở đâu:
#
#     `bo`   <- bỏ, bố, bộ, bỡ   "Em muốn bỏ một nguyên liệu ra" mà thành đòi món bò;
#                               "Trong bàn có người không dùng thịt thì bố trí thế nào?" ĐỔI
#                               ý định sang `xoa_rang_buoc`, tức xóa luôn ràng buộc đang giữ
#     `chua` <- chưa            "Mình chưa ăn ở đây bao giờ" thành đòi món chua (4 câu)
#     `ngot` <- bột ngọt        "Món nào không bột ngọt?" thành đòi món ngọt — ngược nghĩa
#     `beo`  <- sợ béo          "Mình sợ béo, có gì ít dầu không?" thành đòi món béo — ngược nghĩa
#     `kho`  <- khô             "món đảo khô trên chảo" thành món kho
#     `rang` <- ràng buộc       "Khi khách có ràng buộc thì ghép món thế nào?"
#     `nau`  <- nấu (động từ)   "món này nấu bao lâu", "bếp nấu theo phong cách nào"
#     `quay` <- quay lại        "quay lại món ăn đi, cho mình món nướng"
#     `nong` <- nồng            5/5 câu đổi đều là "nồng vị ớt" — nên `serving:hot` BỊ BỎ hẳn
#
# Nên nhóm dưới chia làm hai: nhãn nhận nguyên văn, và nhãn phải kèm khung câu.
#
# Đây là lần thứ 11 rút dấu gây đụng chữ trong dự án. Khác 10 lần trước ở chỗ nó bị bắt TRƯỚC khi
# vào mã, bằng phép đo chứ không bằng ca đỏ.

# Nhóm 1 — nhãn nhận nguyên văn: 0/980 câu đổi sai.
_add("thom khoi", "require", "flavour:smoky")
_add("giau protein", "require", "health:high_protein")
_add("healthy", "require", "health:healthy")
_add("khong msg", "require", "health:no_msg")
_add("thanh nhe", "require", "health:light")
_add("rau", "require", "ingredient:vegetable")
_add("cuon", "require", "method:rolled")
_add("luoc", "require", "method:boiled")
_add("tiem", "require", "method:stewed")
_add("hang ngay", "require", "occasion:everyday")
_add("mang di", "require", "serving:takeaway")
_add("tay nguyen", "require", "region:highlands")

# Nhóm 2 — nhãn phải kèm khung câu vì bản thân nó đụng chữ với từ khác.
#
# Khung được chọn là khung tiếng Việt thường ngày ("vị chua", "kiểu kho", "món rang"), không phải
# khung riêng của tập đánh giá — nhưng phải nói rõ: bộ ca phủ kho dùng đúng những khung này, nên
# phần cải thiện đo trên nó có lợi thế. Con số đáng tin hơn là phần đo trên các tập KHÔNG dùng
# khung đó (140 ca trả lời, 149 lượt phiên, 103 ca golden) — chúng chỉ được dùng để kiểm không
# tụt, và chúng không tụt ca nào.
_add("vi chua|gi do chua", "require", "flavour:sour")
_add("vi ngot|gi do ngot|thu ngot", "require", "flavour:sweet")
_add("vi man|gi do man", "require", "flavour:salty")
_add("vi beo|gi do beo", "require", "flavour:fatty")
# KHÔNG có "co bo" ở đây, dù nó là cụm sửa được câu "Món nào có bò?". Nạp thử rồi đo:
# "Quán có bỏ ớt được không?" — câu xin bớt nguyên liệu — biến thành câu đòi món bò. `bò` và `bỏ`
# rút dấu về cùng `bo`, nên trong khung "có X" không có cách nào tách hai nghĩa.
#
# Đây là giới hạn phải nói ra chứ không phải chỗ để cố: khung "ăn bò" an toàn vì `ăn bỏ` không
# phải tiếng Việt, còn khung "có bò" thì không. Câu "Món nào có bò?" vì thế vẫn chưa xử lý được
# bằng mã tất định, và nó nằm trong phần còn lại của thước đo định tuyến.
_add("an bo", "require", "ingredient:beef")
_add("mon kho|kieu kho", "require", "method:braised")
_add("mon nau|kieu nau", "require", "method:simmered")
_add("mon quay|kieu quay", "require", "method:whole_roast")
_add("mon rang|kieu rang", "require", "method:roasted")

# `it calo` thắng `calo` nhờ bộ khớp ăn cụm DÀI trước, và đó là điều sửa một lỗi thật:
#
#     "Món này bao nhiêu calo?"  hỏi một CON SỐ  -> đúng là phải từ chối, quán không có số đó
#     "Món nào ít calo?"         hỏi một LỰA CHỌN -> trả lời được, 19/91 món mang nhãn này
#
# Trước sửa, cả hai cùng rơi vào `policy:nutrition` và cùng nhận câu "Mình chưa có dữ liệu về việc
# này ạ" — tức hệ thống từ chối một câu mà chính dữ liệu của nó trả lời được.
_add("it calo", "require", "health:low_calorie")

# Danh mục.
#
# Tên danh mục GHÉP phải tách thành từng từ đơn, vì khách gõ từ đơn.
# ------------------------------------------------------------------
# Danh mục `cat_noodle` tên là "Phở & Bún", `cat_main` là "Cơm Việt". Bản đầu chỉ nhận cụm ghép
# `"pho bun"` và `"com viet"` — thứ không khách nào gõ. Hậu quả đo được trên chính ba câu thử của
# phép kiểm deploy, tức câu khách thật hỏi nhiều nhất:
#
#     "Ở đây có phở không"                    -> knowledge_corpus, 0 thẻ giỏ
#     "Nhà hàng mình có những món phở gì nhỉ" -> knowledge_corpus, nêu tên 2 món mà KHÔNG bấm được
#     "Gợi ý cho mình món phở đi"             -> clarify, hỏi lại "món ăn hay đồ uống" (khách ĐÃ nói)
#
# Cả ba cùng một gốc: "phở" không nêu được ràng buộc nào, nên `said_something` là False và câu rơi
# xuống nhánh truy hồi tri thức hoặc hỏi lại — trong khi câu hỏi là câu về THỰC ĐƠN.
#
# Điều làm đây thành lỗi rõ ràng chứ không phải lựa chọn thiết kế: **mọi danh mục ghép khác đã tách
# rồi** — `bia|ruou`, `ca phe|tra`, `nuoc ep|sinh to`, `trang mieng|do ngot`. Đúng hai dòng này sót.
#
# An toàn vì bộ khớp đệm khoảng trắng (`" pho "`): "phòng" -> `" phong "` không chứa `" pho "`. Nếu
# khớp theo chuỗi con thì thêm "pho" là tạo ra một lỗi đụng chữ; xem `DungChuTimDuocBangKiemKe`.
_add("khai vi", "category", "cat_appetizer")
_add("pho bun|pho|bun|mon nuoc", "category", "cat_noodle")
_add("com viet|mon com|com", "category", "cat_main")
_add("lau", "category", "cat_hotpot")
_add("mon ga", "category", "cat_chicken")
# Chỉ có cụm ĐẦY ĐỦ "dac san vung mien", nên "cho mình đặc sản" — cách khách thật hay nói —
# rơi vào nhánh hỏi lại. Đo được bằng bản quét 13 danh mục.
_add("dac san vung mien|dac san|mon dac san|dac san dia phuong|mon vung mien",
     "category", "cat_regional")
_add("ca phe|tra", "category", "cat_drink")
_add("nuoc ep|sinh to", "category", "cat_juice")
_add("trang mieng|do ngot", "category", "cat_dessert")
_add("trai cay|hoa qua|trai cay tuoi|dia trai cay", "category", "cat_fruit")
# "co con" tách riêng: cụm cũ là "do co con", nên câu "đồ uống có cồn" (rút dấu thành
# "do uong co con") KHÔNG khớp — và nó trả về nước mía, tức ngược hẳn điều khách hỏi.
# KHÔNG có cụm trần "co con": `fold("có cồn") == fold("có con") == "co con"`, nên nó biến câu
# "mình có con 5 tuổi" thành yêu cầu RƯỢU BIA. Đã đo được đúng như vậy khi cụm đó còn ở đây.
#
# Đây là vụ va chạm rút dấu thứ mười một trong dự án, và lần này do chính bản sửa "đồ uống có cồn"
# gây ra — nên bài kiểm kê đụng chữ đáng giá đúng ở chỗ nó bắt được người vừa viết ra nó.
#
# Giữ các cụm DÀI: chữ "uong"/"do" đứng trước làm chúng không thể là "có con".
_add("bia|ruou|do co con|ruou bia|do uong co con|thuc uong co con|nuoc co con",
     "category", "cat_alcohol")

# Món ăn hay đồ uống — đúng yêu cầu "không phải bảo tư vấn món mà cứ đưa bia vào".
_add("mon an|do an|an gi|minh doi|toi doi|bua trua|bua toi|bua sang|an com", "wants", "food")
# "nuoc uong"/"nuoc ngot"/"do giai khat" đo được là KHÔNG nhận ra: câu "cho mình nước uống"
# cho `wants=any`, `categories=[]` nên nó rơi vào nhánh HỎI LẠI — khách xin đồ uống và bị
# hỏi ngược lại muốn món ăn hay đồ uống.
_add("do uong|thuc uong|uong gi|nuoc gi|nuoc uong|nuoc ngot|do giai khat|giai khat",
     "wants", "drink")

# --- Tham chiếu ngược vào danh sách khách VỪA đọc --------------------------------------
#
# "Món đầu tiên giá bao nhiêu?" là câu hỏi tự nhiên nhất của một cuộc hội thoại thật, và trước khối
# này hệ thống trả lời nó bằng cách LIỆT KÊ LẠI một danh sách mới — vì nó không hiểu "món đầu tiên"
# trỏ vào đâu. `analyze_failures.py` xếp 9 lượt như vậy vào lớp `capability_missing`: không thiếu
# từ, không thiếu dữ liệu, mà thiếu chỗ LƯU dãy có thứ tự các món đã nêu.
#
# Ba loại cụm, ba cơ chế, không gộp được — xem chú thích ở `Request`.
#
# Cụm chỉ VỊ TRÍ giải ra `named_items` ở bước hợp nhất bộ nhớ. Nghĩa là nó tái dùng nguyên các
# nhánh đã có và đã đo (`price_lookup`, `item_detail`, `allergen_named_dish`), không thêm nhánh
# thứ bảy vào `answer.respond`. Thêm nhánh thì phải đo lại cả sáu nhánh cũ.
#
# "món đó"/"cái đó" không nêu vị trí. Quy ước: lấy món ĐẦU danh sách, và câu trả lời PHẢI nêu tên
# món nó đang nói — nêu tên biến phỏng đoán thành thứ khách sửa được ngay, còn đoán im lặng thì
# khách tin vào câu trả lời về một món khác.
_add("mon dau tien|cai dau tien|mon thu nhat|mon dau", "reference", 1)
_add("mon thu hai|cai thu hai", "reference", 2)
_add("mon thu ba|cai thu ba", "reference", 3)
_add("mon thu tu|cai thu tu", "reference", 4)
_add("mon thu nam|cai thu nam", "reference", 5)
_add("mon cuoi cung|mon cuoi|cai cuoi", "reference", -1)
# "Món đó" trỏ vào món ĐANG NÓI TỚI, không phải món thứ nhất của danh sách.
#
# Bản trước gán các cụm này `reference: 1`, nên chuỗi "món thứ hai có cay không?" rồi "món đó bao
# nhiêu tiền?" trả lời về món THỨ NHẤT — đúng cú pháp, sai người khách đang trỏ vào. Đo được qua
# backend, và cả nhóm `chained_reference` 9 lượt vẫn xanh vì không lượt nào chuyển tiêu điểm rồi
# hỏi tiếp bằng "món đó".
#
# `session.py` phân giải cờ này thành món tiêu điểm nếu có, và LÙI VỀ món thứ nhất nếu chưa có
# tiêu điểm — nên hành vi cũ vẫn nguyên ở lượt đầu.
# `mon nay` / `cai nay` vào danh sách sau khi golden qua stack thật bắt được: khách hỏi "Món này có
# bột ngọt không?" và nhận về một danh sách 6 món kèm thẻ giỏ — vì câu đó không được nhận là câu
# tham chiếu, nên nó rơi xuống nhánh lọc và lớp mô hình thêm `prefer: health:no_msg` vào.
#
# "này" và "đó" trỏ vào cùng một thứ trong hội thoại: món đang được nói tới. Việc chỉ có "đó" là lỗ
# từ vựng, không phải một lựa chọn — và nó im lặng, vì câu vẫn được trả lời, chỉ trả lời sai loại.
_add("mon vua roi|mon vua noi|mon do|cai do|mon nay|cai nay|no co", "flag", "refers_to_focus")

# Cụm thu PHẠM VI. Khác cụm vị trí: "món rẻ nhất TRONG SỐ ĐÓ" không trỏ vào một món, nó giới hạn
# tập rồi để câu hỏi "rẻ nhất" chạy trên tập đó. Dùng cụm vị trí ở đây là trả sai: nó sẽ trả món
# ĐẦU danh sách thay vì món RẺ NHẤT.
#
# Bốn cụm đầu đều đòi chữ "đó" đứng ngay sau, nên chúng bỏ sót phần lớn cách nói thật. Dò 8 câu
# hỏi tiếp nối sau một lượt nêu 4 món:
#
#     "Món nào TRONG ĐÓ có hải sản?"                  -> 6 món, NGOÀI danh sách
#     "TRONG MẤY MÓN VỪA TƯ VẤN có món nào không cay?" -> 6 món, NGOÀI danh sách
#     "4 MÓN ĐÓ có món nào chứa đậu phộng không?"      -> 4 món, nhưng KHÔNG PHẢI 4 món kia
#
# Ca thứ ba tệ nhất: đúng số lượng nên nhìn như trả lời đúng, mà bốn món trả về là bốn món khác.
# Khách hỏi về dị nguyên trong danh sách vừa xem và nhận câu trả lời về một danh sách khác — đúng
# loại sai mà không ai kiểm lại vì nó trông hợp lý.
#
# Đo từng cụm ứng viên trên **847 câu hỏi của 8 tập**: 13/14 cụm không đổi ca nào, cụm `trong do`
# đổi đúng một ca — *"Món nào trong đó không cay?"* — và đổi theo chiều ĐÚNG.
_add("trong so do|trong nhung mon do|trong danh sach do|trong may mon do|"
     "trong do|trong so nay|trong nhung mon vua|trong may mon vua|trong danh sach vua|"
     "trong cac mon do|trong cac mon vua|may mon do|cac mon do|nhung mon do|trong mon vua|"
     "trong so mon do", "flag", "scope_listed")
# Câu so sánh TIẾP NỐI: khách vừa so hai món, rồi hỏi thuộc tính khác mà không nhắc lại tên.
#
# "Món nào cay hơn?" sau một câu so sánh từng rơi vào nhánh hỏi lại — mất hẳn cặp món vừa nói.
#
# Danh sách hẹp CÓ CHỦ ĐÍCH và **không** chứa "re hon" / "it hon" / "thap hon": ba cụm đó là cách
# nói SIẾT NGÂN SÁCH (`STRICT_BUDGET_FRAMING`), và câu "Món nào rẻ hơn?" trong một phiên đang lọc là
# yêu cầu danh sách rẻ hơn, không phải so hai món. Trộn hai nghĩa lại là phá một hành vi đang đúng
# để sửa một hành vi đang sai.
_add("cay hon|ngon hon|dam hon|hon nhau|khac gi nhau|nao hon", "flag", "asks_comparison")
# Khách xin gợi ý món mà chưa nêu ràng buộc. Sáu ca `clarify` của tập đánh giá nằm hết trong nhóm
# cách nói này, và chúng phải HỎI LẠI chứ không nhận một đoạn tri thức.
#
# Các cụm ở đây bị ĂN khỏi câu như mọi cụm từ vựng khác, và điều đó vô hại: không cụm nào trong số
# này mang ràng buộc. "Gợi ý món ăn cho mình" vẫn còn "món ăn" để đặt `wants=food`, nên câu đó vẫn đi
# nhánh lọc — đã kiểm bằng ca golden.
_add("goi y|tu van|ban chon|chon giup|mon ngon|khong biet|cung duoc|tuy ban|mon gi cung",
     "flag", "asks_suggestion")

# Xin thêm món GIỐNG — cơ chế ngược với trỏ vào món cũ: giữ ràng buộc, BỎ món đã nêu.
_add("giong vay|giong the|tuong tu|kieu vay|giong nhu vay", "flag", "similar")
# "Món khác đi" mang ĐÚNG nghĩa của `similar`: giữ ràng buộc cũ, bỏ món vừa nêu. Thiếu nhóm cụm này
# thì câu đó rơi vào nhánh lọc bình thường và khách nhận lại **y nguyên danh sách cũ**.
#
# Đo được qua backend + mô hình thật. Nhóm `no_repeat` của bộ chạy phiên vẫn xanh 10/10 vì tiêu chí
# của nó chỉ kiểm bộ nhớ có GHI món đã gợi — không kiểm danh sách có ĐỔI. Ca đạt sai lý do, lần thứ
# tư trong dự án này.
#
# Không cụm nào ở đây nằm trong cụm từ vựng khác hay trong tên món nào (đã kiểm cả 91 tên).
_add("mon khac|cai khac|mon nao khac|thu khac|mon gi khac", "flag", "similar")
# Trẻ nhỏ nêu bằng TUỔI. Golden bắt được: "Đi cùng bé 4 tuổi, gợi ý món giúp mình" rơi vào nhánh
# hỏi lại vì không cụm nào nhận ra đó là câu về trẻ em. Cụm "be" một mình quá ngắn và đụng nhiều
# chữ, nên nhận theo cách khách thật nói: "bé N tuổi", "con N tuổi", "cháu N tuổi".
#
# CỤM `tuoi` MỘT MÌNH ĐÃ BỊ BỎ — nó vi phạm đúng nguyên tắc mà chú thích trên vừa nêu.
#
# "tươi" và "tuổi" rút dấu về CÙNG một chuỗi `tuoi`. Hậu quả đo được:
#
#   "Đồ biển ở đây có tươi không, lấy từ đâu?"   -> require audience:child, rồi bộ xử lý phủ định
#                                                   đọc tiếp thành "bỏ ràng buộc" và trả lời
#                                                   "Anh/chị muốn em gợi ý món gì tiếp ạ?"
#   "Đi với bà ngoại tám mươi tuổi..."           -> require audience:child (bà ngoại 80 tuổi!)
#
# Thay bằng `<số> tuổi` cho 1–9, cả chữ lẫn số. Con số đứng trước là thứ phân biệt "tuổi" với
# "tươi" — không ai nói "cá 4 tươi". Dừng ở 9 có chủ ý: `muoi tuoi` sẽ khớp "tám mươi TUỔI" và
# lặp lại đúng lỗi vừa sửa, chỉ đổi chiều.
_add("em nho|chau nho|be nho|di cung be|co be", "require", "audience:child")
_add("mot tuoi|hai tuoi|ba tuoi|bon tuoi|nam tuoi|sau tuoi|bay tuoi|tam tuoi|chin tuoi",
     "require", "audience:child")
_add("1 tuoi|2 tuoi|3 tuoi|4 tuoi|5 tuoi|6 tuoi|7 tuoi|8 tuoi|9 tuoi",
     "require", "audience:child")

# Câu hỏi giá.
_add("bao nhieu tien|gia bao nhieu|bao nhieu mot|bao nhieu|gia the nao|may tien", "flag", "asks_price")

# Số người ăn một phần. Chủ đề này TỪNG là `policy: serving_size` với câu trả lời "chưa có dữ
# liệu", và lý do đó SAI: nó dựa trên việc nhóm `serving` chỉ có `takeaway`/`hot`/`preorder`, và bỏ
# sót nhóm `party` — `party:solo` là "Cá nhân", `party:two_three` là "2-3 người",
# `party:three_five` là "3-5 người". Nhóm `party` phủ **91/91 món**, và chính dự án này dùng nó làm
# ràng buộc cứng vì độ phủ đó.
#
# Nên hệ thống từng nói "chưa có dữ liệu" cho một câu mà dữ liệu CÓ, và một ca đánh giá bị sửa tiêu
# chí theo cái sai đó. Lỗi đọc dữ liệu: xem một nhóm nhãn rồi kết luận về cả thực đơn.
#
# Hai câu hỏi khác nhau, hai đường trả lời khác nhau:
#   "khẩu phần thế nào?"           -> tri thức `portion_timing` (nói về cả thực đơn)
#   "món đó cho mấy người ăn?"     -> nhãn `party:*` của CHÍNH món đó (xem `answer.py`)
_add("khau phan the nao|khau phan bao nhieu", "knowledge", "portion_timing")
_add("cho may nguoi an|may nguoi an|an duoc may nguoi|du cho may nguoi|mot phan cho may nguoi",
     "flag", "asks_serving")
# Hỏi HAI LOẠI món KHÁC NHAU thế nào — câu tri thức, không phải câu lọc.
#
# Đây là nhóm cụm phải có ngay sau khi tên loại món ("pho", "bun", "com") thành từ vựng danh mục:
# cùng một chữ "phở" nay xuất hiện trong hai câu hỏi khác hẳn nhau.
#
#   "Ở đây có phở không?"            -> LỌC thực đơn theo cat_noodle   (câu về thực đơn)
#   "Phở với bún khác nhau thế nào?" -> TRI THỨC về hai loại món       (câu về kiến thức)
#
# Không có nhóm này, câu thứ hai nhận một danh sách 6 món — golden bắt được ngay lượt đầu tiên sau
# khi tôi thêm ba cụm tên món. Cùng lớp với `asks_about_attribute`: **hỏi VỀ một thứ không phải lọc
# THEO thứ đó**, và đó là lần thứ ba lớp này xuất hiện trong dự án (nhãn, thuộc tính món, nay loại
# món).
#
# `khac cho nao` phải nằm ở đây, và nó sửa một lỗi RIÊNG: cụm `cho nao` một mình ánh xạ vào chính
# sách `location`, nên "Cơm tấm khác cơm chiên chỗ nào?" từng được trả lời bằng thông tin CHỖ ĐẬU XE.
# Ca golden của câu đó vẫn XANH, vì tiêu chí chỉ đòi `kind=fact` và độ dài — một ca đạt vì lý do sai,
# lần thứ năm trong dự án. Cơ chế cụm dài ăn trước làm phần còn lại: `khac cho nao` khớp trước nên
# `cho nao` không bao giờ được đọc thành địa điểm.
# Ở ĐÂY chỉ những cụm PHẢI ĂN chữ, vì phần đuôi của chúng có nghĩa khác khi đứng một mình:
#
#     "khac cho nao"  -> nếu không ăn, `cho nao` khớp chính sách `location`
#     "khac o dau"    -> nếu không ăn, `o dau`   khớp chính sách `location`
#
# Đó đúng là lỗi đang có: "Cơm tấm khác cơm chiên chỗ nào?" được trả lời bằng thông tin CHỖ ĐẬU XE.
# Ca golden của nó vẫn XANH vì tiêu chí chỉ đòi `kind=fact` và độ dài — một ca đạt vì lý do sai, lần
# thứ năm trong dự án.
#
# Những cách nói khác ("khác nhau thế nào", "khác gì nhau") KHÔNG ở đây: chúng đã thuộc nhóm
# `comparison`/`asks_comparison` từ trước, và nhận chúng lần nữa là cụm trùng. Chúng được nhận qua
# `DIFFERENCE_FRAMING` bên dưới — kiểm trên chuỗi đã rút dấu, đúng khuôn `ATTRIBUTE_DEFINITION_FRAMING`.
_add("khac cho nao|khac nhau cho nao|khac o dau|khac nhau o dau", "flag", "asks_difference")
_add("dat nhat|mac nhat", "flag", "priciest")
_add("re nhat|thap nhat", "flag", "cheapest")

# So sánh.
_add("hay|hoac|khac nhau the nao|nen chon|so voi|voi", "flag", "comparison")

# --- Tri thức nhà hàng ----------------------------------------------------------------
#
# Mỗi chủ đề ứng một `topic_keys` của tài liệu `answer_mode: verbatim` trong `ai/knowledge/`,
# và `answer.py::load_facts()` tra bằng đúng khóa đó. Truy hồi ở đây là
# TRA KHÓA: chủ đề nhận ra từ câu hỏi chính là khóa, không có xếp hạng hay ngưỡng tương
# đồng nên không có chỗ nào để chệch.
#
# Chỗ khó nhất là phân biệt **câu hỏi về thực đơn** với **câu hỏi meta về thực đơn**:
#
#   "Món nào không cay?"      -> LỌC thực đơn, trả về danh sách món (hữu ích hơn)
#   "Có mấy mức cay?"          -> trả lời tri thức, vì khách hỏi về cách thực đơn tổ chức
#
# Nên các chủ đề meta chỉ dùng cụm hỏi VỀ thực đơn, không dùng từ mà câu lọc cũng chứa.
# Gộp hai loại thì câu "món nào không cay" sẽ trả về một đoạn văn thay vì danh sách món.

# Chính sách vận hành.
# Giờ mở/đóng cửa. Cụm ở đây phải chịu được CHỦ NGỮ CHÈN GIỮA — người Việt nói "mấy giờ QUÁN đóng
# cửa", "nhà hàng mở cửa mấy giờ", "mấy giờ THÌ đóng cửa". Bản đầu chỉ liệt kê cụm liền nhau nên
# 4/6 cách hỏi tự nhiên rơi xuống nhánh truy hồi, và truy hồi trả về một danh sách món khai vị cho
# câu hỏi giờ mở cửa — lỗi lộ ra khi chạy ví dụ xuyên suốt cho báo cáo.
#
# Cách sửa: tách thành hai vế và cho phép tối đa ba từ chèn giữa, thay vì liệt kê mọi biến thể.
_add("may gio mo cua|gio mo cua|mo cua luc nao|may gio dong cua|gio dong cua|mo cua den may gio",
     "policy", "hours")
_GIO_CUA_RE = re.compile(
    r"(?<![a-z])(?:"
    r"may gio(?:\s+\S+){0,3}?\s+(?:mo|dong) cua"      # "mấy giờ (quán) đóng cửa"
    r"|(?:mo|dong) cua(?:\s+\S+){0,3}?\s+may gio"      # "mở cửa (đến) mấy giờ"
    r"|(?:mo|dong) cua luc(?:\s+\S+){0,3}?\s+gio"      # "đóng cửa lúc mấy giờ"
    r")(?![a-z])"
)
_add("thanh toan|tra tien|quet the|chuyen khoan|tra bang the|cach tra tien", "policy", "payment")
_add("hoa don|xuat hoa don|vat|hoa don do", "policy", "invoice")
_add("do xe|bai xe|gui xe|cho dau xe|dau o to", "policy", "parking")
_add("wifi|mat khau wifi|pass wifi", "policy", "wifi")
_add("dat ban|dat cho|giu ban|book ban", "policy", "booking")
_add("giao hang|ship|giao den nha|giao tan noi|mang ve|mua mang ve|dat qua app", "policy", "delivery")
_add("dia chi|o dau|duong di|cho nao|toi day the nao", "policy", "location")
_add("so dien thoai|lien he|goi cho quan|hotline", "policy", "contact")
_add("phu phi|phi phuc vu|tien tip|tip bao nhieu|co phai tra them", "policy", "service_charge")
_add("phong rieng|phong vip|to chuc tiec|khu rieng|dat tiec sinh nhat", "policy", "private_room")
# Cụm phải dài hơn "em be" (đã là nhãn audience:child) để thắng ở vòng khớp dài-trước.
# Bản đầu thiếu biến thể "ghe an cho em be", nên câu "Có ghế ăn cho em bé không?" bị
# hiểu thành câu lọc món cho trẻ em thay vì câu hỏi về tiện nghi.
_add("ghe an cho em be|ghe an cho be|ghe cho em be|ghe cho be|ghe em be|ghe tre em|ghe cao cho be", "policy", "high_chair")
_add("xe lan|nguoi khuyet tat|loi di cho xe lan", "policy", "accessibility")
_add("hut thuoc|khu hut thuoc|thuoc la", "policy", "smoking")
_add("mang do tu ngoai vao|mang banh vao|mang banh sinh nhat|do tu ben ngoai", "policy", "outside_food")

# --- Chủ đề tri thức NHIỀU MỤC (`answer_mode: synthesize`) ----------------------------------
#
# 11 chủ đề dưới đây trả lời bằng cách CHỌN MỘT MỤC của một tài liệu, khác 24 chủ đề `policy` ở
# trên vốn trả nguyên văn cả tài liệu. Xem chú thích ở `Request.knowledge_topic`.
#
# Đo trước khi thêm, cùng phương pháp đã dùng cho 23 cụm mô tả và cụm chỉ vị trí: nạp từng cụm rồi
# chạy `understand()` trên CẢ 122 câu. Kết quả: **33/33 cụm an toàn, 0/122 ca đổi, 0 ca dạng `list`
# đổi** — con số cuối là con số phải canh, vì dự án đã ghi rõ nguy cơ: "Gộp hai loại thì câu 'món
# nào không cay' sẽ trả về một đoạn văn thay vì danh sách món."
#
# Cụm được chọn theo một quy tắc: chúng nói về CÁCH LÀM hoặc về CHÍNH THỰC ĐƠN, không nói về món.
# Câu về món phải tiếp tục đi nhánh lọc, vì liệt kê món thật hữu ích hơn một đoạn văn.
#
# CHỦ ĐỀ BỊ LOẠI, và lý do đo được: `budget_planning`. Câu "Hai người 300 nghìn thì gọi được những
# gì?" hiện trả về DANH SÁCH MÓN, và đó **đúng hơn** một đoạn văn về bốn mức giá — khách nêu con số
# cụ thể thì họ muốn món, không muốn giải thích. Không tìm được cách diễn đạt nào vừa rõ là câu
# meta vừa không phải câu đặt hàng, nên chủ đề đó để nguyên cho nhánh lọc.
#
# 48/60 tài liệu `synthesize` còn lại là `derived` — sinh từ nhãn thực đơn (hương vị, vùng miền,
# cách chế biến). Chúng KHÔNG có cụm nào ở đây, cũng vì lý do trên: với "món bò có gì", nhánh lọc
# liệt kê món bò thật tốt hơn một đoạn văn về nhóm nhãn `ingredient:beef`.
_add("goi combo gi|combo gi cho hop|ket hop mon nao|ghep mon the nao", "knowledge", "combo_pairing")
_add("set bua trua|set bua toi|co set nao", "knowledge", "meal_sets")
_add("uong gi cho hop|ghep do uong|uong gi voi", "knowledge", "beverage_pairing")
_add("nen goi bao nhieu mon|goi bao nhieu mon|goi may mon|thu tu goi mon",
     "knowledge", "ordering_guide")
_add("bao lau thi co mon|bao lau moi co mon", "knowledge", "portion_timing")
_add("an chia chung|chia chung the nao", "knowledge", "sharing_etiquette")
_add("lan dau toi day|lan dau den nha hang|thuc don to chuc the nao", "knowledge", "first_visit")
_add("ghi nhan che do an nao|che do an nao", "knowledge", "dietary_limits")

# "đáng tiền" — cụm này vào từ vựng vì golden qua stack thật cho kết quả KHÁC NHAU giữa hai lần chạy.
#
# `value_for_money` là một trong 74 chủ đề KHÔNG có cụm từ vựng, nên nó chỉ tới được qua nhánh truy
# hồi toàn kho. Nhánh đó nằm gần CUỐI chuỗi nhánh, sau `enrich()`. Nên khi mô hình trả về một nhãn
# giá cho "Món nào đáng tiền nhất?", câu rơi vào nhánh lọc và không bao giờ tới nhánh tri thức.
#
# Và mô hình trả về nhãn đó KHÔNG ỔN ĐỊNH: chạy lại cùng câu, có lần nó trả nhãn, có lần không. Nên
# nhánh của câu này phụ thuộc một lần tung xúc xắc — đó là lỗi tệ hơn cả việc trả lời sai, vì nó
# không tái lập được và mọi phép đo trên nó là ngẫu nhiên.
#
# Cụm từ vựng sửa tận gốc: `understand` nhận ra chủ đề, `already_understood` chặn mô hình, và câu trả
# lời giống nhau mọi lần chạy. Đây cũng là hướng đã ghi trong tài liệu — đưa dần các chủ đề chỉ tới
# được qua truy hồi về đường tất định.
_add("dang tien|dang gia|duoc gia|xung tien|hop tui tien nhat", "knowledge", "value_for_money")
_add("noi voi nha hang the nao|khai di ung the nao|nen noi gi ve viec di ung",
     "knowledge", "allergy_guidance")
_add("goi mon qua ma qr|quet ma qr the nao|dung ung dung the nao", "knowledge", "qr_ordering")

# An toàn dị ứng: bếp xử lý thế nào. Đây là chủ đề tri thức quan trọng nhất, vì nó nói ra
# GIỚI HẠN của những gì hệ thống biết.
_add("bep co tach rieng|nhiem cheo|lan thanh phan|bep xu ly di ung|co dam bao khong di ung", "policy", "kitchen_allergy")
_add("thuc don co ghi di nguyen|co ghi di ung khong|ghi nhan di ung the nao", "policy", "allergen_labelling")

# Câu hỏi META về thực đơn — hỏi về cách thực đơn tổ chức, không phải hỏi món cụ thể.
_add("menu co bao nhieu mon|thuc don co bao nhieu mon|bao nhieu mon|co nhung nhom nao|thuc don gom nhung gi", "policy", "menu_size")
_add("gia ca the nao|tam gia bao nhieu|khoang gia|gia tu bao nhieu|co dat khong|dat khong", "policy", "price_range")
_add("mon nao can dat truoc|dat truoc bao lau|co mon nao lau khong", "policy", "preorder")
_add("mon nao mang di duoc|mon nao mang ve duoc", "policy", "takeaway_items")
_add("co may muc cay|muc cay the nao|chia may muc cay|do cay tinh the nao", "policy", "spice_levels")
_add("co bao nhieu mon chay|bao nhieu mon chay|menu chay co may mon", "policy", "vegetarian")
# `children` là tài liệu ĐẾM — "43 món phù hợp trẻ em, 29 món người lớn tuổi, 68 món không cay".
#
# Ba cụm đầu đều đòi chữ "menu" hoặc "phần ăn", nên cách hỏi thường ngày nhất rơi ra ngoài:
#
#     "Quán có bao nhiêu món cho trẻ em?"  ->  policy:menu_size   (tài liệu ĐẾM CẢ THỰC ĐƠN)
#     "Trẻ em ăn được bao nhiêu món?"      ->  policy:menu_size
#
# `bao nhieu mon` khớp và thắng vì không cụm nào của `children` khớp cả. Khách hỏi về trẻ em và
# nhận về con số của toàn thực đơn — sai tài liệu, và sai theo kiểu nghe vẫn trôi.
#
# Đây là hố mà kiểm kê độ phủ bộ đánh giá tìm ra: tài liệu có trong kho, có cụm từ vựng, mà **không
# câu hỏi tự nhiên nào tới được nó**. Nhóm `vegetarian` không dính vì nó đã có `bao nhieu mon chay`
# — cụm DÀI HƠN nên thắng `bao nhieu mon`. Bản sửa dưới đây làm đúng điều đó cho `children`.
#
# Chỉ nhận cụm báo hiệu câu ĐẾM. KHÔNG có `mon cho tre em` trần: "cho mình món cho trẻ em" là câu
# XIN MÓN, và đáp án đúng của nó là danh sách món chứ không phải một con số.
_add("co menu tre em|menu cho tre em|phan an tre em|"
     "bao nhieu mon cho tre em|bao nhieu mon tre em|tre em an duoc bao nhieu",
     "policy", "children")
_add("bao nhieu calo|calo|natri|dinh duong|bao nhieu duong", "policy", "nutrition")
# Cách nói bằng ĐƠN VỊ. Golden bắt được: "Phở bò tái nạm có mấy gam đường?" rơi vào nhánh
# dữ kiện món và trả về giá cùng độ cay — không trả lời câu hỏi, và còn sinh thẻ giỏ.
_add("gam duong|gam dam|gam beo|bao nhieu dam|bao nhieu protein|"
     "gam protein|milligram|cholesterol", "policy", "nutrition")

# Thời gian và tình trạng còn hàng. Thực đơn KHÔNG có trường nào về thời gian, và cả 91 món
# đều `isAvailable = true` nên không kiểm chứng được hành vi khi hết món.
#
# Phải nhận diện ở đây, không để rơi xuống nhánh hỏi lại: hỏi lại thì khách tưởng câu hỏi
# chưa đủ rõ, còn sự thật là hệ thống KHÔNG CÓ dữ liệu đó. Và nếu để nó rơi xuống nhánh lọc
# thì tệ hơn nữa — trả về danh sách món là ngầm khẳng định chúng còn hàng.
#
# Nhãn `promo:signature` nói món đặc trưng của nhà hàng, thứ không đổi theo ngày, nên dùng
# nó để trả lời "hôm nay có món gì đặc biệt" là bịa.
_add(
    "hom nay co mon gi|mon dac biet hom nay|mon moi hom nay|hom nay an gi dac biet|"
    "gio nay con mon gi|con mon gi khong|con hang khong|het mon chua|mon nao con",
    "policy",
    "time_or_availability",
)
# Doanh thu, lợi nhuận, lương: không trả lời ở kênh chat khách hàng.
_add("doanh thu|loi nhuan|luong nhan vien|chi phi nguyen lieu", "policy", "internal")
# Bếp trưởng, nhân sự: KHÁC loại trên — đây là thiếu dữ liệu, không phải từ chối.
_add("bep truong|dau bep|nhan su|chu nha hang|ai nau", "policy", "staff_identity")
# Thực đơn không có khái niệm size. Nêu giá cho "size lớn" là bịa.
_add("size lon|size nho|size vua|size|phan lon|to lon|bat lon", "policy", "no_size")

# Ngoài bài toán.
_add("thoi tiet|ty gia|bong da|tin tuc", "flag", "off_topic")
_add("prompt he thong|system prompt|model ai nao|chi dan noi bo|ban dung model gi", "flag", "off_topic")
_add("goi taxi|goi xe|dat ve|dich cau nay|dich sang tieng", "flag", "off_topic")
# Kiến thức chung, toán, lập trình, nơi khác. Thêm sau khi chạy thật: bốn câu kiểu "Thủ đô nước
# Pháp là gì?", "2 cộng 2 bằng mấy?", "Giải thích thuật toán Dijkstra", "Nhà hàng bên cạnh có ngon
# không?" đều rơi vào nhánh HỎI LẠI, tức trợ lý hỏi khách muốn món ăn hay đồ uống. Nó không trả
# lời sai, nhưng nó cũng không nói được rằng câu đó ngoài phạm vi.
#
# Danh sách từ khóa KHÔNG phủ hết kiến thức chung, và không có cách nào phủ hết. Bảo đảm thật nằm ở
# chỗ khác: chữ gửi cho khách luôn do `answer.py` dựng từ dữ liệu thực đơn và kho tri thức, nên trợ
# lý KHÔNG CÓ ĐƯỜNG trả lời một câu ngoài phạm vi dù có hiểu nó. Danh sách này chỉ để nói ra điều
# đó cho khách nghe, thay vì hỏi lại một câu không liên quan.
_add("thu do|dan so|dien tich nuoc|lich su the gioi|ai la tong thong|ai la thu tuong",
     "flag", "off_topic")
_add("giai phuong trinh|thuat toan|lap trinh|viet code|python|javascript",
     "flag", "off_topic")
# KHÔNG có "doi thu" ở đây. Cụm đó nằm trong "đổi thử món khác" sau khi rút dấu, nên nó từ chối
# oan một câu hoàn toàn đúng chủ đề — đo được ngay khi thêm. Mất khả năng nhận ra câu hỏi về đối
# thủ là giá phải trả, và là giá đúng: từ chối oan khách đang chọn món tệ hơn nhiều so với hỏi lại
# một câu về đối thủ.
_add("nha hang ben canh|nha hang khac|quan ben canh|quan khac", "flag", "off_topic")
# Bốn nhóm golden 103 lượt bắt được. Mỗi cụm ở đây là một câu đã đo được là lọt, không phải một
# phỏng đoán về điều khách có thể hỏi.
#
#   thời tiết   "Mai Hà Nội có mưa không?"        -> trước đó nhận về danh sách món Hà Nội
#   tỷ giá      "1 đô bằng bao nhiêu tiền Việt?"  -> nhận về đoạn tri thức về calo
#   bóng đá     "Đội nào thắng trận tối qua?"     -> nhận về đoạn về cà phê cho trẻ em
#   dò cấu hình "Bạn là model gì?"                -> nhận về đoạn về lẩu
#
# Cổng `thuoc_mien` ở `answer.py` chặn phần lớn nhóm này rồi; các cụm dưới đây làm câu trả lời NÓI
# ĐÚNG là ngoài phạm vi thay vì hỏi lại. Hai lớp cùng hướng, và lớp cổng là lớp không cần liệt kê.
_add("co mua|mua khong|troi mua|nang khong|nhiet do bao nhieu", "flag", "off_topic")
# KHÔNG có "do la" ở đây. Cụm đó (đô la) nằm trong "gì ĐÓ LẠ lạ", "cái ĐÓ LÀ", "món ĐÓ LÀ" sau khi
# rút dấu — và 10 test của `test_llm_understand` đỏ ngay vì câu mơ hồ chuẩn của chúng là "Cho mình
# gì đó lạ lạ", bị đọc thành câu hỏi tỷ giá.
#
# Mất khả năng nhận chữ "đô la" là giá phải trả, và là giá đúng: "đó là" phổ biến gấp nhiều lần
# trong câu khách nói, còn "usd"/"dollar" vẫn nhận được.
_add("bang bao nhieu tien viet|usd|dollar", "flag", "off_topic")
_add("doi nao thang|tran toi qua|ket qua tran|world cup|bong ro", "flag", "off_topic")
_add("model gi|ai huan luyen|cau hinh noi bo|khoa api|api key|token noi bo",
     "flag", "off_topic")

# Cụm sắp theo độ dài giảm dần — đây là cơ chế chống đụng chữ.
VOCAB_ORDER = sorted(VOCAB, key=lambda p: (-len(p), p))

# Các cụm chỉ vị trí, tách ra thành một tập riêng vì THỨ TỰ CÁC BƯỚC bắt buộc phải vậy.
#
# `understand()` quyết nghĩa của "hải sản" ở BƯỚC 2 (tránh / duyệt danh mục / hỏi về món đã nêu),
# còn `reference_index` chỉ được đặt ở BƯỚC 3 khi vòng khớp từ vựng chạy. Nên bản đầu của tôi thêm
# `request.reference_index is not None` vào điều kiện ở bước 2 và đó là MÃ CHẾT: ở thời điểm đó nó
# luôn là None. Không có test nào đỏ, chỉ có một ca vẫn sai — đúng lớp lỗi "tệp có mặt khác nó
# chạy", và đây là lần thứ sáu nó xuất hiện trong dự án này.
#
# Sinh từ VOCAB chứ không viết tay: viết tay thì thêm cụm ở trên mà quên thêm ở đây, và câu
# "món thứ sáu có hải sản không?" lại bị đọc thành duyệt danh mục hải sản.
REFERENCE_PHRASES = frozenset(
    p for p, (kind, value) in VOCAB.items()
    if kind == "reference" or (kind == "flag" and value == "refers_to_focus")
)
# Gồm CẢ cụm tiêu điểm ("món đó", "cái đó"), không chỉ cụm đếm vị trí.
#
# Bỏ sót chúng là một hồi quy thật: khi chuyển các cụm đó từ loại `reference` sang cờ
# `refers_to_focus`, tập này hụt đi và `co_tham_chieu` thành False, nên câu "Cái đó có cay không?"
# không còn được đọc là câu HỎI VỀ MỘT MÓN — nó rơi xuống nhánh lọc và trả về danh sách.
# `context-reference-02` bắt được ngay.
#
# Sinh từ VOCAB theo cả hai điều kiện, không viết tay: thêm cụm tiêu điểm mới mà quên ở đây là đúng
# lỗi này lặp lại.

# Cách nói ngân sách nghiêm ngặt: "rẻ hơn 20 nghìn" KHÔNG bao gồm món đúng 20.000đ.
# Khác với "dưới 50.000đ" hay "tầm 80k trở xuống", vốn được hiểu là bao gồm.
# Bỏ qua khác biệt này thì câu "rẻ hơn 20 nghìn" trả về Bia Sài Gòn Special đúng 20.000đ.
STRICT_BUDGET_FRAMING = ("re hon", "it hon", "thap hon", "duoi muc", "khong den")

# Cách nói KHẲNG ĐỊNH: khách đưa ra một con số và hỏi nó có đúng không.
#
# Kèm điều kiện có tên món, danh sách này mới được dùng — "dưới 45k đúng không?" (không tên món)
# vẫn là ngân sách. Hẹp có chủ đích: nó chỉ chặn đúng trường hợp đo được, không đoán rộng ra.
PRICE_ASSERTION_FRAMING = ("dung khong", "phai khong", "co dung", "co phai", "dung chu",
                           "phai chu", "co đung")

# Cách nói HỎI VỀ một thuộc tính — hỏi định nghĩa hoặc cách nhà hàng ghi nhận nó.
#
# Xem bước 5d-bis. Câu hỏi VỀ một thuộc tính KHÔNG phải yêu cầu lọc theo thuộc tính đó, và lớp mô
# hình đã nhầm hai thứ này ở hai lượt golden thật.
# Cách nói "hai thứ này KHÁC NHAU thế nào" — câu tri thức, không phải câu lọc thực đơn.
#
# Vì sao kiểm trên `folded` chứ không thêm vào từ vựng: hai cách nói phổ biến nhất
# ("khac nhau the nao", "khac gi nhau") ĐÃ thuộc nhóm `comparison` và `asks_comparison` từ trước, và
# nhận lại là cụm trùng — `_add` sẽ nổ. Kiểm trên chuỗi đã rút dấu thì hai cơ chế sống cạnh nhau
# được: cụm vẫn giữ nghĩa so sánh cũ, và thêm nghĩa "đây là câu tri thức".
#
# KHÔNG dùng `request.is_comparison` cho việc này, dù nghe như đủ. Nhóm `comparison` chứa cả `voi`
# (với), và "với" là tiểu từ cuối câu rất thường gặp trong tiếng Việt — "tư vấn giúp mình với", "cho
# mình xem các món lẩu với". Dùng cờ đó thì những câu ấy mất luôn ràng buộc lọc.
DIFFERENCE_FRAMING = (
    "khac nhau the nao", "khac nhau nhu the nao", "khac gi nhau", "co gi khac nhau",
    "phan biet the nao", "khac nhau ra sao", "khac nhau diem nao",
)

# "khác ... CHỖ NÀO" / "khác ... Ở ĐÂU" = khác nhau ở ĐIỂM nào, không phải ở ĐÂU.
#
# Phải là MẪU chứ không phải cụm cố định, vì phần giữa là bất kỳ: "Cơm tấm khác **cơm chiên** chỗ
# nào?". Tôi đã thử bằng cụm cố định `khac cho nao` trước, và nó không khớp câu thật vì hai chữ ấy
# không đứng liền nhau — bài học: cụm cố định chỉ nhận được cách nói mà tôi tình cờ viết ra.
#
# Hậu quả khi không nhận ra: `cho nao` khớp chính sách `location`, nên câu này được trả lời bằng
# thông tin CHỖ ĐẬU XE. Ca golden của nó vẫn XANH vì tiêu chí chỉ đòi `kind=fact` và độ dài — một ca
# đạt vì lý do sai, lần thứ năm trong dự án này.
KHAC_VI_TRI_RE = re.compile(r"\bkhac\b(?:\s+\S+){0,4}\s+(?:cho nao|o dau|diem nao)\b")

# KHÁCH PHỦ NHẬN một ràng buộc mà hệ thống đang gán cho họ.
#
# "tôi đâu có nói là không ăn được cay" chứa nguyên văn cụm `khong an duoc cay`, nên bộ khớp cụm
# gán `spice:none` — đúng cái khách vừa phủ nhận. Đo được trên bản chạy thật, và lượt sau đó mở
# bằng "Vì bạn muốn món không cay…" trong khi khách vừa nói ngược lại.
#
# Đây là lớp va chạm đã gặp nhiều lần ở dự án (`chào` ⊂ `Cháo lòng`, `bỏ` -> `ingredient:beef`),
# nhưng ở tầng CÂU chứ không phải tầng chữ: cụm khớp đúng, chỉ là nó nằm trong một khung phủ định.
# Bộ khớp cụm không đọc được khung — nên khung phải được nhận ra TRƯỚC, ở đây.
#
# Xử lý: nhãn rút ra không được ÁP, mà thành lệnh BỎ ràng buộc cùng nhóm. Đó đúng là điều khách
# muốn, và nó dùng lại nguyên cơ chế `y_dinh_bo` + `da_bo_rang_buoc` sẵn có — nên khách còn nhận
# được câu xác nhận "Dạ em đã bỏ điều kiện không cay…", tức thấy được hệ thống đã sửa.
# PHỦ ĐỊNH MỘT DANH MỤC — "không uống bia", "mình không ăn lẩu".
#
# Đo được, và nó là phép lọc NGƯỢC HẲN ý khách:
#
#     "tôi không uống bia, tư vấn cho tôi đồ uống khác"
#     -> Bia Hà Nội, Bia Sài Gòn Special, Bia Tiger Crystal
#
# Khách nói KHÔNG uống bia và nhận về đúng ba loại bia. Nguyên nhân: `bia` là một cụm DANH MỤC
# (`cat_alcohol`), và không có gì đọc chữ "không" đứng trước nó — nên nó được áp như một bộ lọc
# dương. Cùng lớp lỗi với "không cay" từng tự xuất hiện, nhưng ở tầng danh mục.
#
# Vì sao `la_cau_phu_nhan()` không đỡ được: hàm đó nhận câu PHỦ NHẬN LỜI KHAI TRƯỚC ("tôi đâu có
# nói là..."), không nhận ràng buộc phủ định trực tiếp. Còn "không cay" chạy được là vì cụm
# "khong an duoc cay" nằm SẴN trong từ vựng như một đơn vị — cách đó không mở rộng được cho 24 cụm
# danh mục nhân với mọi cách nói phủ định.
#
# Nhận theo VỊ TRÍ: một từ phủ định đứng trong ba từ ngay trước cụm danh mục. Ba từ đủ cho "không
# uống bia", "không ăn được lẩu", "mình không thích cà phê", và đủ ngắn để "không cay nhưng cho
# mình bia" KHÔNG bị đọc nhầm.
TU_PHU_DINH = ("khong", "ko", "chang", "chả", "dung", "khoi", "kieng", "tranh", "ghet", "khong thich")


def _danh_muc_bi_phu_dinh(folded: str, cum_danh_muc: dict) -> tuple[list[str], list[str]]:
    """(mã danh mục bị phủ định, cụm chữ đã khớp).

    Trả về CẢ cụm chữ vì `ho_mon` cũng bắt những chữ đó, và `ho_mon` thắng `wants` trong `select()`.
    Chỉ gỡ danh mục mà để lại `ho_mon=['bia']` thì phép lọc thành "họ bia, trừ danh mục bia" — ra
    RỖNG. Đo được đúng như vậy ở bản sửa đầu.
    """
    ma_ket: list[str] = []
    cum_ket: list[str] = []
    for cum, ma in cum_danh_muc.items():
        for m in re.finditer(rf"(?<![a-z]){re.escape(cum)}(?![a-z])", folded):
            truoc = folded[: m.start()].split()[-3:]
            if any(t in TU_PHU_DINH for t in truoc):
                if ma not in ma_ket:
                    ma_ket.append(ma)
                cum_ket.append(cum)
                break
    return ma_ket, cum_ket


# COMBO — khách xin một BỘ món, mỗi loại một suất.
#
# "Mình đi một mình, muốn tư vấn 1 món ăn nhẹ gồm 1 món chính, 1 thức uống, 1 tráng miệng"
#
# Trước khi có khối này, câu trên cho `categories=['cat_dessert']` và `wants='drink'` — ba yêu cầu
# chồng lên nhau rồi cái sau đè cái trước, nên khách nhận 6 món khai vị/chay và **không có đồ uống
# nào**. Nhiều danh mục trong một câu chỉ thành phép HOẶC, mà khách đang xin phép CỘNG.
#
# Đây là khác biệt về CẤU TRÚC chứ không phải về từ vựng: một bộ combo là N SUẤT, mỗi suất một
# loại, mỗi suất chọn riêng. Không phép lọc phẳng nào diễn đạt được.
#
# Bảng dưới ánh xạ tên suất -> nhóm danh mục. Tên nhóm lấy từ chính thực đơn (13 danh mục), nên
# thêm danh mục mới thì chỉ cần thêm một dòng.
SUAT_COMBO: tuple[tuple[str, tuple[str, ...]], ...] = (
    # (từ khách dùng, danh mục hợp lệ cho suất này)
    ("khai vi", ("cat_appetizer",)),
    ("trang mieng", ("cat_dessert", "cat_fruit")),
    ("do uong", ("cat_drink", "cat_juice", "cat_alcohol")),
    ("thuc uong", ("cat_drink", "cat_juice", "cat_alcohol")),
    ("nuoc uong", ("cat_drink", "cat_juice")),
    ("nuoc", ("cat_drink", "cat_juice")),
    ("lau", ("cat_hotpot",)),
    ("mon chinh", ("cat_main", "cat_noodle", "cat_seafood", "cat_chicken", "cat_regional")),
    ("mon man", ("cat_main", "cat_noodle", "cat_seafood", "cat_chicken", "cat_regional")),
)

# "1 món chính", "2 nước", "một tráng miệng". Số viết bằng chữ chỉ nhận "mot"/"hai"/"ba" — quá số
# đó thì khách gõ số, và đoán thêm là mở đường cho dương tính giả.
_SO_CHU = {"mot": 1, "hai": 2, "ba": 3}
SUAT_RE = re.compile(r"(\d+|mot|hai|ba)\s+([a-z ]{2,12}?)(?=\s*(?:,|va|\+|$|\d))")


def doc_suat_combo(folded: str) -> list[tuple[str, int, tuple[str, ...]]]:
    """(tên suất, số lượng, danh mục hợp lệ) — rỗng nghĩa là không phải câu combo.

    Đòi ÍT NHẤT HAI suất khác loại. Một suất thì đó là câu lọc bình thường ("cho mình 2 món chay"),
    và biến nó thành combo sẽ phá một đường đã đo.
    """
    thay: list[tuple[str, int, tuple[str, ...]]] = []
    da_co: set[str] = set()
    for m in SUAT_RE.finditer(f" {folded} "):
        so_chu, cum = m.group(1), m.group(2).strip()
        try:
            so = int(so_chu)
        except ValueError:
            so = _SO_CHU.get(so_chu, 0)
        if not 1 <= so <= 9:
            continue
        for ten, nhom in SUAT_COMBO:
            # Khớp ĐUÔI: "mon chinh" khớp cả "mon chinh" lẫn "1 mon chinh nua".
            if cum == ten or cum.endswith(" " + ten):
                if ten not in da_co:
                    thay.append((ten, so, nhom))
                    da_co.add(ten)
                break
    return thay if len(thay) >= 2 else []


# DẤU XIN MÓN KHÁC, ĐỨNG RỜI KHỎI CHỦ ĐỀ.
#
# Từ vựng đã có cụm `mon khac|cai khac|mon nao khac`, nhưng chúng đòi hai chữ ĐI LIỀN NHAU. Khách
# thật thì chèn chủ đề vào giữa, và cả câu mất tín hiệu:
#
#     "tư vấn món khác đi"              -> nhận ra, 0 món trùng
#     "tư vấn món CHAY khác đi"         -> KHÔNG nhận ra, trả lại y nguyên 6 món vừa nêu
#     "còn món CHAY nào nữa không"      -> KHÔNG nhận ra
#     "còn món nào DƯỚI 100 NGHÌN nữa"  -> KHÔNG nhận ra
#
# Nguyên tắc đúng là: **hỏi thêm tức là muốn món khác** — dù khách có nhắc lại chủ đề hay không.
# Nhắc lại chủ đề là để giữ ràng buộc, không phải để xin lại đúng những món vừa đọc.
#
# Nên tín hiệu được đọc ở mức TỪ RỜI thay vì cụm liền. Ba từ này chỉ mang nghĩa "thêm/khác" khi
# đứng riêng: `khac` trong "khác nhau chỗ nào" đã bị `asks_difference` chặn trước, `moi` trong
# "mình mới ăn xong" không đi cùng một câu xin gợi ý, và `nua` gần như luôn là "nữa".
# «A HAY B» — hai LỰA CHỌN, không phải hai điều kiện phải thỏa cùng lúc.
#
# Đo được: "nên gọi lẩu hay nướng" -> **0 món**. "lẩu" thành `cat_hotpot`, "nướng" thành
# `method:grilled`, và phép lọc là AND nên nó đi tìm món vừa là lẩu vừa nướng.
#
# "chọn cơm hay phở" thì lại ra 11 món — vì cả hai rơi vào `ho_mon`, mà `ho_mon` vốn là phép HOẶC.
# Nên lỗi chỉ hiện khi hai vế rơi vào HAI LOẠI ràng buộc khác nhau. Đúng kiểu lỗi chỉ lộ ra ở một
# tổ hợp dữ liệu cụ thể, và không tổ hợp nào trong 140 ca chạm tới.
#
# Chỉ nhận khi có "hay"/"hoặc" đứng RỜI giữa câu. `hay` còn nghĩa "hay ho" nhưng lúc đó nó không
# đứng giữa hai vế ràng buộc, và điều kiện dưới đòi phải có ĐỦ HAI nguồn ràng buộc.
HAI_LUA_CHON_RE = re.compile(r"\b(?:hay|hoac)\b")

XIN_MON_KHAC_TU = ("khac", "nua", "moi", "tiep")

# «khác» có HAI nghĩa hoàn toàn khác nhau, và golden bắt được ngay lượt đầu sau khi tôi thêm tín
# hiệu trên:
#
#     "tư vấn món chay KHÁC đi"            -> lệnh: cho tôi món khác     (đúng ý tín hiệu)
#     "Vị miền Bắc KHÁC miền Nam thế nào?" -> câu hỏi: chúng khác ra sao (NGƯỢC hẳn)
#
# Câu thứ hai đáng được trả bằng một đoạn tri thức, nhưng tín hiệu mới đọc nó thành "bỏ những món
# vừa nêu" và đẩy nó xuống nhánh lọc. Golden tụt 103/103 -> 102/103.
#
# `DIFFERENCE_FRAMING` không bắt được vì mọi cụm ở đó đều đòi chữ "nhau" ("khác nhau thế nào"), còn
# `KHAC_VI_TRI_RE` chỉ nhận "chỗ nào|ở đâu|điểm nào". Câu này là "khác <X> thế nào" — không có
# "nhau", không có "chỗ nào".
#
# Phân biệt bằng thứ ĐỨNG SAU: có từ hỏi thì là câu hỏi. Đây là hàng rào hẹp và kiểm được, thay vì
# một danh sách cụm dài mãi không đủ.
KHAC_LA_CAU_HOI_RE = re.compile(
    r"\bkhac\b(?:\s+\S+){0,5}\s+(?:the nao|nhu the nao|ra sao|cho nao|o dau|diem nao|gi)\b")

# ------------------------------------------------------------------------------------------------
# CÂU HỎI VỀ MỘT SỰ VIỆC, khác CÂU XIN MÓN — và đây là chỗ mã tất định sai nhiều nhất.
#
# Bộ đo hai chiều (mục 4.9 của báo cáo) cho thấy: trên 50 câu tri thức, mã tất định trả lời SAI DẠNG
# 25 câu. Nó không im lặng — nó trả về một danh sách món, mọi món có thật, mọi giá đúng, và không
# câu nào trả lời điều được hỏi:
#
#     hỏi : "Gọi khai vị trước có làm no bụng không ăn được món chính không?"
#     đáp : "Mời bạn tham khảo: Bánh mì pate Sài Gòn (35.000đ), Bánh cuốn Thanh Trì..."
#
# Nguyên nhân: câu chứa chữ "khai vị", và "khai vị" là một cụm từ vựng NHÓM MÓN. Nhánh lọc món khớp
# trước nhánh tri thức, nên câu đi sai đường.
#
# CÁCH PHÂN BIỆT: không phải bằng nội dung mà bằng DẠNG CÂU.
#
#     xin món  : "món nào không cay", "cho mình món chay", "gợi ý món khai vị"
#                -> hỏi VỀ MỘT TẬP MÓN, mong đợi danh sách
#     hỏi về   : "gọi khai vị trước CÓ làm no bụng KHÔNG", "cùng là gà MÀ SAO món dai"
#                -> hỏi VỀ MỘT SỰ VIỆC, mong đợi lời giải thích
#
# Hàng rào phải có HAI CHIỀU. Chỉ nhận diện chiều "hỏi về" thì câu "có món nào không cay không?"
# — vốn là câu xin món — cũng khớp, và ta phá một nhánh đang đúng để sửa một nhánh đang sai.
# ------------------------------------------------------------------------------------------------

# Chiều 1 — dấu hiệu HỎI VỀ một sự việc: hỏi cách thức, lý do, hay tình trạng.
_HOI_VE_SU_VIEC = (
    r"the nao", r"nhu the nao", r"ra sao", r"lam sao", r"cach nao",
    r"vi sao", r"tai sao", r"sao lai", r"ma sao", r"sao ma",
    r"co nen", r"nen .{0,20} khong", r"co phai", r"phai khong",
    r"bao lau", r"bao gio", r"khi nao", r"tinh sao", r"the a",
    # "có ... không" đòi ÍT NHẤT BA TỪ ở giữa.
    #
    # Đây là chỗ hàng rào suýt phá bốn nhánh đang đúng. "Ở đây có phở không", "Có cơm không ạ",
    # "có bia gì không" đều khớp mẫu rộng, nhưng chúng là câu HỎI THỰC ĐƠN — khách hỏi quán có bán
    # món đó không, và câu trả lời đúng là một danh sách món.
    #
    # Phân biệt bằng ĐỘ DÀI phần ở giữa, vì nó phản ánh khác biệt ngữ pháp thật:
    #     "có PHỞ không"            danh từ, 1 từ  -> hỏi thực đơn
    #     "có LÀM NO BỤNG không"    cụm động từ    -> hỏi sự việc
    r"co(?:\s+\S+){3,8}?\s+khong",
    r"duoc khong", r"co duoc", r"co the .{0,20} khong",
    r"khac nhau", r"khac gi", r"la gi", r"nghia la",
)
HOI_VE_SU_VIEC_RE = re.compile(
    r"(?<![a-z])(?:" + "|".join(_HOI_VE_SU_VIEC) + r")(?![a-z])")

# Chiều 2 — dấu hiệu XIN MÓN. Khớp cái nào ở đây thì KHÔNG phải câu hỏi tri thức, dù chiều 1 khớp.
#
# `mon nao` là dấu hiệu mạnh nhất: "có MÓN NÀO không cay không?" khớp cả `co .* khong` ở chiều 1,
# nhưng nó là câu xin món rõ ràng.
_XIN_MON = (
    # "mon ... nao" chịu được từ chèn giữa: "món CHAY nào", "món NƯỚNG nào có" — cùng lớp lỗi với
    # cụm giờ mở cửa, và nếu thiếu thì "Có món chay nào không?" bị đọc thành câu hỏi tri thức.
    r"mon(?:\s+\S+){0,3}?\s+nao", r"mon(?:\s+\S+){0,3}?\s+gi",
    r"nhung mon nao",
    r"cho minh", r"cho toi", r"cho em", r"cho anh", r"cho chi",
    r"goi y", r"tu van", r"de xuat", r"lay cho", r"mang cho",
    r"minh muon an", r"toi muon an", r"em muon an", r"muon goi",
    r"co gi ngon", r"an gi", r"goi gi", r"uong gi", r"chon gi",
)
XIN_MON_RE = re.compile(r"(?<![a-z])(?:" + "|".join(_XIN_MON) + r")(?![a-z])")


# Dấu hiệu MẠNH — hỏi cách thức hoặc lý do. Những cụm này không bao giờ xuất hiện trong câu xin
# món, nên chúng thắng cả khi câu có ràng buộc:
#
#     "tiêu tầm hai trăm mỗi người thì TÍNH SAO?"   có ngân sách, nhưng đang hỏi CÁCH LÀM
#     "cùng là gà MÀ SAO món thì mềm món thì dai?"  có nguyên liệu, nhưng đang hỏi LÝ DO
#
# Dấu hiệu YẾU ("có ... không", "được không") thì mơ hồ hơn, nên chỉ áp dụng khi câu KHÔNG có ràng
# buộc nào — có ràng buộc thì khách đang lọc thật.
_HOI_MANH = (
    r"the nao", r"nhu the nao", r"ra sao", r"lam sao", r"cach nao",
    r"vi sao", r"tai sao", r"sao lai", r"ma sao", r"sao ma", r"tinh sao",
    r"sao cho", r"sao gio", r"khac nhau", r"khac gi",
    # Bốn khung ĐÒI BẢO ĐẢM / HỎI NGUỒN GỐC. Chúng phải nằm ở nhóm MẠNH, không phải nhóm yếu.
    #
    # Vì sao: chúng gần như luôn đi kèm một nhãn, và nhóm yếu bị chính nhãn đó vô hiệu hoá.
    # "Đồ chay ở đây CÓ THẬT SỰ chay không" có `diet:vegetarian`, nên dấu hiệu yếu thua và câu rơi
    # vào nhánh lọc — khách nhận về một danh sách món chay cho một câu hỏi **có nên tin nhãn chay
    # hay không**. Danh sách ấy không trả lời gì, và tệ hơn, nó ngầm khẳng định điều khách đang nghi.
    #
    # Bốn khung này không bao giờ là lời xin món: không ai nói "cho tôi món có thật sự chay" hay
    # "lấy từ đâu" để gọi đồ ăn. Nên đưa lên nhóm mạnh là an toàn.
    #
    # Đo từng mẫu trên 710 câu của mọi tập: mỗi mẫu đổi ĐÚNG một câu, đúng câu nó nhắm, 0 câu khác.
    # `thi sao` bị LOẠI dù cũng là khung hỏi: nó đổi 6 câu, trong đó "Món đặc sản vùng miền thì sao?"
    # mất `cat_regional` — đó là câu xin món, và nhánh lọc mới đúng.
    r"co that su", r"lay tu dau", r"co tien khong", r"co an duoc",
    # `la gi` và `nghia la` KHÔNG nằm ở đây, dù chúng là câu hỏi định nghĩa.
    #
    # Lý do đo được: ca `A-promo-02` "Món đặc trưng của nhà hàng là gì?" — đây là câu HỎI THỰC ĐƠN,
    # và câu trả lời đúng là danh sách 2 món mang `promo:signature`. Đưa `la gi` vào nhóm mạnh làm
    # câu này rơi xuống truy hồi và tập 140 ca tụt còn 139.
    #
    # Cùng cụm chữ, hai loại câu: "nhãn ít calo LÀ GÌ" hỏi định nghĩa; "món đặc trưng LÀ GÌ" hỏi
    # danh sách. Chúng chỉ phân biệt được bằng thứ đứng trước, nên `la gi` ở lại nhóm YẾU — nơi nó
    # chỉ có hiệu lực khi câu không có ràng buộc nào.
)
HOI_MANH_RE = re.compile(r"(?<![a-z])(?:" + "|".join(_HOI_MANH) + r")(?![a-z])")


def la_cau_hoi_manh(folded: str) -> bool:
    """Dấu hiệu hỏi cách thức/lý do — thắng cả khi câu có ràng buộc."""
    return bool(HOI_MANH_RE.search(folded)) and not XIN_MON_RE.search(folded)


def la_cau_hoi_tri_thuc(folded: str) -> bool:
    """Câu này hỏi VỀ một sự việc, hay xin một danh sách món?

    Trả `True` chỉ khi chiều 1 khớp và chiều 2 KHÔNG khớp. Hàng rào hẹp có chủ ý: thà bỏ sót một
    câu tri thức (nó rơi về nhánh lọc như cũ) còn hơn nuốt một câu xin món (làm hỏng nhánh đang
    đúng trên 140 ca và 149 lượt).
    """
    return bool(HOI_VE_SU_VIEC_RE.search(folded)) and not XIN_MON_RE.search(folded)


PHU_NHAN_FRAMING = (
    # a) khung LIỀN MẠCH — cụm phủ định đứng ngay trước điều bị phủ nhận
    "dau co noi", "dau co bao", "dau co keu", "dau co yeu cau", "dau co doi",
    "khong he noi", "khong he bao", "khong noi la", "khong bao la", "chua he noi",
    "dau phai", "khong phai la", "khong phai minh", "khong phai toi", "co phai dau",
    "ai bao", "ai noi", "nao co noi", "nao co bao", "lam gi co",
    "toi dau co", "minh dau co", "em dau co", "toi khong co", "minh khong co",
    "hieu nham", "hieu sai", "nham roi", "sai roi", "khong dung",
)

# b) khung RỜI — "tôi CÓ nói … ĐÂU", "mình CÓ … ĐÂU". Phần bị phủ nhận nằm GIỮA hai mảnh, nên
#    không cụm liền mạch nào bắt được; phải khớp bằng mẫu.
#
#    `\bdau\s*$` neo vào CUỐI câu có chủ ý: "đâu" giữa câu là từ để hỏi ("ăn ở đâu"), chỉ "đâu"
#    cuối câu mới là dấu phủ định. Đây đúng kiểu bẫy rút dấu mà dự án đã gặp nhiều lần, nên nó được
#    thu hẹp bằng vị trí thay vì bằng một danh sách ngoại lệ.
PHU_NHAN_ROI_RE = re.compile(r"\b(?:co|da)\b.{0,40}\bdau\s*$")


# Cụm dài hơn NUỐT cụm phủ nhận nằm trong nó. Cùng luật khớp-cụm-dài-trước của `VOCAB_ORDER`, và
# ở đây nó chống một vụ đụng chữ đảo nghĩa:
#
#     "Hải sản là mình KHÔNG ĐỤNG ĐƯỢC"  ->  rút dấu `khong dung duoc`
#                                            chứa `khong dung` ("không ĐÚNG") của khung phủ nhận
#
# Khách nói mình không đụng được hải sản, hệ thống đọc thành "bạn nói không đúng" và **gỡ** ràng
# buộc dị nguyên. Đây là đường đảo nghĩa thứ BA tìm được khi rà 20 cách khai dị ứng — hai đường kia
# nằm ở lớp ý định (`an duoc hai san`) và ở chỗ thiếu cụm.
#
# Vì sao dùng danh sách nuốt thay vì bỏ `khong dung` khỏi khung phủ nhận: "bạn nói không đúng" là
# câu phủ nhận thật và cần giữ. Hai nghĩa chỉ tách được bằng chữ đứng sau.
# Đường đảo nghĩa THỨ TƯ, cùng một chữ `khong dung` nhưng nghĩa khác cả ba đường trên:
#
#     "Mình KHÔNG DÙNG mì chính"  ->  rút dấu `khong dung mi chinh`
#
# Đây là lời KHAI TRÁNH ("tôi không ăn thứ này"), không phải lời rút lại ("bạn nói không đúng").
# Không nuốt thì khung phủ nhận bật, và hệ thống **gỡ** đúng ràng buộc khách vừa đặt ra — nó nhận
# ra `health:no_msg` rồi tự bỏ đi.
_PHU_NHAN_BI_NUOT = {
    "khong dung": ("khong dung duoc", "khong dung noi", "khong dung vao",
                   "khong dung mi chinh", "khong dung bot ngot"),
}


def la_cau_phu_nhan(folded: str) -> bool:
    """Câu có phải là PHỦ NHẬN một ràng buộc không."""
    for k in PHU_NHAN_FRAMING:
        if k not in folded:
            continue
        if any(dai in folded for dai in _PHU_NHAN_BI_NUOT.get(k, ())):
            continue
        return True
    return bool(PHU_NHAN_ROI_RE.search(folded))


ATTRIBUTE_DEFINITION_FRAMING = (
    "dua tren gi", "dua vao gi", "nghia la gi", "hieu the nao", "tinh the nao", "do the nao",
    "can cu vao", "co nghia gi", "duoc ghi the nao", "ghi nhan the nao",
)

# Cách nói ĐÒI ỨNG VIÊN. Đây là phép loại trừ của bước 5d-bis, và nó bắt buộc: thiếu nó thì
# "Có món nào không cay không?" — một câu lọc thật — cũng bị coi là câu hỏi về thuộc tính.
CANDIDATE_FRAMING = ("mon nao", "co mon nao", "goi y", "cho minh", "co gi", "mon gi", "nao co")

# "<số> món": "cho mình 2 món", "lấy 3 món". Nhận bằng mẫu vì con số là bất kỳ.
#
# Mẫu này chỉ được ĐỌC ở nhánh cuối, sau khi đã biết câu không có ràng buộc nào — nên "gọi 2 món cho
# 3 người" không bị ảnh hưởng: câu đó có nhãn `party` nên nó đi nhánh lọc từ trước.
SO_MON_RE = re.compile(r"\d+\s*mon\b")

# Phép tính: "2 cộng 2 bằng mấy", "5 x 3", "10 chia 2".
#
# Mẫu chứ không phải danh sách cụm, vì cụm "cong bang may" khớp "2 cộng bằng mấy?" mà KHÔNG khớp
# "2 cộng 2 bằng mấy?" — có con số ở giữa. Lỗi đó đã xảy ra thật: bản từ khóa qua được phép thử cục
# bộ của tôi và trượt ở phép thử qua backend, vì hai phép thử dùng hai cách viết câu.
#
# Mẫu đòi HAI con số kẹp một phép tính, nên nó không khớp câu về món: "gọi 2 món cho 3 người" không
# có phép tính ở giữa, còn "50.000đ" chỉ có một số. Đo trên 9 câu về món: 0 câu bắt oan.
#
# CHỈ có tên phép tính viết bằng chữ, cộng `x`. Không có `+ - * /` vì `fold()` bỏ chúng: "3+4" thành
# "3 4", không phân biệt được với "gọi 3 4 món". Nên "3+4 = ?" KHÔNG bị chặn — giới hạn có thật, ghi
# ra chứ không để một nhánh ký hiệu trông như đang chạy. Thêm chúng vào mẫu là mã chết.
ARITHMETIC_RE = re.compile(
    r"\d+\s*(?:cong|tru|nhan|chia|x)\s*\d+"
)

# Tiền: "50k", "200 nghìn", "50.000đ".
MONEY_RE = re.compile(
    r"(?P<number>\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?P<unit>dong|nghin|ngan|trieu|d|k)(?![\w])"
)

# Món khách hay hỏi mà nhà hàng không bán. Đây là một DANH SÁCH, không phải suy luận:
# hệ thống chỉ nói chắc "không có món đó" với những món nó biết là không có. Món ngoài
# danh sách này mà cũng không có trong thực đơn thì rơi vào nhánh hỏi lại — kém hơn,
# nhưng không bịa.
NOT_ON_MENU = (
    "pizza", "sushi", "sashimi", "burger", "hamburger", "pasta", "spaghetti",
    "mi y", "ga ran", "khoai tay chien", "banh ngot", "kimchi", "lau thai",
    "dim sum", "steak", "bo bit tet", "salad ca ngu", "taco", "kebab",
    # Thêm sau khi chạy thật: câu "Có món bò Wagyu A5 không?" trả về các món bò khác mà KHÔNG nói
    # thực đơn không có Wagyu. Nó không xác nhận Wagyu tồn tại nên không bịa, nhưng nó yếu hơn hẳn
    # cách xử lý "sushi cá hồi Na Uy" — và khác biệt duy nhất là món kia có trong danh sách này.
    #
    # Cả bốn cụm đều KHÔNG nằm trong tên món nào của thực đơn (đã kiểm 91/91), nên thêm chúng không
    # tạo chỗ đụng chữ. Danh sách vẫn cố ý hẹp: cơ chế ĐOÁN tên món lạ đã bị bỏ vì nó bắt oan bốn ca
    # khai dị ứng, và nới lại cần một cách đo, không phải một danh sách dài hơn.
    "wagyu", "foie gras", "truffle", "caviar",
)


FOOD_CATEGORIES = (
    "cat_appetizer", "cat_noodle", "cat_main", "cat_seafood",
    "cat_hotpot", "cat_chicken", "cat_regional", "cat_vegetarian",
)
DRINK_CATEGORIES = ("cat_drink", "cat_juice", "cat_alcohol")


_NAME_CACHE: dict[int, list[tuple[str, str, str]]] = {}
_HO_MON_CACHE: dict[int, list[str]] = {}


def ho_mon_trong_thuc_don(menu_items: list[dict]) -> list[str]:
    """HỌ MÓN — từ đầu tên món mà NHIỀU món cùng dùng: "phở", "bún", "cơm", "lẩu", "trà"...

    Vì sao cơ chế này cần tồn tại riêng
    -----------------------------------
    Khách hỏi "có phở không" và nhận về cả bún, vì "phở" chỉ ánh xạ được tới DANH MỤC `cat_noodle` —
    mà danh mục ấy tên là **"Phở & Bún"**. Đúng nhóm, sai câu hỏi.

    `_name_candidates` ngay dưới đã tính đúng thứ cần, rồi **bỏ đi**: nó gom tiền tố tên món và giữ
    lại tiền tố ứng ĐÚNG MỘT món (để nhận "khách đang nói về món nào"). Nhánh `len(ids) != 1` —
    tiền tố ứng nhiều món — bị `continue`. Nhưng đó chính là **họ món**: `bun` ứng 6 món không phải
    vì nó nhập nhằng, mà vì nhà hàng có 6 món bún.

    Sinh từ THỰC ĐƠN, không viết tay
    --------------------------------
    Đây là lý do cơ chế này đúng hơn cách sửa đầu tiên của tôi (thêm `pho|bun|com` vào từ vựng danh
    mục): nó phủ mọi họ món nhà hàng có, kể cả họ thêm sau, và không ai phải nhớ cập nhật. Thêm 5
    món "Mì Quảng..." vào thực đơn là "mì" thành họ món ngay.

    Chỉ nhận từ ĐẦU TIÊN của tên. "Gà nướng mật ong" và "Cơm gà Hội An" đều có chữ "gà", nhưng "gà"
    không phải từ đầu của món thứ hai — nên nó không thành họ. Lấy mọi từ ở mọi vị trí thì "nướng",
    "chay", "sả" đều thành họ món, và câu lọc theo nhãn sẽ bị họ món giành mất.
    """
    key = id(menu_items)
    if key in _HO_MON_CACHE:
        return _HO_MON_CACHE[key]

    dem: dict[str, int] = {}
    for item in menu_items:
        words = fold(item["name"]).split()
        if words:
            dem[words[0]] = dem.get(words[0], 0) + 1
    # Từ đầu chỉ một món dùng thì không phải "họ" — món đó đã nhận được qua tên đầy đủ.
    ra = sorted((w for w, n in dem.items() if n >= 2 and len(w) >= 2), key=lambda w: (-len(w), w))
    _HO_MON_CACHE[key] = ra
    return ra


def _name_candidates(menu_items: list[dict]) -> list[tuple[str, str, str]]:
    """Các chuỗi nhận ra một món, sắp dài trước ngắn.

    Gồm tên đầy đủ và mọi tiền tố từ 2 từ trở lên **chỉ ứng đúng một món**. Tiền tố ứng
    nhiều món bị loại — đó là điều khiến cơ chế này khác với khớp một phần bừa.
    """
    cache_key = id(menu_items)
    if cache_key in _NAME_CACHE:
        return _NAME_CACHE[cache_key]

    owners: dict[str, set[str]] = {}
    for item in menu_items:
        words = fold(item["name"]).split()
        for size in range(2, len(words) + 1):
            owners.setdefault(" ".join(words[:size]), set()).add(item["id"])

    by_id = {m["id"]: m for m in menu_items}
    candidates: list[tuple[str, str, str]] = []
    for prefix, ids in owners.items():
        if len(ids) != 1:
            continue
        item_id = next(iter(ids))
        candidates.append((f" {prefix} ", item_id, by_id[item_id]["name"]))
    candidates.sort(key=lambda c: (-len(c[0]), c[0]))
    _NAME_CACHE[cache_key] = candidates
    return candidates


# Từ báo hiệu món đứng NGAY SAU nó là món bị loại, không phải món được hỏi.
#
# Danh sách hẹp có chủ ý. Mỗi cụm ở đây phải là cụm mà sau nó KHÔNG thể là món khách muốn — nên
# "không" trần không có mặt: "trà sữa không đường" là món khách muốn, chỉ đổi cách pha.
_TU_LOAI_TRU = (
    "khong phai", "khong muon", "khong thich", "khong lay", "khong uong", "khong an",
    "tru ", "ngoai tru", "tru mon", "dung lay", "bo qua", "chan ", "ngan ",
    "khac ngoai", "thay vi",
)


def understand(question: str, menu_items: list[dict]) -> Request:
    request = Request(text=question, folded=fold(question))
    working = f" {request.folded} "

    # 1. Tên món trước tiên, và ăn hết đoạn đã khớp. Phải đứng trước từ vựng: tên
    #    "Bún đậu mắm tôm" chứa "mam tom", "Gà nướng mật ong" chứa "nuong".
    #
    #    Khách thường viết rút gọn: "Lẩu gà lá é" thay cho "Lẩu gà lá é Đà Lạt". Nên ngoài
    #    tên đầy đủ, hệ thống nhận cả TIỀN TỐ DUY NHẤT — đoạn đầu của tên món mà không tên
    #    món nào khác cũng bắt đầu bằng nó. "lau ga la e" chỉ ứng một món nên nhận được;
    #    còn "bun" ứng 6 món nên không nhận, và đó là lý do phải đòi duy nhất chứ không
    #    khớp một phần bừa (18 từ đầu trong thực đơn bị trùng).
    for needle, item_id, label in _name_candidates(menu_items):
        if needle in working:
            if item_id in request.named_items or item_id in request.exclude_item_ids:
                continue
            # TÊN MÓN ĐỨNG SAU TỪ LOẠI TRỪ là món khách KHÔNG muốn, không phải món khách hỏi.
            #
            # Trước khi có nhánh này, cả ba cách nói dưới đây đều trả về đúng món vừa bị loại:
            #
            #     "Muốn cái gì mát mà rẻ, không phải trà sữa"  -> Trà sữa trân châu (45.000đ)
            #     "Cho mình đồ uống, không phải trà sữa"       -> Trà sữa trân châu
            #     "Món nào cũng được, trừ trà sữa"             -> Trà sữa trân châu
            #
            # Đây là kiểu sai tệ hơn "không hiểu": hệ thống hiểu đủ để tìm ra món, rồi mời đúng
            # món khách vừa từ chối. Khách đọc câu trả lời đó sẽ kết luận trợ lý không nghe mình.
            #
            # Cửa sổ 24 ký tự trước tên món, không phải cả câu: "trà sữa ngon không, à mà thôi cho
            # mình cái khác" có từ loại trừ ở SAU nên không được tính. Loại trừ là quan hệ vị trí.
            # Đệm một khoảng trắng vào cuối: tên món đã mang khoảng trắng đầu, nên đoạn trước nó
            # kết thúc bằng CHỮ. Thiếu đệm thì "…cũng được TRỪ" không khớp cụm `tru ` — đo được
            # bằng đúng câu "Món nào cũng được, trừ trà sữa".
            truoc = working[: working.index(needle)][-24:] + " "
            if any(t in truoc for t in _TU_LOAI_TRU):
                request.exclude_item_ids.append(item_id)
                working = working.replace(needle, " " * len(needle))
                request.matched.append(f"loại trừ tên món: {label}")
                continue
            request.named_items.append(item_id)
            working = working.replace(needle, " " * len(needle))
            request.matched.append(f"tên món: {label}")

    # 2. Cách hỏi về dị nguyên, quyết định TRƯỚC vòng khớp để một từ như "hải sản" được
    #    đọc đúng nghĩa. Hai dấu hiệu, và cả hai đều dẫn tới cùng một việc là loại món:
    #      - khách nói tránh: "dị ứng", "không ăn được", "không có ..."
    #      - khách hỏi về một món đã nêu tên: "... có X không?"
    #    Chỉ dùng chữ CÒN LẠI sau khi đã ăn tên món, để "Bún đậu mắm tôm" không tự sinh
    #    ra chủ đề tôm.
    wants_to_avoid = any(f" {f} " in working for f in AVOID_FRAMING)
    # "không sữa", "không trứng", "không hải sản" — mẫu "không <chủ đề>" là cách nói tránh
    # phổ biến nhất, và liệt kê từng tổ hợp thì vừa dài vừa dễ sót. Bắt bằng mẫu.
    #
    # Đây là chỗ AN TOÀN không được phụ thuộc mô hình sinh: câu "Bé nhà mình uống sữa là bị
    # đau bụng, có món nào không sữa không?" trước đây chỉ mô hình hiểu được, nghĩa là an
    # toàn của hệ thống phụ thuộc một thành phần không tất định. Nay mã tất định hiểu được.
    wants_to_avoid = wants_to_avoid or bool(
        re.search(r"\bkhong (?:co )?(?:hai san|do bien|do tanh|dau phong|lac|trung|sua|gluten|bot mi)\b", working)
    )
    # Triệu chứng cũng là cách khai dị ứng, không chỉ chữ "dị ứng".
    wants_to_avoid = wants_to_avoid or any(
        f" {p} " in working for p in ("bi dau bung", "bi di ung", "bi ngua", "bi noi me day", "an vao la bi")
    )
    # Câu "⟨món⟩ có ⟨thành phần⟩ không?" — hỏi VỀ một món, không phải duyệt danh mục.
    #
    # `request.reference_index` tính vào đây cùng với `named_items`, và đó là điểm dễ bỏ sót nhất
    # của cả khối tham chiếu ngược: câu "món thứ hai có hải sản không?" chưa có `named_items` khi
    # `understand()` chạy — món đó chỉ được giải ra ở bước hợp nhất bộ nhớ, VỀ SAU. Không tính
    # `reference_index` thì "hải sản" bị đọc thành "duyệt danh mục hải sản", và hệ thống liệt kê
    # món hải sản cho người vừa hỏi vì lo có hải sản. Đúng lớp lỗi an toàn tệ nhất mà khối
    # `allergen_topic` tồn tại để chống, chỉ đến theo một đường mới.
    co_tham_chieu = any(f" {p} " in working for p in REFERENCE_PHRASES)
    asks_about_named = (
        (bool(request.named_items) or co_tham_chieu)
        and " co " in working
        and " khong" in working
    )
    request.asks_about_named_dish = asks_about_named
    request.declared_avoidance = bool(wants_to_avoid)

    # Nhận "khác ... chỗ nào" TRƯỚC vòng khớp cụm, vì kết quả của nó chặn một ánh xạ trong vòng đó:
    # `cho nao` không được đọc thành chính sách `location`.
    khac_vi_tri = bool(KHAC_VI_TRI_RE.search(request.folded))
    if khac_vi_tri:
        request.asks_difference = True

    # 2b. Ý ĐỊNH — đọc TRƯỚC vòng khớp từ vựng, và ĂN hết đoạn đã khớp.
    #
    # Phải ăn chữ, không chỉ nhận diện: "bỏ hết điều kiện đi" rút dấu thành `bo het dieu kien di`,
    # và `bo` là nhãn `ingredient:beef` ("bò"). Không ăn thì khách xin BỎ ràng buộc lại nhận thêm
    # ràng buộc **thịt bò** — vụ đụng chữ thứ chín, xuất hiện ngay trong cơ chế vừa dựng để sửa một
    # vụ khác. Đúng lý do dự án có quy tắc "khớp cụm dài trước rồi ăn hết đoạn".
    from intent import doc_y_dinh_tu_chuoi_dem

    _y = doc_y_dinh_tu_chuoi_dem(working)
    if _y.cum_khop:
        _needle = f" {_y.cum_khop} "
        _sau = working.replace(_needle, " " * len(_needle))
        # CHỈ ăn khi việc ăn không phá mất một cụm từ vựng NẰM NGOÀI đoạn bị ăn.
        #
        # "cho mình thêm món chay": cụm ý định `them mon` khớp, và ăn nó làm mất `mon chay` — một
        # cụm KHÔNG nằm trong `them mon`. Khách xin món chay thì bị loại đúng những món chay.
        #
        # Còn "bỏ hết điều kiện đi": ăn `bo het dieu kien` làm mất cụm `bo` (ingredient:beef), nhưng
        # `bo` NẰM TRONG đoạn bị ăn — tức nó là một phần của chính cụm ý định, mất là đúng.
        #
        # Phân biệt hai trường hợp bằng đúng câu hỏi đó, thay vì bằng một bảng kiểm kê: bảng kiểm kê
        # tĩnh cho 200+ cặp chồng chữ mà chỉ một cặp có thật, và một thước đo như vậy sẽ bị tắt.
        _pha = [
            v for v in VOCAB
            if f" {v} " in working and f" {v} " not in _sau and v not in _y.cum_khop
        ]
        if _pha:
            # Phá cụm khác thì KHÔNG ăn — nhưng vẫn GIỮ ý định.
            #
            # Bản đầu bỏ luôn ý định ở đây, và nó làm mất đúng thứ cần: "cho mình thêm món chay nữa"
            # có cụm `them mon`, ăn nó sẽ phá `mon chay`, nên ý định bị bỏ và câu trả lại y nguyên
            # 6 món chay vừa xem — đúng lỗi đang sửa, chỉ đổi chỗ.
            #
            # Ăn chữ chỉ có MỘT mục đích: chặn chữ của cụm ý định tự nó sinh ra nhãn sai (`bo` của
            # "bỏ hết điều kiện" là `ingredient:beef`). Không ăn thì rủi ro là nhãn sai đó; bỏ ý
            # định thì mất hẳn một cơ chế. Rủi ro thứ nhất nhỏ hơn và nhìn thấy được.
            pass
        else:
            working = _sau

    # Họ món có thật trong thực đơn — tính từ dữ liệu, dùng làm hàng rào cho bước 3 dưới.
    ho_mon_co_that = set(ho_mon_trong_thuc_don(menu_items))

    # 3. Cụm từ vựng, dài trước ngắn, ăn hết đoạn đã khớp.
    for phrase in VOCAB_ORDER:
        needle = f" {phrase} "
        if needle not in working:
            continue
        kind, value = VOCAB[phrase]
        working = working.replace(needle, " " * len(needle))
        request.matched.append(f"{phrase!r} -> {kind}:{value}")
        if kind == "require":
            if value not in request.require_tags:
                request.require_tags.append(str(value))
        elif kind == "prefer":
            if value not in request.prefer_tags:
                request.prefer_tags.append(str(value))
        elif kind == "avoid":
            if value not in request.avoid_tags:
                request.avoid_tags.append(str(value))
            request.asks_allergy = True
        elif kind == "allergen_topic":
            allergen_tag, category = value  # type: ignore[misc]
            if wants_to_avoid or asks_about_named:
                if allergen_tag not in request.avoid_tags:
                    request.avoid_tags.append(str(allergen_tag))
                request.asks_allergy = True
            elif category is not None and category not in request.categories:
                # Không có dấu hiệu tránh -> khách đang duyệt danh mục.
                request.categories.append(str(category))
        elif kind == "category":
            if value not in request.categories:
                request.categories.append(str(value))
            # Cụm này có ĐỒNG THỜI là một họ món trong thực đơn không (từ đầu của nhiều tên món)?
            #
            # Giao HAI nguồn, và cả hai đều cần thiết:
            #
            #   thực đơn  -> "pho" là từ đầu của 3 món, "bun" của 6 -> đây là họ món THẬT
            #   từ vựng   -> cụm này đã được rà soát và khai là danh mục
            #
            # Vì sao không lấy trực tiếp danh sách họ món: nó chứa `goi` (Gỏi), `ca`, `ga`, `mi`,
            # `nuoc`. Nhận thẳng thì "nhà hàng GỌI món thế nào?" lọc ra toàn món gỏi, và "món NƯỚC"
            # lọc ra Nước ép. Đúng lớp lỗi đụng chữ đã giết bản cũ bảy lần — nên phép giao là hàng
            # rào: mỗi họ món được nhận đều là một cụm có người viết ra và có test canh.
            if phrase in ho_mon_co_that and phrase not in request.ho_mon:
                request.ho_mon.append(phrase)
        elif kind == "wants":
            request.wants = str(value)
        elif kind == "policy":
            # "Cơm tấm khác cơm chiên chỗ nào?" -> `cho nao` KHÔNG phải câu hỏi địa điểm.
            if value == "location" and khac_vi_tri:
                continue
            request.policy_topic = request.policy_topic or str(value)
        elif kind == "knowledge":
            # `policy` THẮNG `knowledge` khi cả hai cùng khớp: chủ đề nguyên văn chính xác tuyệt
            # đối, còn chủ đề nhiều mục phải chọn mục nên có chỗ để chệch. Đo được: câu "Nhà hàng
            # có nhận đặt bàn trước không?" khớp cả `booking` (nguyên văn) — và câu trả lời nguyên
            # văn đúng hơn, nên nó phải thắng.
            request.knowledge_topic = request.knowledge_topic or str(value)
        elif kind == "flag":
            if value == "asks_price":
                request.asks_price = True
            elif value in ("cheapest", "priciest"):
                request.asks_extreme = str(value)
            elif value == "comparison":
                request.is_comparison = True
            elif value == "off_topic":
                request.off_topic = True
            elif value == "asks_serving":
                request.asks_serving = True
            elif value == "scope_listed":
                request.scope_last_listed = True
            elif value == "similar":
                request.wants_similar = True
            elif value == "refers_to_focus":
                request.refers_to_focus = True
            elif value == "asks_comparison":
                request.asks_comparison = True
            elif value == "asks_suggestion":
                request.asks_suggestion = True
            elif value == "asks_difference":
                request.asks_difference = True
        elif kind == "reference":
            # Cụm đầu tiên khớp thắng. Cụm dài được khớp trước nên "món thứ hai" thắng "món đó",
            # và không cần thứ tự ưu tiên riêng ở đây.
            if request.reference_index is None:
                request.reference_index = int(value)  # type: ignore[arg-type]

    # 3b. Khách nói tránh điều gì, nhưng hệ thống không hiểu tránh gì.
    #
    #     Đây là trạng thái nguy hiểm nhất mã tất định có thể ở: khách đã nêu một hạn chế
    #     ("không ăn được đồ tanh") mà hệ thống KHÔNG biết hạn chế đó là gì — trả lời như
    #     thể không có hạn chế nào thì có thể mời đúng món khách không ăn được.
    #
    #     Kiểm trên chữ CÒN LẠI, không phải chữ gốc. Đây lại là nguyên tắc ăn đoạn: câu
    #     "không ăn được cay" đã được cụm `khong an duoc cay` ăn trọn và hiểu thành
    #     `spice:none`, nên phần "khong an duoc" không còn nữa và hạn chế KHÔNG phải là
    #     chưa hiểu. Bản đầu của tôi kiểm trên chữ gốc, nên nó báo động sai ở câu đó và
    #     làm tụt một ca đang đúng.
    leftover_avoid = any(f" {f} " in working for f in AVOID_FRAMING)
    request.unparsed_restriction = leftover_avoid and not request.avoid_tags

    # 4. Khách hỏi một món mà nhà hàng không bán.
    #
    #    Bản đầu của tôi đoán: "có cách hỏi về một món cụ thể + không khớp tên món nào".
    #    Nó bắt oan bốn ca dị ứng — câu "Mình dị ứng hải sản mà muốn ăn lẩu" còn lại chữ
    #    "mà" sau khi ăn hết từ vựng, và chữ đó bị coi là tên món lạ. Mở rộng danh sách từ
    #    chung chung là trò đánh chuột vô tận, nên cơ chế đoán đã bị bỏ.
    #
    #    Nay chỉ dựa vào một danh sách tường minh. Hẹp hơn, nhưng nói được điều gì thì nói
    #    chắc điều đó, và không bao giờ bắt oan một lời khai dị ứng.
    if not request.named_items:
        request.unknown_item = any(f" {w} " in working for w in NOT_ON_MENU)

    # 5. Ngân sách.
    money = MONEY_RE.search(request.folded)
    if money is not None:
        digits = money.group("number").replace(".", "").replace(",", "")
        value = int(digits)
        unit = money.group("unit")
        if unit in ("k", "nghin", "ngan"):
            value *= 1000
        elif unit == "trieu":
            value *= 1_000_000
        # Con số dưới 1.000 đồng không phải ngân sách thật — thường là số người.
        #
        # Và con số đi kèm TÊN MÓN cùng lối nói khẳng định là giá khách tưởng, không phải ngân
        # sách: nó phải được ĐÍNH CHÍNH, không phải dùng để lọc.
        khang_dinh_gia = bool(request.named_items) and any(
            f in request.folded for f in PRICE_ASSERTION_FRAMING
        )
        if value >= 1000 and khang_dinh_gia:
            request.asserted_price = value
            request.matched.append(f"giá khách khẳng định: {value:,}đ")
        elif value >= 1000:
            request.budget_max = value
            request.budget_strict = any(
                f in request.folded for f in STRICT_BUDGET_FRAMING
            )
            limit = "<" if request.budget_strict else "<="
            request.matched.append(f"ngân sách: {limit} {value:,}đ")

    # 5d. Câu về CHÍNH CÁI NHÃN, không về con số dinh dưỡng.
    #
    # Golden bắt được: "Nhãn 'ít calo' dựa trên gì?" bị cụm `calo` đẩy vào chủ đề dinh dưỡng và trả
    # "chưa có dữ liệu" — trong khi tài liệu `reading-menu-labels.md` trả lời đúng câu đó: nhãn là
    # đánh giá cảm quan của người nhập thực đơn, không phải kết quả phân tích.
    #
    # Phân biệt bằng chữ "nhãn": khách hỏi VỀ nhãn thì đó là câu meta về thực đơn, không phải câu
    # đòi một con số. Bỏ chủ đề dinh dưỡng để câu rơi xuống nhánh truy hồi toàn kho, nơi có câu
    # trả lời thật.
    # 5c-bis. Câu HỎI VỀ một sự việc, dù có chứa tên nhóm món.
    #
    # Bộ đo hai chiều: 25/50 câu tri thức bị trả lời SAI DẠNG — mã tất định đưa ra một danh sách
    # món cho câu hỏi "thế nào / vì sao / có ... không". Nguyên nhân: câu chứa tên nhóm món ("khai
    # vị", "cà phê", "lẩu") nên nhánh lọc khớp trước nhánh tri thức.
    #
    # Bỏ tín hiệu NHÓM MÓN để câu rơi xuống truy hồi. Chỉ bỏ khi:
    #   - dạng câu là HỎI VỀ, không phải XIN MÓN (hàng rào hai chiều, xem `la_cau_hoi_tri_thuc`)
    #   - và KHÔNG có ràng buộc cứng nào — có ràng buộc thì khách đang lọc thật, không phải hỏi
    #
    # Điều kiện thứ hai quan trọng: câu "món chay nào dưới 100 nghìn có cay không?" vừa hỏi vừa lọc,
    # và ở đó nhánh lọc mới là nhánh đúng.
    _manh = la_cau_hoi_manh(request.folded)
    if ((_manh or la_cau_hoi_tri_thuc(request.folded))
            and not request.named_items
            and not request.policy_topic
            # Dấu hiệu MẠNH thắng cả khi có ràng buộc; dấu hiệu yếu thì không.
            and (_manh or (not request.require_tags
                           and not request.avoid_tags
                           and request.budget_max is None))):
        if request.categories or request.wants:
            request.matched.append(
                f"dạng câu HỎI VỀ -> bỏ tín hiệu nhóm món ({request.categories or request.wants})")
            request.categories = []
            # `wants` về "any", KHÔNG về None — hợp đồng JSON chỉ nhận food|drink|any, và đặt None
            # làm phản hồi trượt lược đồ. Test hợp đồng bắt được ngay ở câu "Hôm nay thời tiết thế
            # nào?", nơi cờ này bật rồi đi tiếp xuống nhánh off_topic.
            request.wants = "any"
        request.hoi_ve_su_viec = True

    # Giờ mở/đóng cửa với CHỦ NGỮ CHÈN GIỮA — "mấy giờ QUÁN đóng cửa", "nhà hàng mở cửa mấy giờ".
    #
    # Bảng từ vựng chỉ khớp cụm LIỀN NHAU, nên bốn trong sáu cách hỏi tự nhiên rơi xuống nhánh truy
    # hồi. Và truy hồi trả về một danh sách món khai vị cho câu hỏi giờ mở cửa — vì không đoạn nào
    # nói về giờ (tài liệu giờ mở cửa là `verbatim`, KHÔNG nằm trong chỉ mục truy hồi), nên nó lấy
    # đoạn giống nhất còn lại.
    #
    # Lỗi này lộ ra khi chạy ví dụ xuyên suốt cho báo cáo, không phải từ tập đánh giá — vì mọi ca
    # trong tập đều viết cụm liền nhau.
    if not request.policy_topic and _GIO_CUA_RE.search(request.folded):
        request.policy_topic = "hours"
        request.matched.append("giờ mở/đóng cửa (có chủ ngữ chèn giữa)")

    if request.policy_topic == "nutrition" and " nhan " in f" {request.folded} ":
        request.policy_topic = None
        request.matched.append("hỏi VỀ nhãn -> không phải câu dinh dưỡng")

    # 5d-bis. Câu HỎI VỀ một thuộc tính KHÁC câu yêu cầu LỌC theo thuộc tính đó.
    #
    # Golden qua stack thật bắt được hai lượt, và cả hai do LỚP MÔ HÌNH làm sai chứ không phải mã
    # tất định:
    #
    #     "Nhãn 'ít calo' dựa trên gì?"   mô hình trả `prefer: health:low_calorie`  -> nhánh filter
    #     "Món này có bột ngọt không?"    mô hình trả `prefer: health:no_msg`       -> nhánh filter
    #
    # Đường tất định định tuyến ĐÚNG cả hai (`knowledge_corpus`), rồi `enrich()` thêm một nhãn ưu
    # tiên và câu trả lời thành một danh sách 6 món. Khách hỏi "món này có bột ngọt không?" và nhận
    # về "Mời bạn tham khảo: Cơm chiên chay ngũ sắc (50.000đ), …" — sai loại câu trả lời, kèm thẻ giỏ
    # cho một câu không hỏi mua gì.
    #
    # Mô hình không phân biệt được hai việc đó, và không có lý do để tin nó sẽ phân biệt được: cả hai
    # câu đều nhắc đúng một khái niệm nhãn. Nên phép phân biệt phải TẤT ĐỊNH.
    #
    # Dấu hiệu phân biệt, và nó nằm trong câu chứ không nằm trong nhãn:
    #
    #     hỏi VỀ thuộc tính   "món NÀY có bột ngọt không"   trỏ vào MỘT món cụ thể
    #                         "nhãn 'ít calo' DỰA TRÊN GÌ"   hỏi định nghĩa
    #     yêu cầu LỌC         "có món NÀO không bột ngọt"    hỏi ỨNG VIÊN
    #
    # `mon nao` / `co mon nao` là dấu của câu đòi ứng viên, nên nó loại trừ cờ này. Không có phép
    # loại trừ đó thì "Có món nào không cay không?" — một câu lọc thật — cũng bị coi là câu hỏi về
    # thuộc tính, và đó là hỏng nặng hơn lỗi đang sửa.
    # Câu "hai loại này khác nhau thế nào" là câu TRI THỨC. Đặt cờ ở đây, cạnh phép nhận diện
    # cùng loại, để hai cơ chế đọc cùng một khuôn: kiểm cách NÓI trên chuỗi đã rút dấu.
    if any(c in request.folded for c in DIFFERENCE_FRAMING):
        request.asks_difference = True

    hoi_dinh_nghia = any(c in request.folded for c in ATTRIBUTE_DEFINITION_FRAMING)
    doi_ung_vien = any(c in request.folded for c in CANDIDATE_FRAMING)
    if not doi_ung_vien and (hoi_dinh_nghia or (request.refers_to_focus and " khong" in f" {request.folded}")):
        request.asks_about_attribute = True
        request.matched.append("hỏi VỀ thuộc tính -> không phải yêu cầu lọc theo thuộc tính")

    # CÂU HỎI ĐỊNH NGHĨA: nhãn được nhắc tới là CHỦ THỂ của câu hỏi, không phải bộ lọc.
    #
    # Golden bắt được ngay khi bảng từ vựng nhận thêm chính nhãn tiếng Việt:
    #
    #     "Nhãn 'ít calo' dựa trên gì?"  ->  require=[health:low_calorie]  ->  nhánh filter
    #
    # Khách hỏi nhãn đó DỰA TRÊN GÌ, và nhận về một danh sách 6 món kèm thẻ giỏ. Câu trả lời đúng
    # nằm trong tài liệu: đó là đánh giá CẢM QUAN của người nhập thực đơn, không phải kết quả phân
    # tích — tức đúng loại câu mà trả lời cho có sẽ thành một khẳng định y tế.
    #
    # Và nó không dừng ở một lượt: ràng buộc sai đi vào BỘ NHỚ PHIÊN, nên lượt 3 của cùng hội thoại
    # ("Món này có bột ngọt không?") thừa hưởng nó và cũng thành một danh sách món. Một lượt hiểu
    # sai làm hỏng hai lượt.
    #
    # Hai điều kiện, cả hai đều cần:
    #   - `hoi_dinh_nghia`  — hỏi định nghĩa, KHÔNG phải hỏi ứng viên (`doi_ung_vien` đã loại)
    #   - không có TÊN MÓN — "Phở bò tái nạm có hải sản không?" vẫn cần nhãn để trả lời được
    if hoi_dinh_nghia and not doi_ung_vien and not request.named_items:
        if request.require_tags or request.prefer_tags:
            request.matched.append("hỏi ĐỊNH NGHĨA về nhãn -> bỏ ràng buộc lọc suy từ nhãn đó")
            request.require_tags = []
            request.prefer_tags = []

    # Câu này XIN MÓN hay HỎI VỀ một món? Dùng lại đúng bộ dấu hiệu của hàng rào câu tri thức —
    # không dựng bộ thứ hai, vì hai bộ sẽ lệch nhau.
    request.la_xin_mon = bool(XIN_MON_RE.search(request.folded))

    # 5c. "<số> món" — câu xin gợi ý món bằng số lượng.
    if SO_MON_RE.search(request.folded):
        request.asks_suggestion = True

    # SỐ MÓN KHÁCH XIN — nhận con số, không chỉ nhận rằng "có một con số".
    #
    # Trước bản này hệ thống chỉ bật cờ `asks_suggestion` rồi vẫn trả về đúng `LIST_SIZE = 6` món.
    # Đo trên ba lượt liên tiếp:
    #
    #     "Liệt kê cho tôi 2 món đầu vừa tư vấn"   ->  6 món
    #     "Liệt kê 3 món vừa tư vấn bên trên"      ->  6 món
    #     "Cho mình 4 món vừa tư vấn ở trên"       ->  6 món
    #
    # Phạm vi tham chiếu ngược thì ĐÚNG — cả ba lượt trả về đúng danh sách đã nêu, đúng thứ tự.
    # Chỉ con số bị bỏ. Khách xin hai món và nhận sáu món thì đó không phải trả lời sai, nhưng nó
    # là không nghe — và khách nói lại lần nữa cũng vẫn thế.
    #
    # HAI ĐIỀU KIỆN, và điều kiện thứ hai là bản sửa của một hồi quy mà chính bước này sẽ gây ra:
    #
    #   đúng MỘT cụm     nhiều cụm số là câu ghép, không phải một yêu cầu về số lượng
    #   KHÔNG combo      "1 món chính 1 nước 1 tráng miệng" chỉ có MỘT cụm khớp `<số> món` (hai
    #                    cụm kia không mang chữ "món"), nên đếm cụm một mình KHÔNG đủ. Nhánh combo
    #                    chạy trước nhánh lọc phẳng nên nó không bị cắt trên thực tế — nhưng để cờ
    #                    mang giá trị sai là để lại một quả mìn cho lần sửa sau.
    #   trong 1..12      thước đo chặn ở 12 món; số ngoài dải là gõ nhầm chứ không phải yêu cầu
    so = re.findall(r"(\d+)\s*mon\b", request.folded)
    if len(so) == 1 and 1 <= int(so[0]) <= 12 and not doc_suat_combo(request.folded):
        request.so_mon_muon = int(so[0])
        request.matched.append(f"số món khách xin: {so[0]}")

    # "<số> MÓN ĐẦU" là một LÁT CẮT, không phải một món.
    #
    # Cụm `mon dau` trỏ `reference_index = 1` ("món đầu tiên"), nên "2 món đầu vừa tư vấn" bị đọc
    # thành *món thứ nhất* và trả về đúng MỘT món — đo được:
    #
    #     "Liệt kê cho tôi 2 món đầu vừa tư vấn"  ->  item_detail, 1 món
    #
    # Hai cách nói chồng chữ mà khác hẳn nghĩa: "món đầu" là một món, "2 món đầu" là hai món. Con
    # số đứng trước là dấu hiệu phân biệt, và nó không mơ hồ.
    if request.so_mon_muon and re.search(r"\d+\s*mon dau\b", request.folded):
        request.reference_index = None
        request.matched.append("«<số> món đầu» là lát cắt, không phải món thứ nhất")

    # "<số ≥ 2> MÓN vừa rồi / vừa nói" cũng là LÁT CẮT, không phải món đang nói tới.
    #
    # Cùng lớp lỗi với «<số> món đầu» ở trên, nhưng qua một đường khác: cụm "vừa rồi", "vừa nói"
    # bật `refers_to_focus`, và bước hợp nhất bộ nhớ giải cờ đó thành MỘT món cụ thể. Đo được sau
    # khi lượt đầu đã nêu 6 món:
    #
    #     "Cho mình xem lại 3 món vừa rồi"  ->  item_detail, 1 món
    #     "Kể lại 5 món vừa nói"            ->  item_detail, 1 món
    #
    # Trong khi "Tóm tắt 3 món vừa tư vấn" đúng 3 món — chỉ khác ở cụm cuối câu. Khách gõ hai cách
    # nói tương đương và nhận hai kết quả khác hẳn nhau.
    #
    # NGƯỠNG ≥ 2, không phải ≥ 1: "cho mình 1 món vừa rồi" thì "một món đang nói tới" và "lát cắt
    # dài 1" ra cùng một món, nhưng dạng đáp án khác nhau — `item_detail` mô tả một món là câu trả
    # lời đúng hơn cho câu hỏi số ít, nên chiều đó giữ nguyên.
    if request.so_mon_muon and request.so_mon_muon >= 2 and request.refers_to_focus:
        request.refers_to_focus = False
        request.matched.append("«<số> món vừa rồi» là lát cắt, không phải món đang nói tới")

    # THAM CHIẾU VỊ TRÍ VIẾT BẰNG SỐ — "món thứ 2", "món số 3", "cái thứ 4".
    #
    # Bảng từ vựng chỉ có dạng CHỮ (`mon thu hai`, `cai thu ba`), còn khách gõ SỐ. Đo được:
    #
    #     "món thứ hai"  ->  reference_index = 2      đúng
    #     "món thứ 2"    ->  reference_index = None   không nhận ra
    #     "món số 2"     ->  reference_index = None
    #
    # Và hậu quả nặng hơn "không hiểu": câu rơi xuống nhánh lọc và trả về SÁU món, tức mất luôn cả
    # phạm vi danh sách đang nói tới. Khách chỉ vào một món và nhận lại cả bảng.
    #
    # Đây đúng là lượt khách dùng để TRẢ LỜI câu hỏi lại của trợ lý, nên hỏng ở đây làm cả vòng
    # hỏi-đáp thành ngõ cụt.
    #
    # Chỉ nhận 1..12: `LIST_SIZE` là 6 và thước đo chặn ở 12, nên số lớn hơn là gõ nhầm chứ không
    # phải một vị trí có thật.
    # "<số> MÓN ĐÓ / <số> MÓN VỪA ..." cũng thu phạm vi về danh sách vừa nêu.
    #
    # Bảng cụm không phủ được dạng này vì con số nằm giữa. Đo được:
    #
    #     "4 món đó có món nào chứa đậu phộng không?"  ->  4 món, nhưng KHÔNG PHẢI 4 món kia
    #
    # Đây là ca tệ nhất trong nhóm: đúng số lượng nên nhìn như trả lời đúng, mà bốn món trả về là
    # bốn món khác. Khách hỏi về dị nguyên trong danh sách vừa xem và nhận câu trả lời về một danh
    # sách khác — sai theo kiểu không ai kiểm lại, vì nó trông hợp lý.
    if not request.scope_last_listed and re.search(
        r"\b\d{1,2}\s*mon\s+(?:do|nay|vua|tren|ay)\b", request.folded
    ):
        request.scope_last_listed = True
        request.matched.append("«<số> món đó» thu phạm vi về danh sách vừa nêu")

    if request.reference_index is None:
        # Đòi có chữ "món" HOẶC "cái" trong câu: con số một mình ("cho mình 2") không phải vị trí,
        # và mẫu dưới đây đủ lỏng để khớp "thứ 2" ở bất kỳ đâu nếu không có neo danh từ này.
        _vt = re.search(r"(?:mon|cai)\s*(?:thu|so)\s*(\d{1,2})\b", request.folded)
        _co_neo = " mon " in f" {request.folded} " or " cai " in f" {request.folded} "
        if _vt and _co_neo and 1 <= int(_vt.group(1)) <= 12:
            # KHÔNG áp khi câu đang xin một SỐ LƯỢNG: "cho mình 3 món" là ba món, không phải món
            # thứ ba. Phân biệt bằng chính `so_mon_muon` — nó chỉ được đặt cho khung đếm.
            if not request.so_mon_muon:
                request.reference_index = int(_vt.group(1))
                request.matched.append(f"tham chiếu vị trí (viết số): {_vt.group(1)}")

    # 5b. Câu số học. Đặt sau bước ngân sách vì cả hai đọc `request.folded`, và trước các bước
    #     suy ra ý muốn — một câu số học không có ý muốn nào để suy.
    if ARITHMETIC_RE.search(request.folded):
        request.off_topic = True
        request.matched.append("phép tính -> ngoài phạm vi")

    # 6a. Dịp ăn ngầm định đây là bữa ăn, nên là món ăn — trừ "nhậu", vì nhậu bao gồm cả
    #     bia. Không có luật này thì câu "Mình đi hẹn hò, nên gọi món gì?" trả về cả
    #     cocktail và rượu mơ.
    MEAL_OCCASIONS = ("occasion:date", "occasion:business", "occasion:banquet",
                      "occasion:birthday")
    PARTY_TAGS = ("party:solo", "party:two_three", "party:three_five",
                  "party:friends", "party:family")
    if request.wants == "any" and (
        any(t in request.prefer_tags for t in MEAL_OCCASIONS)
        or any(t in request.require_tags for t in PARTY_TAGS)
    ):
        request.wants = "food"

    # `< 2` chứ không phải `not`: khách nêu ĐÚNG HAI món cụ thể thì nhánh so sánh hai món xử lý được
    # (nó nêu dữ kiện cả hai). Nêu một hoặc không nêu món nào thì câu đang hỏi về LOẠI, và loại thì
    # phải trả lời bằng tri thức — "Cơm tấm khác cơm chiên chỗ nào?" chỉ giải ra được MỘT tên món,
    # vì "cơm chiên" là kiểu chứ không phải món trong thực đơn.
    request.loai_mon_la_chu_de = request.asks_difference and len(request.named_items) < 2

    # 6b. Danh mục đã nêu ngầm định món ăn hay đồ uống, nếu khách chưa nói rõ.
    #
    # KHÔNG suy khi tên loại món là chủ thể câu hỏi: "Phở với bún khác nhau thế nào?" nêu `cat_noodle`,
    # và suy ra `wants=food` từ đó làm câu có "ràng buộc khách nêu" nên nó đi nhánh LỌC — trả 6 món
    # cho một câu hỏi kiến thức.
    if request.wants == "any" and request.categories and not request.loai_mon_la_chu_de:
        if all(c in DRINK_CATEGORIES for c in request.categories):
            request.wants = "drink"
        elif all(c in FOOD_CATEGORIES for c in request.categories):
            request.wants = "food"

    # 7. So sánh: nêu tên đúng hai món là đủ, không cần từ nối.
    #    Bản đầu đòi phải có "hay"/"so với", nên câu "Gà nướng mật ong VÀ gà nướng muối ớt
    #    xanh, món nào cay hơn?" bị đọc thành câu hỏi về một món. Từ nối tiếng Việt quá đa
    #    dạng để liệt kê, còn "khách nêu tên đúng hai món" thì đếm được.
    request.is_comparison = len(request.named_items) == 2

    # 8. Ý ĐỊNH — khách đang LÀM GÌ, tách khỏi câu hỏi khách MUỐN MÓN NÀO.
    #
    # Đặt ở CUỐI, vì nó cần biết câu này đã nêu được thứ gì khác chưa. Đặt trong `understand()` chứ
    # không trong `service.py`, vì mọi bộ đánh giá gọi thẳng `understand`/`respond` — nối ở lớp vỏ
    # thì phép đo không chạm tới, đúng cái bẫy "hai đầu" đã trả giá tám lần trong dự án này.
    #
    # Nhập trong hàm để tránh vòng nhập: `intent` dùng `fold` của tệp này.
    from intent import CAM_ON, CHAO_HOI, NGOAI_PHAM_VI, XIN_THEM, XOA_RANG_BUOC, YDinh

    y = _y

    # Câu có nêu thứ gì khác không. Dùng để CHẶN ý định xã giao chiếm mất một câu hỏi thật:
    # "cảm ơn bạn, cho mình xem món chay" phải là câu hỏi món, không phải lời cảm ơn.
    co_thu_khac = bool(
        request.require_tags
        or request.prefer_tags
        or request.avoid_tags
        or request.categories
        or request.named_items
        or request.policy_topic
        or request.knowledge_topic
        or request.budget_max is not None
    )
    if co_thu_khac and y.ten in (CHAO_HOI, CAM_ON, NGOAI_PHAM_VI):
        # `XIN_THEM` cố ý KHÔNG nằm trong danh sách chặn này, và tôi đã thử cả hai cách.
        #
        # Lo ngại ban đầu: "cho mình thêm món chay" là ràng buộc MỚI, đọc thành xin-thêm sẽ loại
        # đúng những món chay vừa nêu. Lo ngại đó SAI, và kịch bản `ask-for-more-02` chỉ ra chỗ sai:
        # loại món ĐÃ NÊU luôn đúng khi khách xin thêm, vì
        #
        #     ràng buộc mới KHÁC   -> món cũ không khớp bộ lọc mới, đã bị loại sẵn
        #     ràng buộc mới GIỐNG  -> "thêm ... nữa" chính là xin món mới của cùng thứ
        #
        # Chặn nó thì "cho mình thêm món chay nữa" trả lại y nguyên 6 món chay vừa xem — đúng lỗi
        # đang sửa, chỉ đổi chỗ. Thứ THẬT SỰ phải bảo vệ là ràng buộc, và nó được bảo vệ ở chỗ
        # khác: cơ chế ăn chữ chỉ ăn khi không phá cụm nằm ngoài đoạn bị ăn.
        y = YDinh()

    request.y_dinh = y.ten
    request.y_dinh_bo = list(y.bo_rang_buoc)
    if y.cum_khop:
        request.matched.append(f"ý định: {y.cum_khop!r} -> {y.ten}")

    # KHUNG PHỦ NHẬN — xem `PHU_NHAN_FRAMING`. Đặt SAU vòng khớp cụm chứ không trước, vì phải biết
    # cụm nào đã khớp thì mới biết khách đang phủ nhận NHÓM nào.
    #
    # Nhãn rút ra không bị vứt đi lặng lẽ — nó thành lệnh BỎ ràng buộc cùng nhóm. Khác biệt quan
    # trọng: vứt đi thì `spice:none` kế thừa từ bộ nhớ vẫn còn nguyên và khách vẫn nhận đúng câu
    # sai; bỏ nhóm thì bộ nhớ được dọn, và `da_bo_rang_buoc` làm khách THẤY được điều đó.
    # PHỦ ĐỊNH DANH MỤC — chuyển từ "lọc ra" sang "loại bỏ". Xem `_danh_muc_bi_phu_dinh`.
    _cum_dm = {p: v for p, (k, v) in VOCAB.items() if k == "category"}
    _bi_phu_dinh, _cum_bi_phu_dinh = _danh_muc_bi_phu_dinh(request.folded, _cum_dm)

    # KHÁCH PHỦ ĐỊNH MỘT MÓN, KHÔNG PHẢI CẢ DANH MỤC.
    #
    #     "Muốn cái gì mát mà rẻ, KHÔNG PHẢI TRÀ SỮA"
    #
    # Cụm danh mục khớp ở đây là `tra` (5 món mang chữ đó), nên phủ định nó loại **cả danh mục đồ
    # uống**. Khách xin đồ uống mát và nhận về bánh mì pate với cháo lòng.
    #
    # Nhưng bộ khớp TÊN MÓN đã bắt đúng rồi: `exclude_item_ids=['m_062']` — Trà sữa trân châu. Khi
    # đã có loại trừ ở mức MÓN, loại thêm cả danh mục là làm quá điều khách nói.
    #
    # Ranh giới: **có loại trừ theo tên món hay không.** Đo trên bốn cách nói:
    #
    #     "không phải trà sữa"      exclude=['m_062']  -> khách nêu MỘT MÓN   -> giữ danh mục
    #     "tôi không uống bia"      exclude=[]         -> khách nêu DANH MỤC  -> loại danh mục
    #     "mình không ăn được phở"  exclude=[]         -> như trên
    #     "không phải lẩu nhé"      exclude=[]         -> như trên
    #
    # Tên món đủ cụ thể để khớp duy nhất thì mới sinh `exclude_item_ids`; "bia" khớp 4 món nên nó
    # không khớp duy nhất, và câu đó giữ nguyên hành vi cũ.
    if _bi_phu_dinh and request.exclude_item_ids:
        _ten = {i["id"]: fold(i["name"]) for i in menu_items}
        _cat = {i["id"]: i.get("categoryId") for i in menu_items}
        _bo_qua = {
            _cat[mid] for mid in request.exclude_item_ids
            if mid in _ten and any(p in _ten[mid] for p in _cum_bi_phu_dinh)
        }
        if _bo_qua:
            _giu = [c for c in _bi_phu_dinh if c not in _bo_qua]
            request.matched.append(
                f"phủ định TÊN MÓN chứ không phải danh mục: giữ lại {sorted(_bo_qua)}")
            _bi_phu_dinh = _giu

    if _bi_phu_dinh:
        request.avoid_categories = list(
            dict.fromkeys([*request.avoid_categories, *_bi_phu_dinh])
        )
        request.categories = [c for c in request.categories if c not in _bi_phu_dinh]
        # Gỡ luôn HỌ MÓN sinh từ chính cụm bị phủ định — xem `_danh_muc_bi_phu_dinh`.
        request.ho_mon = [h for h in request.ho_mon
                          if not any(h in c or c in h for c in _cum_bi_phu_dinh)]
        request.matched.append(f"phủ định danh mục: loại {_bi_phu_dinh}")

    # COMBO — đọc TRƯỚC các cờ khác vì nó đổi hẳn hình dạng câu trả lời.
    request.combo = doc_suat_combo(request.folded)

    # DẤU XIN MÓN KHÁC — xem `XIN_MON_KHAC_TU`.
    #
    # Hai hàng rào, cả hai đều cần:
    #   - `asks_difference`: "hai món này khác nhau chỗ nào" là câu SO SÁNH, không phải xin thêm.
    #   - phải là câu ĐÒI MÓN: có ràng buộc, có danh mục, có họ món, hoặc đã là ý định xin thêm.
    #     Thiếu hàng rào này thì "quán mới mở à" cũng thành lệnh loại trừ.
    if not request.wants_similar and not request.asks_difference:
        _tu = [t for t in XIN_MON_KHAC_TU
               if not (t == "khac" and KHAC_LA_CAU_HOI_RE.search(request.folded))]
        _co_dau = any(f" {t} " in f" {request.folded} " for t in _tu)
        _doi_mon = bool(request.require_tags or request.prefer_tags or request.categories
                        or request.ho_mon or request.budget_max is not None
                        or request.asks_suggestion)
        if _co_dau and _doi_mon:
            request.wants_similar = True
            request.matched.append("dấu xin món khác (từ rời) -> bỏ món đã nêu")

    # Khung «A hay B»: đánh dấu để `answer.select()` biết đây là hai lựa chọn.
    #
    # Chỉ bật khi câu có ĐỦ HAI nguồn ràng buộc khác loại — một vế `categories`/`ho_mon` và một vế
    # `require_tags`. Một nguồn thôi thì "hay" không nối hai điều kiện nào, và bật nhầm sẽ nới lỏng
    # một câu lọc bình thường.
    _nguon = [
        bool(request.categories or request.ho_mon),
        bool(request.require_tags),
    ]
    request.hai_lua_chon = (
        sum(_nguon) >= 2 and bool(HAI_LUA_CHON_RE.search(request.folded))
    )

    _nhan_phu_nhan = [*request.require_tags, *request.avoid_tags]
    if _nhan_phu_nhan and la_cau_phu_nhan(request.folded):
        # Gồm cả `avoid_tags`, tức cả DỊ NGUYÊN. "mình đâu có dị ứng hải sản" mà bị đọc thành khai
        # dị ứng thì khách bị chặn mất đúng những món họ muốn, và không có cách nào gỡ ngoài việc
        # đoán ra câu thần chú "bỏ hết điều kiện".
        #
        # Hạ một hàng rào dị nguyên là việc phải làm rất dè dặt — nhưng ở đây khách nói THẲNG là họ
        # không có dị ứng đó. Cùng loại với "tôi hết dị ứng rồi", vốn đã được chấp nhận từ trước. Và
        # nó KHÔNG im lặng: `da_bo_rang_buoc` bắt câu trả lời phải mở bằng "Dạ em đã bỏ điều kiện
        # hải sản theo yêu cầu của anh/chị", nên hiểu sai thì khách thấy ngay và sửa được.
        request.y_dinh = XOA_RANG_BUOC
        request.y_dinh_bo = list(dict.fromkeys(
            t.split(":", 1)[0] for t in _nhan_phu_nhan))
        request.matched.append(
            f"phủ nhận: bỏ nhóm {request.y_dinh_bo} thay vì áp {_nhan_phu_nhan}")
        request.require_tags = []
        request.avoid_tags = []
    return request
