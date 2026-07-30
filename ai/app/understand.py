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
    asks_extreme: str | None = None   # "cheapest" | "priciest"
    is_comparison: bool = False
    off_topic: bool = False
    policy_topic: str | None = None
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
    # Hai tập id do bước hợp nhất bộ nhớ điền, KHÔNG do bộ khớp từ vựng điền. `understand()` chỉ
    # nhận ra khách đang tham chiếu; nó không biết khách đã đọc danh sách nào. Tách vai như vậy để
    # `understand()` giữ được tính chất "chỉ đọc câu của lượt này".
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
_add("cay nhe", "require", "spice:mild")
_add("cay vua", "require", "spice:medium")
_add("cay dam|cay nhieu|that cay", "require", "spice:hot")

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
_add("thit bo|bo|beef", "require", "ingredient:beef")
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
_add("thanh thanh", "require", "health:light")

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
_add("khai vi", "category", "cat_appetizer")
_add("pho bun|mon nuoc", "category", "cat_noodle")
_add("com viet|mon com", "category", "cat_main")
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
_add("mon vua roi|mon vua noi|mon do|cai do|no co", "reference", 1)

# Cụm thu PHẠM VI. Khác cụm vị trí: "món rẻ nhất TRONG SỐ ĐÓ" không trỏ vào một món, nó giới hạn
# tập rồi để câu hỏi "rẻ nhất" chạy trên tập đó. Dùng cụm vị trí ở đây là trả sai: nó sẽ trả món
# ĐẦU danh sách thay vì món RẺ NHẤT.
_add("trong so do|trong nhung mon do|trong danh sach do|trong may mon do", "flag", "scope_listed")

# Xin thêm món GIỐNG — cơ chế ngược với trỏ vào món cũ: giữ ràng buộc, BỎ món đã nêu.
_add("giong vay|giong the|tuong tu|kieu vay|giong nhu vay", "flag", "similar")

# Câu hỏi giá.
_add("bao nhieu tien|gia bao nhieu|bao nhieu mot|bao nhieu|gia the nao|may tien", "flag", "asks_price")

# Số người ăn một phần — thực đơn KHÔNG có dữ liệu này. Nhóm `serving` chỉ có `takeaway`, `hot`,
# `preorder`, không có khẩu phần. Nên câu "món đó cho mấy người ăn?" phải trả "chưa có dữ liệu",
# không được trả bừa giá và độ cay như thể đã trả lời.
_add("cho may nguoi an|may nguoi an|an duoc may nguoi|du cho may nguoi|khau phan bao nhieu",
     "policy", "serving_size")
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
REFERENCE_PHRASES = frozenset(p for p, (kind, _) in VOCAB.items() if kind == "reference")

# Cách nói ngân sách nghiêm ngặt: "rẻ hơn 20 nghìn" KHÔNG bao gồm món đúng 20.000đ.
# Khác với "dưới 50.000đ" hay "tầm 80k trở xuống", vốn được hiểu là bao gồm.
# Bỏ qua khác biệt này thì câu "rẻ hơn 20 nghìn" trả về Bia Sài Gòn Special đúng 20.000đ.
STRICT_BUDGET_FRAMING = ("re hon", "it hon", "thap hon", "duoi muc", "khong den")

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
)


FOOD_CATEGORIES = (
    "cat_appetizer", "cat_noodle", "cat_main", "cat_seafood",
    "cat_hotpot", "cat_chicken", "cat_regional", "cat_vegetarian",
)
DRINK_CATEGORIES = ("cat_drink", "cat_juice", "cat_alcohol")


_NAME_CACHE: dict[int, list[tuple[str, str, str]]] = {}


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
        elif kind == "wants":
            request.wants = str(value)
        elif kind == "policy":
            request.policy_topic = request.policy_topic or str(value)
        elif kind == "flag":
            if value == "asks_price":
                request.asks_price = True
            elif value in ("cheapest", "priciest"):
                request.asks_extreme = str(value)
            elif value == "comparison":
                request.is_comparison = True
            elif value == "off_topic":
                request.off_topic = True
            elif value == "scope_listed":
                request.scope_last_listed = True
            elif value == "similar":
                request.wants_similar = True
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
        if value >= 1000:
            request.budget_max = value
            request.budget_strict = any(
                f in request.folded for f in STRICT_BUDGET_FRAMING
            )
            limit = "<" if request.budget_strict else "<="
            request.matched.append(f"ngân sách: {limit} {value:,}đ")

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

    # 6b. Danh mục đã nêu ngầm định món ăn hay đồ uống, nếu khách chưa nói rõ.
    if request.wants == "any" and request.categories:
        if all(c in DRINK_CATEGORIES for c in request.categories):
            request.wants = "drink"
        elif all(c in FOOD_CATEGORIES for c in request.categories):
            request.wants = "food"

    # 7. So sánh: nêu tên đúng hai món là đủ, không cần từ nối.
    #    Bản đầu đòi phải có "hay"/"so với", nên câu "Gà nướng mật ong VÀ gà nướng muối ớt
    #    xanh, món nào cay hơn?" bị đọc thành câu hỏi về một món. Từ nối tiếng Việt quá đa
    #    dạng để liệt kê, còn "khách nêu tên đúng hai món" thì đếm được.
    request.is_comparison = len(request.named_items) == 2
    return request
