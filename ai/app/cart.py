# -*- coding: utf-8 -*-
"""Thẻ giỏ hàng gợi ý — sinh từ ĐÚNG danh sách món mà `answer.py` đã chọn.

Nguyên tắc trung tâm: KHÔNG có đường chọn món thứ hai
-----------------------------------------------------
Thẻ giỏ nhận vào **danh sách món đã lọc**, không nhận `Request` rồi tự lọc lại. Nếu nó tự lọc thì
có **hai đường chọn món**, và hai đường sẽ lệch nhau — không phải "có thể lệch", mà **sẽ**, vì
mỗi lần sửa ràng buộc ở một đường là một cơ hội quên sửa đường kia.

Lệch ở đây không phải chuyện chất lượng: nó nghĩa là **thẻ giỏ chứa món khách dị ứng**. Bản cũ có
8 đường xử lý chồng nhau và 2 trong số đó bị một cờ tắt mà không ai biết — đó là cái giá của
đường thứ hai.

Nên chữ ký hàm cố tình **không nhận `menu_items`**: không có thực đơn thì không thể tự lọc, kể cả
khi ai đó muốn.

Năm bất biến, và vì sao mỗi cái tồn tại
---------------------------------------
1. Món phải TỒN TẠI trong thực đơn, giá lấy từ thực đơn. Giá do mô hình hay do người viết tay là
   giá có thể sai, và sai giá là chuyện tiền của khách.
2. `requires_customer_confirmation` LUÔN `true`. Không nhánh nào đặt `false`. Đây là ranh giới
   "AI không tự đặt món" — và nó phải là **hằng số**, không phải một quyết định theo ngữ cảnh, vì
   một quyết định theo ngữ cảnh sẽ có ngày sai ngữ cảnh.
3. Món bị `avoid_tags` loại KHÔNG BAO GIỜ vào thẻ. Kiểm lại ở đây dù `answer.select()` đã lọc —
   xem mục "vì sao kiểm hai lần" dưới.
4. Chỉ sinh thẻ ở nhánh `filter`, `compare`, `item_detail`. Nhánh `clarify`, `no_data`, `refuse`
   không có thẻ: gợi ý đặt món khi **chưa hiểu câu hỏi** là sai, và gợi ý đặt món kèm câu "mình
   chưa có dữ liệu" thì tự mâu thuẫn.
5. `reason` nêu RÀNG BUỘC ĐÃ THỎA, không phải câu quảng cáo. Sinh từ `require_tags`/`avoid_tags`
   nên **không thể bịa** — nó chỉ nhắc lại điều khách vừa nói.

Vì sao kiểm dị nguyên HAI LẦN
-----------------------------
`answer.select()` đã fail-closed rồi, nên phép kiểm ở đây là **dư về mặt logic**. Giữ nó vì:

- Nó rẻ (một phép kiểm tập hợp) và cái nó chặn thì đắt.
- `answer.py` và `cart.py` do **hai người khác nhau** sở hữu (TV4 sở hữu cả hai, nhưng hợp đồng
  giữa chúng là hợp đồng thật). Một thay đổi ở `select()` mà quên `cart` là chuyện xảy ra được.
- Nó là **phép kiểm cuối cùng trước khi rời hệ thống**. Sau điểm này không còn ai canh.

Đây là ngoại lệ có chủ ý với nguyên tắc "mỗi việc một đường": nguyên tắc đó chống **hai đường
QUYẾT ĐỊNH**, còn đây là một đường quyết định cộng một **phép kiểm cuối**. Khác nhau ở chỗ phép
kiểm không bao giờ *thêm* món — nó chỉ có thể bỏ, và nếu nó phải bỏ thì đó là lỗi cần báo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from understand import Request

# Nhánh được phép sinh thẻ giỏ. Danh sách TRẮNG, không phải danh sách đen: nhánh mới thêm sau này
# mặc định KHÔNG có thẻ, và người thêm phải chủ động nghĩ xem nó có nên có.
BRANCHES_WITH_CART = ("filter", "compare", "item_detail", "extreme", "price_lookup")

# Số thẻ tối đa = số món câu trả lời NÊU RA. Lấy từ `answer.LIST_SIZE`, không viết lại con số.
#
# Vì sao: hai hằng số này PHẢI khớp, và chúng đã lệch — 3 thẻ cho 6 món được nêu
# -----------------------------------------------------------------------------
# Bản trước đặt `MAX_CART_ACTIONS = 3` với lý lẽ "giỏ gợi ý dài hơn thế thì khách không đọc, và nó
# biến câu tư vấn thành danh mục". Lý lẽ đó hợp lý — nhưng nó áp cho SỐ THẺ mà không áp cho SỐ MÓN
# ĐƯỢC NÊU, và `answer.LIST_SIZE` là 6.
#
# Hậu quả đo được khi hỏi stack thật: câu trả lời nêu Bánh mì pate, Cháo lòng, Gỏi cuốn chay, Đậu hũ
# sốt cà chua, Cơm chiên chay ngũ sắc, Xôi gà Hà Nội — **sáu món** — còn thẻ giỏ có **ba**. Khách đọc
# sáu lựa chọn và bấm chọn được ba; ba món còn lại phải gõ tay.
#
# Đây là dạng NHẸ của đúng vấn đề "trả lời một kiểu, thẻ giỏ một kiểu", và golden KHÔNG bắt được nó:
# bất biến thẻ giỏ đòi *thẻ ⊆ món được nêu*, không đòi chiều ngược lại. Một bất biến một chiều thì
# im lặng với chiều còn lại.
#
# Vì sao nâng thẻ lên 6 thay vì hạ số món xuống 3: `LIST_SIZE = 6` được chọn vì "ca đòi nhiều nhất là
# 5 món", nên hạ xuống 3 làm hỏng những ca đó. Giữa hai hằng số, cái có căn cứ đo được thì giữ.
#
# Cái giá phải nói ra: 6 thẻ dài hơn 3 trên điện thoại. Nhưng nó thẳng thắn — khách thấy đúng số
# lựa chọn mình đọc được, thay vì thấy sáu rồi bấm được ba.
from answer import LIST_SIZE  # noqa: E402  (không có vòng: `answer` không import `cart`)

MAX_CART_ACTIONS = LIST_SIZE

_TAG_VI = {
    "spice:none": "không cay", "spice:mild": "cay nhẹ", "spice:medium": "cay vừa",
    "spice:hot": "cay đậm",
    "diet:vegetarian": "món chay", "diet:vegan": "thuần chay",
    "party:solo": "khẩu phần một người", "party:two_three": "cho 2–3 người",
    "party:three_five": "cho 3–5 người",
    "allergen:seafood": "không ghi nhận hải sản", "allergen:dairy": "không ghi nhận sữa",
    "allergen:egg": "không ghi nhận trứng", "allergen:peanut": "không ghi nhận đậu phộng",
    "allergen:gluten": "không ghi nhận gluten",
}


class CartError(ValueError):
    """Thẻ giỏ vi phạm một bất biến. Là lỗi lập trình, không phải lỗi dữ liệu của khách."""


@dataclass(frozen=True)
class CartAction:
    """Một dòng trong giỏ gợi ý. `frozen` để không ai sửa được sau khi đã kiểm."""

    menu_item_id: str
    name: str
    price: int
    quantity: int
    reason: str
    evidence_ids: tuple[str, ...] = ()
    # Không có tham số. Đây là ranh giới "AI không tự đặt món", nên nó là HẰNG SỐ.
    requires_customer_confirmation: bool = field(default=True, init=False)

    def to_payload(self) -> dict[str, Any]:
        return {
            "menu_item_id": self.menu_item_id,
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
            "requires_customer_confirmation": True,
        }


def _reason(item: dict, request: Request, category_names: dict[str, str]) -> str:
    """Câu lý do, ghép từ ràng buộc khách đã nêu và món này THỎA.

    Chỉ nêu ràng buộc mà món này **thật sự thỏa**, không nêu mọi ràng buộc khách nói. Nêu bừa thì
    câu lý do thành câu quảng cáo, và khách không kiểm được nó đúng hay sai.

    Dị nguyên nói "KHÔNG GHI NHẬN", không nói "không có" — nhãn dị nguyên chỉ phủ 44/91 món nên
    "không có nhãn" không đồng nghĩa "không chứa". Đây là chỗ dễ nói quá nhất trong cả hệ thống.
    """
    parts: list[str] = []

    # Danh mục TRƯỚC nhãn, vì nó thường là ràng buộc chính khách nêu. "Món chay" đi vào
    # `categories` chứ không vào `require_tags` (bộ hiểu câu hỏi map nó thành `cat_vegetarian`),
    # nên bỏ qua danh mục là bỏ mất đúng ràng buộc quan trọng nhất.
    #
    # Lỗi đó có thật: câu "món chay dưới 100 nghìn" từng cho lý do chỉ nói "Trong ngân sách
    # 100.000đ" — không nhắc chay một chữ. Và test đầu tiên của tôi KHÔNG bắt được vì nó chấp
    # nhận "chay" HOẶC "không cay", nên câu có cả hai đã qua nhờ vế thứ hai.
    if item.get("categoryId") in request.categories:
        ten = category_names.get(item["categoryId"], "")
        if ten:
            parts.append(f"thuộc nhóm {ten}")

    for tag in request.require_tags:
        if tag in item["tags"]:
            parts.append(_TAG_VI.get(tag, tag))
    for tag in request.avoid_tags:
        if tag not in item["tags"]:
            parts.append(_TAG_VI.get(tag, f"không ghi nhận {tag}"))
    if request.budget_max is not None and item["price"] <= request.budget_max:
        moc = f"{request.budget_max:,}".replace(",", ".") + "đ"
        parts.append(f"trong ngân sách {moc}")

    if not parts:
        # Không ràng buộc nào -> nói thẳng đây là món phù hợp chung, đừng bịa một lý do.
        return "Phù hợp với yêu cầu bạn vừa nêu."

    # Chỉ viết hoa CHỮ ĐẦU. `str.capitalize()` viết hoa chữ đầu *và viết thường tất cả phần còn
    # lại*, nên tên nhóm lấy từ thực đơn ("Món chay") bị hạ thành "món chay" — tức câu lý do
    # không còn khớp dữ liệu gốc.
    #
    # Đây là lần thứ HAI cùng một hàm gây lỗi trong dự án này (lần đầu ở
    # `session.rolling_summary`, làm `season:summer` thành `Season:summer`). `str.capitalize()`
    # gần như luôn sai khi câu có chứa danh từ riêng hoặc mã máy.
    cau = "; ".join(parts)
    return f"{cau[0].upper()}{cau[1:]}."


def build_cart(
    request: Request,
    selected_items: list[dict],
    branch: str,
    kind: str,
    category_names: dict[str, str] | None = None,
) -> list[CartAction]:
    """Sinh thẻ giỏ từ danh sách món ĐÃ ĐƯỢC `answer.py` chọn.

    Cố tình KHÔNG nhận `menu_items`: không có thực đơn thì không thể tự lọc lại, nên không thể
    trở thành đường chọn món thứ hai.

    `category_names` là **bảng tra tên** (`cat_vegetarian` → "Món chay"), không phải danh sách
    món — nên nó không mở lại đường lọc. Cần nó vì câu lý do phải gọi được tên nhóm mà khách nêu,
    và tên nhóm chỉ có trong thực đơn. Truyền bảng tra thay vì viết cứng 13 tên vào tệp này, để
    tên nhóm không trôi khỏi thực đơn.

    Trả về danh sách rỗng khi nhánh không được phép có thẻ. Rỗng là câu trả lời đúng ở đó, không
    phải thất bại.
    """
    # Bất biến 4 — danh sách trắng theo nhánh.
    if branch.split(":")[0] not in BRANCHES_WITH_CART:
        return []
    if kind in ("clarify", "no_data", "refuse"):
        return []
    if not selected_items:
        return []

    # Bất biến 3 — phép kiểm CUỐI trước khi rời hệ thống. Xem docstring đầu tệp về việc kiểm hai
    # lần. Nếu chỗ này phải bỏ món thì `answer.select()` đã hỏng, nên nó là LỖI, không phải lọc.
    avoid = set(request.avoid_tags)
    if avoid:
        vi_pham = [i["id"] for i in selected_items if avoid & set(i["tags"])]
        if vi_pham:
            raise CartError(
                f"món {vi_pham} mang nhãn cần tránh {sorted(avoid)} nhưng đã qua được "
                "answer.select() — lọc fail-closed đang hỏng, KHÔNG được lặng lẽ bỏ món ở đây "
                "rồi coi như xong"
            )

    actions: list[CartAction] = []
    for item in selected_items[:MAX_CART_ACTIONS]:
        # Bất biến 1 — giá lấy từ thực đơn, không nhận từ đâu khác.
        actions.append(
            CartAction(
                menu_item_id=item["id"],
                name=item["name"],
                price=int(item["price"]),
                quantity=1,
                reason=_reason(item, request, category_names or {}),
                evidence_ids=(f"menu:{item['id']}",),
            )
        )
    return actions


def cart_payload(actions: list[CartAction]) -> list[dict[str, Any]]:
    return [a.to_payload() for a in actions]
