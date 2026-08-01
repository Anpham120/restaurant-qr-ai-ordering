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
    asks_suggestion: bool = False
    # Khách hỏi hai LOẠI món khác nhau thế nào. Câu tri thức, nên tên loại món trong câu KHÔNG được
    # đọc thành ràng buộc lọc — xem `DIFFERENCE_FRAMING`.
    asks_difference: bool = False
    # Ý ĐỊNH của lượt này — xem `intent.py`. Mặc định `hoi_mon`, tức "đi tiếp xuống tầng chọn món".
    y_dinh: str = "hoi_mon"
    # Nhóm ràng buộc khách bảo BỎ ("allergen", "all"). Đây là điều `llm_understand` KHÔNG diễn đạt
    # được: hợp đồng của nó chỉ cho THÊM nhãn, nên "tôi hết dị ứng rồi" không có cách nào nói ra.
    y_dinh_bo: list[str] = field(default_factory=list)
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
_add("tom|tom su|tom hum|cua|ghe|muc|ca|ca bien|ca hoi|nghieu|so|oc|hau",
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
_add("dac san vung mien", "category", "cat_regional")
_add("ca phe|tra", "category", "cat_drink")
_add("nuoc ep|sinh to", "category", "cat_juice")
_add("trang mieng|do ngot", "category", "cat_dessert")
_add("trai cay", "category", "cat_fruit")
_add("bia|ruou|do co con", "category", "cat_alcohol")

# Món ăn hay đồ uống — đúng yêu cầu "không phải bảo tư vấn món mà cứ đưa bia vào".
_add("mon an|do an|an gi|minh doi|toi doi|bua trua|bua toi|bua sang|an com", "wants", "food")
_add("do uong|thuc uong|uong gi|nuoc gi", "wants", "drink")

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
_add("trong so do|trong nhung mon do|trong danh sach do|trong may mon do", "flag", "scope_listed")
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
_add("tuoi|em nho|chau nho|be nho|di cung be|co be", "require", "audience:child")

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
_add("may gio mo cua|gio mo cua|mo cua luc nao|may gio dong cua|gio dong cua|mo cua den may gio", "policy", "hours")
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
_add("co menu tre em|menu cho tre em|phan an tre em", "policy", "children")
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


def la_cau_phu_nhan(folded: str) -> bool:
    """Câu có phải là PHỦ NHẬN một ràng buộc không."""
    return (any(k in folded for k in PHU_NHAN_FRAMING)
            or bool(PHU_NHAN_ROI_RE.search(folded)))


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
            if item_id in request.named_items:
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

    # 5c. "<số> món" — câu xin gợi ý món bằng số lượng.
    if SO_MON_RE.search(request.folded):
        request.asks_suggestion = True

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
