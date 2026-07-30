# -*- coding: utf-8 -*-
"""Bộ nhớ trong một phiên QR — hợp nhất ràng buộc qua nhiều lượt.

Vì sao khâu này tồn tại
-----------------------
119 ca đánh giá hiện có đều **một lượt**, nên chúng không đo được điều quan trọng nhất của một
cuộc hội thoại thật: khách khai dị ứng ở lượt 1 rồi hỏi tiếp ở lượt 5 **mà không nhắc lại**.

Nếu bộ nhớ quên, hệ thống mời đúng món khách không ăn được — và câu hỏi ở lượt 5 nhìn hoàn toàn
vô hại nên không ai nghi. Đó là lỗi an toàn khó thấy nhất mà hệ thống này có thể mắc.

Ba quy tắc hợp nhất, và chúng KHÁC NHAU
---------------------------------------
Sai lầm dễ mắc là dùng một quy tắc cho cả ba loại. Mỗi loại có lý do riêng:

    dị nguyên        CỘNG DỒN, không bao giờ bỏ    khai một lần là giữ suốt phiên
    ràng buộc cứng   lượt mới GHI ĐÈ cùng nhóm     "rẻ hơn nữa" phải THAY ngân sách cũ
    ngữ cảnh         cộng vào, giữ 5 gần nhất      sở thích tích lũy nhưng không phình

Thử đổi quy tắc cho nhau thì thấy ngay từng cái sai ở đâu:

- Nếu **dị nguyên** cũng ghi đè: khách nói "mình dị ứng hải sản" rồi lượt sau nói "mình không ăn
  được sữa" → mất bảo vệ hải sản. Đây là lý do quy tắc này là **chốt an toàn**.
- Nếu **ràng buộc cứng** cũng cộng dồn: "dưới 200k" rồi "rẻ hơn nữa đi" → hệ thống giữ cả hai
  ngân sách, và cái nào thắng thì tùy thứ tự áp. Ghi đè theo NHÓM (không phải theo nhãn) là điểm
  cốt lõi: `spice:none` phải đẩy `spice:hot` ra, chứ không nằm cạnh nó.
- Nếu **ngữ cảnh** cũng ghi đè: khách nói "đi hẹn hò" rồi "trời nóng" → mất một trong hai, dù cả
  hai đều đúng và đều chỉ dùng để sắp thứ tự.

Rolling summary sinh TẤT ĐỊNH
-----------------------------
Tóm tắt phiên **không nhờ mô hình sinh**. Câu trả lời sai thì sai **một lượt**; bộ nhớ sai thì
sai **suốt phiên** — mọi lượt sau đều đọc lại cái sai đó. Nhờ mô hình viết tóm tắt là mở đúng
đường cho nó bịa vào bộ nhớ.

Nên tóm tắt ở đây là một câu ghép từ chính các trường đã hợp nhất. Nó không hay bằng câu mô hình
viết, và đó là đánh đổi có chủ ý.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from understand import Request

# Số nhãn ngữ cảnh giữ lại. Ngữ cảnh tích lũy qua lượt nên phải có trần, nếu không thì lượt thứ
# 20 mang theo 20 sở thích và phép sắp thứ tự mất ý nghĩa — mọi món đều khớp một cái gì đó.
#
# Chọn 5 vì đó là số nhãn `prefer` mà một câu dài nhất trong 119 ca sinh ra (2), nhân đôi rồi
# cộng một. Không có căn cứ mạnh hơn, và nếu tập kịch bản đa lượt cho thấy 5 là sai thì sửa —
# nhưng phải sửa vì SỐ ĐO, không vì cảm giác.
MAX_CONTEXT_TAGS = 5

# Số món đã gợi ý còn được nhớ, để "cho món khác đi" biết phải bỏ những gì. Trần này chống việc
# sau 10 lượt thì mọi món đều đã bị gợi ý và hệ thống không còn gì để nói.
MAX_SUGGESTED_MEMORY = 24

# Nhóm nhãn được coi là RÀNG BUỘC CỨNG — lượt mới ghi đè cùng nhóm.
#
# Cả bốn nhóm này phủ 91/91 món, và đó không phải trùng hợp: chỉ nhóm phủ hết mới lọc dứt khoát
# được, nên chỉ chúng mới xứng là ràng buộc cứng. Nhóm phủ một phần (occasion 79/91, flavour
# 72/91...) thuộc NGỮ CẢNH, vì thiếu nhãn ở đó nghĩa là *chưa ghi nhận*, không phải *không phù
# hợp*.
HARD_CONSTRAINT_GROUPS = ("spice", "price", "party", "season")

# Nhóm nhãn dị nguyên — cộng dồn, không bao giờ bỏ.
ALLERGEN_PREFIX = "allergen:"

MEMORY_VERSION = "v3"


@dataclass
class SessionState:
    """Bộ nhớ một phiên QR. Backend sở hữu việc lưu và XÓA nó, không phải dịch vụ này.

    Việc xóa đã đúng và không cần làm lại: `IChatStore.DeleteSessionsByTableSession` được gọi
    khi đóng phiên, khi phiên hết hạn, và khi thanh toán. Nên "bộ nhớ chỉ mất khi đóng phiên"
    là hành vi của backend, dịch vụ AI chỉ đọc và ghi.
    """

    avoid_tags: list[str] = field(default_factory=list)
    hard_tags: list[str] = field(default_factory=list)
    context_tags: list[str] = field(default_factory=list)
    budget_max: int | None = None
    budget_strict: bool = False
    wants: str = "any"
    suggested_item_ids: list[str] = field(default_factory=list)
    rejected_item_ids: list[str] = field(default_factory=list)
    turn_count: int = 0

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "SessionState":
        """Đọc bộ nhớ backend gửi lên. Trường lạ hoặc sai kiểu bị BỎ QUA, không làm sập.

        Vì sao khoan dung ở đây mà nghiêm ở kho tri thức: kho tri thức là dữ liệu ta tự viết nên
        sai là lỗi cần chặn ngay; còn bộ nhớ phiên đến từ mạng, và một phiên có dữ liệu hỏng
        không được làm chết cả luồng trả lời khách. Mất bộ nhớ thì tệ; sập thì tệ hơn.
        """
        if not isinstance(payload, dict):
            return cls()

        def tags(key: str, keep: str | None = None) -> list[str]:
            raw = payload.get(key)
            if not isinstance(raw, list):
                return []
            out = [t for t in raw if isinstance(t, str) and t and ":" in t]
            if keep is not None:
                out = [t for t in out if t.startswith(keep)]
            return list(dict.fromkeys(out))

        def ids(key: str) -> list[str]:
            raw = payload.get(key)
            if not isinstance(raw, list):
                return []
            return list(dict.fromkeys(i for i in raw if isinstance(i, str) and i))

        budget = payload.get("budget_max")
        wants = payload.get("wants")
        return cls(
            avoid_tags=tags("avoid_tags", keep=ALLERGEN_PREFIX),
            hard_tags=[
                t for t in tags("hard_tags")
                if t.split(":", 1)[0] in HARD_CONSTRAINT_GROUPS
            ],
            context_tags=tags("context_tags")[:MAX_CONTEXT_TAGS],
            budget_max=budget if isinstance(budget, int) and budget > 0 else None,
            budget_strict=bool(payload.get("budget_strict")),
            wants=wants if wants in ("food", "drink", "any") else "any",
            suggested_item_ids=ids("suggested_item_ids")[:MAX_SUGGESTED_MEMORY],
            rejected_item_ids=ids("rejected_item_ids")[:MAX_SUGGESTED_MEMORY],
            turn_count=payload.get("turn_count") if isinstance(payload.get("turn_count"), int) else 0,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "avoid_tags": list(self.avoid_tags),
            "hard_tags": list(self.hard_tags),
            "context_tags": list(self.context_tags),
            "budget_max": self.budget_max,
            "budget_strict": self.budget_strict,
            "wants": self.wants,
            "suggested_item_ids": list(self.suggested_item_ids),
            "rejected_item_ids": list(self.rejected_item_ids),
            "turn_count": self.turn_count,
        }


def _group(tag: str) -> str:
    return tag.split(":", 1)[0]


def merge_into_request(request: Request, state: SessionState) -> Request:
    """Áp bộ nhớ phiên vào yêu cầu của lượt hiện tại, theo ba quy tắc khác nhau.

    Trả về một `Request` MỚI thay vì sửa tại chỗ, để chỗ gọi còn giữ được yêu cầu gốc của lượt
    này — cần nó để biết lượt này khách nói gì mới, tách khỏi cái đã nhớ từ trước.
    """
    # QUY TẮC 1 — dị nguyên: CỘNG DỒN, không bao giờ bỏ. Đây là chốt an toàn của khâu này.
    avoid = list(dict.fromkeys([*state.avoid_tags, *request.avoid_tags]))

    # QUY TẮC 2 — ràng buộc cứng: lượt mới GHI ĐÈ cùng NHÓM.
    #
    # Ghi đè theo nhóm chứ không theo nhãn: `spice:none` phải đẩy `spice:hot` ra khỏi bộ nhớ,
    # không phải nằm cạnh nó. Nằm cạnh thì phép lọc AND cho kết quả rỗng và khách nhận "không
    # có món nào" cho một yêu cầu hoàn toàn hợp lệ.
    new_groups = {_group(t) for t in request.require_tags}
    carried_hard = [t for t in state.hard_tags if _group(t) not in new_groups]
    require = list(dict.fromkeys([*carried_hard, *request.require_tags]))

    # Ngân sách cũng là ràng buộc cứng: lượt mới có nêu thì thay, không nêu thì giữ.
    if request.budget_max is not None:
        budget_max, budget_strict = request.budget_max, request.budget_strict
    else:
        budget_max, budget_strict = state.budget_max, state.budget_strict

    # QUY TẮC 3 — ngữ cảnh: cộng vào, giữ MAX_CONTEXT_TAGS gần nhất.
    #
    # Nhãn của lượt này đứng TRƯỚC, nên khi phải cắt thì cắt cái cũ nhất. Sở thích khách vừa nêu
    # đáng tin hơn sở thích ba lượt trước.
    prefer = list(dict.fromkeys([*request.prefer_tags, *state.context_tags]))[:MAX_CONTEXT_TAGS]

    # `wants` (món ăn / đồ uống) là ràng buộc cứng nhưng không mang dạng nhãn, nên xử riêng.
    wants = request.wants if request.wants != "any" else state.wants

    return replace(
        request,
        avoid_tags=avoid,
        require_tags=require,
        prefer_tags=prefer,
        budget_max=budget_max,
        budget_strict=budget_strict,
        wants=wants,
    )


def update_state(state: SessionState, merged: Request, replied_item_ids: list[str]) -> SessionState:
    """Ghi bộ nhớ sau khi đã trả lời. Nhận `Request` ĐÃ hợp nhất, không phải bản gốc.

    Nhận bản đã hợp nhất là điểm quan trọng: nếu ghi từ bản gốc thì dị nguyên khai ở lượt 1 sẽ
    không có trong bản gốc của lượt 2, và bộ nhớ **mất nó ngay lượt sau** — đúng lỗi mà cả khâu
    này tồn tại để chống.
    """
    return SessionState(
        avoid_tags=[t for t in merged.avoid_tags if t.startswith(ALLERGEN_PREFIX)],
        hard_tags=[t for t in merged.require_tags if _group(t) in HARD_CONSTRAINT_GROUPS],
        context_tags=list(merged.prefer_tags)[:MAX_CONTEXT_TAGS],
        budget_max=merged.budget_max,
        budget_strict=merged.budget_strict,
        wants=merged.wants,
        suggested_item_ids=list(
            dict.fromkeys([*replied_item_ids, *state.suggested_item_ids])
        )[:MAX_SUGGESTED_MEMORY],
        rejected_item_ids=list(state.rejected_item_ids),
        turn_count=state.turn_count + 1,
    )


# Nhãn đọc được cho người, dùng trong tóm tắt. Chỉ những nhãn thật sự xuất hiện trong tóm tắt.
_ALLERGEN_VI = {
    "allergen:seafood": "hải sản",
    "allergen:peanut": "đậu phộng",
    "allergen:egg": "trứng",
    "allergen:dairy": "sữa",
    "allergen:gluten": "gluten",
}
_HARD_VI = {
    "spice:none": "không cay",
    "spice:mild": "cay nhẹ",
    "spice:medium": "cay vừa",
    "spice:hot": "cay đậm",
    "party:solo": "ăn một mình",
    "party:two_three": "nhóm 2–3 người",
    "party:three_five": "nhóm 3–5 người",
}


def rolling_summary(state: SessionState) -> str:
    """Một câu tóm tắt phiên, sinh TẤT ĐỊNH từ chính bộ nhớ.

    Không gọi mô hình. Xem docstring đầu tệp: bộ nhớ sai thì sai suốt phiên, nên chỗ này không
    được có sinh tự do.

    Nhãn không có tên tiếng Việt thì in nguyên nhãn, không bỏ qua. Bỏ qua thì tóm tắt nói THIẾU
    so với bộ nhớ thật, và người đọc log sẽ tưởng ràng buộc đó không tồn tại.
    """
    parts: list[str] = []
    if state.avoid_tags:
        ten = ", ".join(_ALLERGEN_VI.get(t, t) for t in state.avoid_tags)
        parts.append(f"khách dị ứng {ten}")
    if state.wants == "food":
        parts.append("đang hỏi món ăn")
    elif state.wants == "drink":
        parts.append("đang hỏi đồ uống")
    for tag in state.hard_tags:
        parts.append(_HARD_VI.get(tag, tag))
    if state.budget_max is not None:
        moc = f"{state.budget_max:,}".replace(",", ".") + "đ"
        parts.append(f"ngân sách {'dưới' if state.budget_strict else 'tầm'} {moc}")
    if state.suggested_item_ids:
        parts.append(f"đã xem {len(state.suggested_item_ids)} món")

    if not parts:
        return f"Phiên mới, chưa có ràng buộc nào ({state.turn_count} lượt)."

    # Chỉ viết hoa CHỮ ĐẦU. Không dùng `.capitalize()` — nó viết hoa chữ đầu *và viết thường tất
    # cả phần còn lại*, nên `season:summer` thành `Season:summer` và tên riêng bị phá. Test
    # `test_nhan_khong_co_ten_tieng_viet_van_hien_nguyen_nhan` bắt đúng lỗi này.
    cau = "; ".join(parts)
    return f"{cau[0].upper()}{cau[1:]}."


def session_updates(state: SessionState, replied_item_ids: list[str]) -> dict[str, Any]:
    """Phần `session_updates` trả cho backend, đúng tên trường backend đang đọc.

    Cố ý KHÔNG trả `accepted_menu_item_ids` và `added_to_cart_menu_item_ids`. Backend đã bỏ qua
    hai trường đó (`ApplyAiSessionUpdates` ghi rõ chúng thuộc backend), nên không gửi thì ranh
    giới quyền rõ hơn là gửi rồi bị bỏ: AI **đề xuất**, khách **xác nhận**, backend **quyết**.
    """
    return {
        "facts": [],
        "constraints": {
            "avoid_tags": list(state.avoid_tags),
            "hard_tags": list(state.hard_tags),
            "context_tags": list(state.context_tags),
            "budget_max": state.budget_max,
            "wants": state.wants,
        },
        "referenced_menu_item_ids": list(replied_item_ids),
        "suggested_menu_item_ids": list(state.suggested_item_ids),
        "rejected_menu_item_ids": list(state.rejected_item_ids),
        "rolling_summary": rolling_summary(state),
        "memory_version": MEMORY_VERSION,
    }
