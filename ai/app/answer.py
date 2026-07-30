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

from dataclasses import dataclass, field

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
    if request.categories:
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
    if request.is_comparison and len(named) == 2:
        first, second = named
        gap = abs(first["price"] - second["price"])
        cheaper = first if first["price"] <= second["price"] else second
        return Reply(
            text=(
                f"{phrase(first)} và {phrase(second)}. "
                f"Chênh nhau {money(gap)}, {cheaper['name']} nhẹ ví hơn. "
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
        return Reply(
            text=f"Món {label} là {item['name']}, giá {money(item['price'])} ạ.",
            items=[item["id"]],
            kind="fact",
            branch=f"extreme:{request.asks_extreme}",
        )

    # 6a. Câu hỏi về dị nguyên của một món đã nêu tên.
    if named and request.asks_allergy:
        item = named[0]
        present = [t for t in request.avoid_tags if t in item["tags"]]
        if present:
            return Reply(
                text=(
                    f"Thực đơn có ghi nhận thành phần bạn cần tránh trong {phrase(item)}, "
                    f"nên mình không gợi ý món này. {STAFF_NOTE}"
                ),
                items=[item["id"]],
                kind="fact",
                branch="allergen_named_dish",
            )
        return Reply(
            text=(
                f"Thực đơn không ghi nhận thành phần đó trong {phrase(item)}. "
                # KHÔNG nối `STAFF_NOTE` sau chữ "nên": nó bắt đầu bằng chữ B hoa nên câu ra
                # "…thực đơn ghi, nên Bạn nhắc nhân viên…". Lỗi chữ, nhưng KHÁCH ĐỌC THẤY, và nó
                # chỉ hiện khi đọc câu trả lời thật — thước đo chấm nội dung nên không bắt được.
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
    if named and (
        request.reference_index is not None
        or (not request.require_tags and not request.categories)
    ):
        item = named[0]
        spice = next((t for t in item["tags"] if t.startswith("spice:")), None)
        spice_vi = {
            "spice:none": "không cay",
            "spice:mild": "cay nhẹ",
            "spice:medium": "cay vừa",
            "spice:hot": "cay đậm",
        }.get(spice or "", "")
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
    said_something = bool(
        request.require_tags
        or request.prefer_tags
        or request.avoid_tags
        or request.categories
        or request.budget_max is not None
        or khach_neu_wants
    )
    if not said_something:
        return Reply(
            text=(
                "Để gợi ý đúng ý bạn, cho mình biết bạn muốn món ăn hay đồ uống, "
                "đi mấy người, và tầm giá khoảng bao nhiêu ạ?"
            ),
            kind="clarify",
            asks_back=True,
            branch="clarify",
        )

    picked = _order(select(request, items), request.prefer_tags, request.wants)
    if not picked:
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
