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
    asks_price: bool = False
    asks_extreme: str | None = None   # "cheapest" | "priciest"
    is_comparison: bool = False
    off_topic: bool = False
    policy_topic: str | None = None
    unknown_item: bool = False
    unparsed_restriction: bool = False  # khách nêu điều cần tránh mà không hiểu tránh gì
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
_add("hai san|do bien", "allergen_topic", ("allergen:seafood", "cat_seafood"))
_add("dau phong|lac", "allergen_topic", ("allergen:peanut", None))
_add("trung", "allergen_topic", ("allergen:egg", None))
_add("sua|lactose", "allergen_topic", ("allergen:dairy", None))
_add("gluten|bot mi", "allergen_topic", ("allergen:gluten", None))

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

# Độ cay — nhóm phủ 91/91 nên lọc được dứt khoát.
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
_add("chien", "require", "method:fried")
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

# Đối tượng.
_add("tre em|em be|cho be|con nho|tre nho", "require", "audience:child")
_add("nguoi gia|nguoi lon tuoi|ong ba", "require", "audience:elderly")

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

# Câu hỏi giá.
_add("bao nhieu tien|gia bao nhieu|bao nhieu mot|bao nhieu|gia the nao|may tien", "flag", "asks_price")
_add("dat nhat|mac nhat", "flag", "priciest")
_add("re nhat|thap nhat", "flag", "cheapest")

# So sánh.
_add("hay|hoac|khac nhau the nao|nen chon|so voi|voi", "flag", "comparison")

# Chính sách nhà hàng — chưa có kho tri thức nên chỉ để nhận diện và nói thẳng.
_add("may gio mo cua|gio mo cua|mo cua luc nao|may gio dong cua", "policy", "hours")
_add("thanh toan|tra tien|quet the|chuyen khoan", "policy", "payment")
_add("do xe|bai xe|gui xe", "policy", "parking")
_add("wifi|mat khau wifi", "policy", "wifi")
_add("dat ban|dat cho", "policy", "booking")
_add("giao hang|ship|giao den nha", "policy", "delivery")
_add("bao nhieu calo|calo|natri|dinh duong|bao nhieu duong", "policy", "nutrition")
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
    asks_about_named = bool(request.named_items) and " co " in working and " khong" in working
    request.asks_about_named_dish = asks_about_named

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
