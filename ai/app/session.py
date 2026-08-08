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

# Số món của MỘT danh sách giữ lại để trỏ vào. `answer.LIST_SIZE` là 6, nên 6 là đủ và nhiều hơn
# là giữ món khách không đọc thấy. Khách nói "cái thứ ba" về danh sách vừa đọc, không về lượt trước.
MAX_LISTED_MEMORY = 6

# Nhóm nhãn được coi là RÀNG BUỘC CỨNG — lượt mới ghi đè cùng nhóm.
#
# Cả bốn nhóm này phủ 91/91 món, và đó không phải trùng hợp: chỉ nhóm phủ hết mới lọc dứt khoát
# được, nên chỉ chúng mới xứng là ràng buộc cứng. Nhóm phủ một phần (occasion 79/91, flavour
# 72/91...) thuộc NGỮ CẢNH, vì thiếu nhãn ở đó nghĩa là *chưa ghi nhận*, không phải *không phù
# hợp*.
HARD_CONSTRAINT_GROUPS = ("spice", "price", "party", "season", "diet")

# `diet` thêm vào sau khi golden 103 lượt bắt được: khách nói "Mình ăn chay nữa" ở lượt 3, và lượt 4
# nhận về Bánh mì pate, Cháo lòng, Xôi gà — ba món không chay. Chế độ ăn bị QUÊN ngay lượt sau.
#
# Vì sao nó thuộc nhóm cứng dù chỉ phủ 17/91 món, trong khi bốn nhóm kia phủ 91/91: tiêu chí không
# phải độ phủ mà là "khách nêu điều này là nêu điều BẮT BUỘC". Ăn chay không phải sở thích để sắp
# thứ tự — món không chay là món khách không ăn. Cùng lý do `llm_understand.HARD_GROUPS` đã xếp
# `diet` vào nhóm cứng từ trước; chỗ này bỏ sót và hai tệp lệch nhau.

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
    # Món của lượt gần nhất, THEO ĐÚNG THỨ TỰ đã nêu ra cho khách. Khác `suggested_item_ids` ở
    # hai điểm, và cả hai đều cần thiết:
    #
    #   suggested_item_ids   TẬP tích lũy cả phiên, dùng để KHÔNG gợi lại. Thứ tự vô nghĩa.
    #   last_listed_ids      DÃY của MỘT lượt, dùng để trỏ vào: "món đầu tiên", "cái thứ ba".
    #
    # Gộp hai thứ này là lý do tham chiếu ngược không làm được: "món đầu tiên" trong một tập tích
    # lũy 24 món qua 6 lượt thì không trỏ vào đâu cả. Khách nói "món đầu tiên" là nói về danh sách
    # họ VỪA đọc, nên nó phải bị THAY mỗi lượt có danh sách, không phải cộng dồn.
    last_listed_ids: list[str] = field(default_factory=list)
    # Món ĐANG NÓI TỚI. Khác `last_listed_ids` ở chỗ nó là MỘT món, và nó chỉ đổi khi câu trả lời
    # nói về đúng một món — nên nó sống qua những lượt liệt kê danh sách.
    #
    # Có mặt vì "món thứ hai có cay không?" rồi "món đó bao nhiêu tiền?" từng trả lời về món THỨ
    # NHẤT: cụm "món đó" bị gán vị trí 1 trong từ vựng. Vị trí là cách trỏ khi khách ĐẾM; "món đó"
    # thì không đếm, nó trỏ vào tiêu điểm của cuộc nói.
    last_focus_id: str | None = None
    # Cặp món của câu so sánh gần nhất, để câu "món nào cay hơn?" không mất ngữ cảnh.
    last_compared_ids: list[str] = field(default_factory=list)
    # Danh mục của lượt gần nhất. `categories` KHÔNG nằm trong `hard_tags` vì nó không phải nhãn,
    # và không cộng dồn được: "cho mình món chay" rồi "cho mình món lẩu" là hai yêu cầu khác nhau,
    # không phải giao của hai danh mục.
    #
    # Nó tồn tại vì câu "còn món nào giống vậy không?": không nhớ danh mục thì "giống vậy" không
    # có gì để giống, và hệ thống liệt kê lại cả thực đơn — đúng điều đã đo được ở
    # `context-reference-08`.
    last_categories: list[str] = field(default_factory=list)
    # Hệ thống VỪA HỎI gì. Rỗng nghĩa là lượt trước không hỏi câu có/không nào.
    #
    # Có vì một lỗi đo được trên production: hệ thống hỏi *"Bạn muốn mình bỏ bớt một điều kiện để có
    # thêm lựa chọn không?"* rồi KHÔNG hiểu câu trả lời — khách nói "bỏ và tư vấn thêm đi" và nhận
    # lại đúng câu hỏi đó, lặp mãi. Tệ hơn: chữ "bỏ" rút dấu thành `bo`, mà `bo` là nhãn
    # `ingredient:beef`, nên khách xin BỎ điều kiện lại bị THÊM ràng buộc thịt bò.
    #
    # Vá bằng cách thêm cụm là đánh chuột: mỗi cách nói "đồng ý" trong tiếng Việt là một cụm mới.
    # Nhớ CÂU MÌNH VỪA HỎI thì chỉ cần một cơ chế, và nó đúng cho mọi cách nói ngắn.
    cho_doi: str = ""
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

        # Backend .NET gửi bộ nhớ theo hình dạng CỦA NÓ (`ChatSessionStatePayload`): ràng buộc
        # nằm trong `constraints`, còn món đã gợi ý nằm ở `suggested_menu_item_ids`. Dịch vụ dùng
        # hình dạng phẳng. Nhận CẢ HAI, vì:
        #
        #   - hình dạng backend  -> khi backend gọi thật
        #   - hình dạng phẳng    -> khi test và công cụ nội bộ gọi trực tiếp
        #
        # Chỗ này từng là lỗi IM LẶNG nguy hiểm nhất của phần tích hợp: bộ nhớ khoan dung với
        # khóa lạ nên nó không báo lỗi, nó trả về phiên RỖNG. Tức dị ứng khai ở lượt 1 mất ở lượt
        # 2, và câu ở lượt 2 nhìn hoàn toàn vô hại. 422 thì thấy ngay; mất bộ nhớ thì không.
        if isinstance(payload.get("constraints"), dict):
            rang_buoc = dict(payload["constraints"])
            payload = {
                **rang_buoc,
                "suggested_item_ids": payload.get("suggested_menu_item_ids")
                or rang_buoc.get("suggested_item_ids") or [],
                "rejected_item_ids": payload.get("rejected_menu_item_ids")
                or rang_buoc.get("rejected_item_ids") or [],
                # Đi vòng tròn qua `constraints` được, vì backend copy MỌI khóa của dict đó vào
                # `constraints_json` rồi trả lại nguyên vẹn. Xem `session_updates()`.
                "last_listed_ids": rang_buoc.get("last_listed_ids") or [],
                "last_categories": rang_buoc.get("last_categories") or [],
                "turn_count": rang_buoc.get("turn_count", 0),
            }

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
            last_listed_ids=ids("last_listed_ids")[:MAX_LISTED_MEMORY],
            last_categories=ids("last_categories"),
            cho_doi=(payload.get("cho_doi")
                     if isinstance(payload.get("cho_doi"), str) else ""),
            last_focus_id=(payload.get("last_focus_id")
                           if isinstance(payload.get("last_focus_id"), str) else None),
            last_compared_ids=ids("last_compared_ids")[:2],
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
            "last_focus_id": self.last_focus_id,
            "last_compared_ids": list(self.last_compared_ids),
            "suggested_item_ids": list(self.suggested_item_ids),
            "rejected_item_ids": list(self.rejected_item_ids),
            "last_listed_ids": list(self.last_listed_ids),
            "last_categories": list(self.last_categories),
            "cho_doi": self.cho_doi,
            "turn_count": self.turn_count,
        }


def _group(tag: str) -> str:
    return tag.split(":", 1)[0]


def merge_into_request(request: Request, state: SessionState) -> Request:
    """Áp bộ nhớ phiên vào yêu cầu của lượt hiện tại, theo ba quy tắc khác nhau.

    Trả về một `Request` MỚI thay vì sửa tại chỗ, để chỗ gọi còn giữ được yêu cầu gốc của lượt
    này — cần nó để biết lượt này khách nói gì mới, tách khỏi cái đã nhớ từ trước.
    """
    # QUY TẮC 0 — KHÁCH BẢO BỎ. Đường duy nhất hạ được hàng rào ở quy tắc 1.
    #
    # "Không bao giờ bỏ" khác "không có đường bỏ", và dự án đã lẫn hai thứ đó. Đo được trên
    # production: khách khai dị ứng hải sản, rồi nói "tôi không còn dị ứng nữa" — mô hình ĐỌC ĐÚNG
    # (`decision.model.reason` = "mô hình đọc được ràng buộc") mà câu trả lời vẫn lọc, vì dòng ngay
    # dưới lấy HỢP hai tập. Rồi "vậy gợi ý món hải sản đi" nhận `no_data`: khách bị kẹt trong một
    # ràng buộc không có cách nào gỡ.
    #
    # Ba điều kiện giữ cho việc này KHÔNG làm yếu chốt an toàn:
    #
    #   1. chỉ bỏ khi khách nói RÕ RÀNG   `intent._XOA_DI_NGUYEN` là danh sách cụm, không suy diễn
    #   2. chỉ bỏ thứ ĐANG CÓ             không bao giờ bỏ nhãn của chính lượt này
    #   3. câu trả lời phải NÊU RA        `da_bo_rang_buoc` -> `answer` nói ra, khách sửa được
    #
    # Điều 3 là điều phân biệt việc này với "im lặng bỏ ràng buộc": một hàng rào an toàn được hạ
    # xuống thì khách phải THẤY nó được hạ.
    from intent import XOA_RANG_BUOC, la_dong_y

    # Khách ĐỒNG Ý với đề nghị hệ thống vừa đưa ra.
    #
    # Hệ thống hỏi "Bạn muốn mình bỏ bớt một điều kiện để có thêm lựa chọn không?" rồi trước đây
    # KHÔNG hiểu câu trả lời — khách nói "bỏ và tư vấn thêm đi" và nhận lại đúng câu hỏi đó, lặp mãi.
    #
    # Nới ở đây là nới BỘ LỌC (`loc`), tuyệt đối không phải `all`: khách đồng ý xem thêm lựa chọn
    # KHÔNG có nghĩa là họ hết dị ứng. Đây là chỗ một cơ chế tiện lợi dễ hạ mất chốt an toàn nhất.
    if state.cho_doi == "bo_bot_dieu_kien" and la_dong_y(request.text):
        # `wants_similar=True` để GIỮ CHỦ ĐỀ qua câu đồng ý.
        #
        # "ừ bỏ đi" tự nó không mang danh mục nào, nên nếu không kéo `last_categories` thì lượt sau
        # rơi về toàn thực đơn. Đo được, và hỏng theo cách tệ nhất có thể:
        #
        #     "chuyển sang món chay đi"  -> 0 món, mời bỏ điều kiện 2-3 người
        #     "ừ bỏ đi"                  -> 6 món KHÔNG chay
        #
        # Khách xin món chay, đồng ý bỏ một điều kiện, và nhận về thịt. Bỏ điều kiện phải bỏ ĐÚNG
        # điều kiện được hỏi, không được cuốn theo cả chủ đề khách vừa nêu.
        request = replace(request, y_dinh=XOA_RANG_BUOC, y_dinh_bo=["loc"], wants_similar=True)

    da_bo: list[str] = []
    ke_thua_avoid = list(state.avoid_tags)
    ke_thua_hard = list(state.hard_tags)
    ke_thua_budget = state.budget_max
    if request.y_dinh == XOA_RANG_BUOC:
        if "allergen" in request.y_dinh_bo or "all" in request.y_dinh_bo:
            da_bo.extend(ke_thua_avoid)
            ke_thua_avoid = []
        # `loc` bỏ ràng buộc LỌC (số người, độ cay, giá, chế độ ăn) nhưng GIỮ dị nguyên.
        # `all` bỏ cả hai. Tách hai nhóm chính vì điều đó — xem `intent._NOI_BO_LOC`.
        if "all" in request.y_dinh_bo or "loc" in request.y_dinh_bo:
            da_bo.extend(ke_thua_hard)
            ke_thua_hard = []
            ke_thua_budget = None
        else:
            # BỎ ĐÚNG MỘT NHÓM. Dùng cho khung phủ nhận ("tôi đâu có nói là không ăn được cay"):
            # khách phủ nhận độ cay thì bỏ độ cay, không bỏ luôn số người và ngân sách họ đã nêu.
            #
            # `loc` là bỏ TẤT CẢ ràng buộc lọc, đúng cho câu "bỏ bớt điều kiện đi" vì lúc đó khách
            # không chỉ định nhóm nào. Ở đây khách chỉ định rất rõ, nên bỏ rộng hơn điều họ nói là
            # tự ý gỡ thêm hàng rào — đúng thứ mà cả cơ chế này được viết ra để tránh.
            nhom_bo = {n for n in request.y_dinh_bo if n not in ("allergen", "loc", "all")}
            if nhom_bo:
                da_bo.extend([t for t in ke_thua_hard if _group(t) in nhom_bo])
                ke_thua_hard = [t for t in ke_thua_hard if _group(t) not in nhom_bo]

    # QUY TẮC 1 — dị nguyên: CỘNG DỒN, không bao giờ bỏ. Đây là chốt an toàn của khâu này.
    avoid = list(dict.fromkeys([*ke_thua_avoid, *request.avoid_tags]))

    # QUY TẮC 2 — ràng buộc cứng: lượt mới GHI ĐÈ cùng NHÓM.
    #
    # Ghi đè theo nhóm chứ không theo nhãn: `spice:none` phải đẩy `spice:hot` ra khỏi bộ nhớ,
    # không phải nằm cạnh nó. Nằm cạnh thì phép lọc AND cho kết quả rỗng và khách nhận "không
    # có món nào" cho một yêu cầu hoàn toàn hợp lệ.
    new_groups = {_group(t) for t in request.require_tags}
    carried_hard = [t for t in ke_thua_hard if _group(t) not in new_groups]
    require = list(dict.fromkeys([*carried_hard, *request.require_tags]))

    # Ngân sách cũng là ràng buộc cứng: lượt mới có nêu thì thay, không nêu thì giữ.
    if request.budget_max is not None:
        budget_max, budget_strict = request.budget_max, request.budget_strict
    else:
        budget_max, budget_strict = ke_thua_budget, state.budget_strict

    # QUY TẮC 3 — ngữ cảnh: cộng vào, giữ MAX_CONTEXT_TAGS gần nhất.
    #
    # Nhãn của lượt này đứng TRƯỚC, nên khi phải cắt thì cắt cái cũ nhất. Sở thích khách vừa nêu
    # đáng tin hơn sở thích ba lượt trước.
    prefer = list(dict.fromkeys([*request.prefer_tags, *state.context_tags]))[:MAX_CONTEXT_TAGS]

    # `wants` (món ăn / đồ uống) là ràng buộc cứng nhưng không mang dạng nhãn, nên xử riêng.
    # CHỈ kế thừa `wants` khi lượt này KHÔNG nêu chủ đề nào.
    #
    # Đo được trong một hội thoại đổi chủ đề liên tục:
    #
    #     "cho mình món lẩu"        -> 6 món lẩu
    #     "uống gì hợp với lẩu"     -> 6 đồ uống          (đúng, `wants=drink`)
    #     "tráng miệng có gì"       -> 6 ĐỒ UỐNG y nguyên  <- SAI
    #
    # `understand()` đọc đúng `cat_dessert` cho lượt ba, nhưng `wants=drink` kéo từ lượt hai đè lên
    # nó: Tráng miệng không thuộc `FOOD_CATEGORIES` lẫn `DRINK_CATEGORIES`, nên phép lọc theo loại
    # gạt nó đi rồi trả về đồ uống của lượt trước.
    #
    # Khách gọi tên một nhóm món là họ đã nói rõ mình muốn gì. Kế thừa `wants` chỉ có nghĩa cho câu
    # KHÔNG nói gì ("còn nữa không") — đúng chỗ nó sinh ra để phục vụ.
    if request.wants != "any":
        wants = request.wants
    elif request.categories or request.ho_mon:
        wants = "any"
    else:
        wants = state.wants

    # XIN THÊM = XIN MÓN GIỐNG. Dùng lại đúng cơ chế `wants_similar` đã có và đã đo, thay vì dựng
    # đường loại trừ thứ hai — hai đường sẽ lệch nhau.
    #
    # Đây là lỗi số 1 người dùng nêu: "tư vấn thêm đi" trả lại y nguyên 6 món của lượt trước, vì từ
    # vựng chỉ nhận `mon khac|cai khac|thu khac` mà không nhận "thêm", "còn gì nữa".
    from intent import XIN_THEM

    xin_them = request.y_dinh == XIN_THEM
    if xin_them:
        request = replace(request, wants_similar=True)

    # BỎ MỘT RÀNG BUỘC KHÔNG ĐƯỢC LÀM MẤT CHỦ ĐỀ ĐANG XEM.
    #
    # Đo được trong hội thoại khách tự sửa lời khai:
    #
    #     "giờ cho mình món hải sản"      -> 6 món hải sản
    #     "mình dị ứng tôm nhé"           -> đổi sang món không hải sản
    #     "à mình đâu có dị ứng tôm"      -> lặp Y NGUYÊN danh sách không hải sản  <- SAI
    #
    # Khách gỡ đúng hàng rào đang che mất thứ họ muốn xem, rồi vẫn không thấy nó. Câu "à mình đâu
    # có dị ứng tôm" tự nó không mang danh mục nào, nên không có gì kéo `cat_seafood` trở lại.
    #
    # Kéo lại DANH MỤC, nhưng KHÔNG bật `wants_similar`.
    #
    # `wants_similar` làm hai việc cùng lúc: khôi phục chủ đề VÀ loại những món đã nêu. Ở đây chỉ
    # cần việc thứ nhất. Bật cả hai thì đo được kết quả này:
    #
    #     "à mình đâu có dị ứng tôm"  ->  1 món (Tôm hùm nướng mỡ hành 890.000đ)
    #
    # Khách gỡ hàng rào là để THẤY LẠI những món bị che, không phải để xem đúng một món sót lại.
    # Đây là chỗ tái dùng một cơ chế sẵn có sẽ mang theo cả phần không muốn — nên tách ra.
    if da_bo and not request.categories:
        request = replace(request, categories=list(state.last_categories))

    # Danh mục chỉ được kéo lại khi khách xin món GIỐNG. Kéo lại mọi lượt là sai: "cho mình món
    # chay" rồi "cho mình đồ uống" thì lượt sau không được vẫn bị giới hạn trong danh mục chay.
    categories = list(request.categories)
    if request.wants_similar and not categories:
        categories = list(state.last_categories)

    # QUY TẮC 4 — THAM CHIẾU NGƯỢC. Giải ở đây, không giải trong `answer.py`.
    #
    # Đây là chỗ đúng vì tham chiếu ngược là câu hỏi về BỘ NHỚ, không phải về thực đơn: "món đầu
    # tiên" chỉ có nghĩa khi biết khách vừa đọc danh sách nào. Giải nó thành `named_items` làm
    # `answer.respond()` xử lý nó bằng đúng các nhánh đã có và đã đo (`price_lookup`,
    # `item_detail`, `allergen_named_dish`) — không thêm nhánh thứ bảy, nên không phải đo lại sáu
    # nhánh cũ.
    named = list(request.named_items)
    if request.reference_index is not None and state.last_listed_ids and not named:
        i = request.reference_index
        # -1 = món cuối. Chỉ số ngoài phạm vi thì BỎ QUA thay vì kẹp về đầu/cuối: khách nói "món
        # thứ năm" cho một danh sách 3 món là khách nhớ sai, và trả về món thứ 3 như thể đó là món
        # thứ 5 là xác nhận một điều sai. Bỏ qua thì câu đi tiếp và hệ thống hỏi lại.
        if i == -1:
            named = [state.last_listed_ids[-1]]
        elif 1 <= i <= len(state.last_listed_ids):
            named = [state.last_listed_ids[i - 1]]

    # "Món đó" / "cái đó" / "món vừa rồi": trỏ vào TIÊU ĐIỂM, không vào vị trí.
    #
    # Lùi về món thứ nhất của danh sách khi chưa có tiêu điểm — đúng hành vi cũ ở lượt đầu, nên
    # không ca nào tụt. Chuỗi "món thứ hai có cay không?" rồi "món đó bao nhiêu tiền?" nay trả lời
    # về món thứ hai, vì lượt trước đã đặt tiêu điểm vào đó.
    mo_ho = False
    if request.refers_to_focus and not named:
        if state.last_focus_id:
            named = [state.last_focus_id]
        elif len(state.last_listed_ids) >= 2 and request.la_xin_mon:
            # XIN MÓN + tham chiếu mơ hồ + chưa có tiêu điểm -> HỎI LẠI, không đoán.
            #
            # Nhánh `elif` dưới lùi về món THỨ NHẤT của danh sách, và với câu HỎI thì đó là hành vi
            # đúng đã chốt: đoán nhưng nêu tên món đã đoán, để khách sửa được ngay. 12 lượt đánh
            # giá dựa vào nó ("Món đó bao nhiêu tiền?", "Cái đó có cay không?"), và hỏi lại ở
            # những câu đó là bước lùi — khách hỏi một câu đơn giản.
            #
            # Câu XIN MÓN thì khác: "cho mình món vừa rồi" với bốn món trên màn hình là **ý định
            # lấy một món cụ thể**, và đoán ở đây nghĩa là chọn hộ khách. Phân loại bằng đúng bộ
            # dấu hiệu `XIN_MON_RE` đã có — đo trên 13 lượt đang dùng tiêu điểm thì nó tách sạch
            # 12 câu hỏi khỏi 1 câu xin, không cần luật mới.
            #
            # Đòi >= 2 món: danh sách một món thì không có gì mơ hồ để hỏi.
            mo_ho = True
        elif state.last_listed_ids:
            named = [state.last_listed_ids[0]]

    # Câu so sánh TIẾP NỐI: lấy lại cặp món của câu so sánh gần nhất.
    #
    # Chỉ khi lượt này KHÔNG nhắc tên món nào — khách nhắc tên thì tên đó thắng. Và chỉ khi cặp cũ
    # đủ hai món, vì nhánh so sánh cần đúng hai.
    #
    # Nhận CẢ `is_comparison` (cụm sẵn có: "khác nhau thế nào", "nên chọn", "so với") lẫn
    # `asks_comparison` (cụm mới: "cay hơn", "ngon hơn"). Hai cụm khác nhau nhưng cùng một nhu cầu:
    # khách đang so hai món mà không nhắc lại tên. Để `is_comparison` ngoài luật này thì câu "hai
    # món đó khác nhau thế nào?" vẫn rơi vào nhánh hỏi lại.
    if ((request.asks_comparison or request.is_comparison)
            and not named and len(state.last_compared_ids) == 2):
        named = list(state.last_compared_ids)

    return replace(
        request,
        da_bo_rang_buoc=da_bo,
        # Ràng buộc kéo từ bộ nhớ, KHÔNG do câu lượt này nêu. Tính ở đây vì đây là chỗ duy nhất
        # biết được cả hai nguồn.
        rang_buoc_ke_thua=[
            *[t for t in carried_hard if t not in request.require_tags],
            # Ngân sách kế thừa dùng chung danh sách này bằng một mã canh, để không phải thêm
            # trường thứ hai cho cùng một câu hỏi "thứ này do lượt nào nêu".
            *(["__ngan_sach__"] if (request.budget_max is None and ke_thua_budget is not None)
              else []),
        ],
        avoid_tags=avoid,
        require_tags=require,
        prefer_tags=prefer,
        categories=categories,
        budget_max=budget_max,
        budget_strict=budget_strict,
        wants=wants,
        named_items=named,
        mo_ho_tieu_diem=mo_ho,
        # Hai cơ chế còn lại của tham chiếu ngược đi qua HAI tập món, không qua nhãn:
        #
        #   scope_item_ids    "món rẻ nhất TRONG SỐ ĐÓ" -> chỉ xét danh sách vừa nêu
        #   exclude_item_ids  "còn món nào GIỐNG VẬY"   -> giữ ràng buộc, bỏ món đã nêu
        #
        # Đặt ở đây chứ không ở `answer.py` vì cả hai chỉ có nghĩa khi biết bộ nhớ phiên. `answer`
        # nhận chúng như một tập id và không cần biết chúng từ đâu ra.
        scope_item_ids=(
            # Khi tham chiếu MƠ HỒ, phạm vi chính là danh sách đang gây mơ hồ — `answer` cần đúng
            # tập đó để liệt kê ứng viên kèm số thứ tự trong câu hỏi lại.
            list(state.last_listed_ids)
            if (request.scope_last_listed or mo_ho) and state.last_listed_ids
            else []
        ),
        # Loại CẢ tập đã gợi trong phiên, không chỉ lượt cuối.
        #
        # Đo được: sau ba lượt danh sách, "món khác đi" mà chỉ loại lượt cuối vẫn có thể trả về món
        # của lượt 1 — và với khách thì đó vẫn là "món cũ". `suggested_item_ids` bị chặn ở
        # MAX_SUGGESTED_MEMORY nên tập này không phình vô hạn.
        exclude_item_ids=(
            list(dict.fromkeys([*state.last_listed_ids, *state.suggested_item_ids]))
            if request.wants_similar else []
        ),
    )


def update_state(
    state: SessionState,
    merged: Request,
    replied_item_ids: list[str],
    reply_kind: str,
    reply_branch: str = "",
) -> SessionState:
    """Ghi bộ nhớ sau khi đã trả lời. Nhận `Request` ĐÃ hợp nhất, không phải bản gốc.

    Nhận bản đã hợp nhất là điểm quan trọng: nếu ghi từ bản gốc thì dị nguyên khai ở lượt 1 sẽ
    không có trong bản gốc của lượt 2, và bộ nhớ **mất nó ngay lượt sau** — đúng lỗi mà cả khâu
    này tồn tại để chống.

    `reply_kind` là tham số BẮT BUỘC, không có giá trị mặc định. Nó quyết định `last_listed_ids`
    có bị thay hay không, và đặt mặc định cho nó sẽ che đúng lỗi mà nó tồn tại để sửa — xem bên
    dưới. Thà sửa ba chỗ gọi còn hơn để một mặc định quyết định thay.
    """
    return SessionState(
        # Dị nguyên vào bộ nhớ CHỈ khi lượt này KHAI điều cần tránh. Nhãn đã có trong bộ nhớ thì
        # giữ nguyên vô điều kiện — chốt an toàn không đổi: đã khai một lần là giữ suốt phiên.
        #
        # Điều ĐỔI là chiều còn lại: một câu HỎI ("món này có hải sản không?") cũng sinh
        # `avoid_tags` để trả lời được, nhưng nó KHÔNG được biến thành lời khai. Trước bản này, một
        # câu hỏi tò mò làm 26/91 món bị ẩn suốt phiên và mọi câu sau đó mở đầu bằng "thực đơn không
        # ghi nhận thành phần bạn cần tránh" — khẳng định một điều khách chưa nói.
        #
        # Vì sao đây KHÔNG phải nới ràng buộc an toàn: nới là bỏ một điều khách ĐÃ khai. Ở đây
        # không có lời khai nào để bỏ — có một câu hỏi, và nó đã được trả lời đầy đủ.
        # Khách bảo BỎ thì bộ nhớ phải ghi lại việc bỏ.
        #
        # Dòng này từng lấy `state.avoid_tags` — bộ nhớ TRƯỚC lượt này — nên nó **ghi lại đúng cái
        # `merge_into_request` vừa xóa**. Kết quả đo được: câu trả lời của lượt xóa nói "đã bỏ điều
        # kiện hải sản", rồi lượt kế tiếp "vậy gợi ý món hải sản đi" nhận `no_data` vì ràng buộc đã
        # sống lại. Bất biến hai đầu lần thứ mười, và lần này hai đầu nằm trong CÙNG MỘT TỆP.
        #
        # Cách sửa ĐÚNG là trừ đi đúng phần đã bỏ, KHÔNG phải đọc `merged.avoid_tags` thay cho
        # `state.avoid_tags`. Bản đầu của tôi làm thế và mất ngay một bất biến khác: `merged` mang
        # dị nguyên cả khi khách chỉ HỎI ("món này có hải sản không?"), nên câu hỏi bị biến thành
        # lời khai — 4 lượt kịch bản đỏ, và test `KhongBienCauHoiThanhLoiKhai` bắt đúng chỗ đó.
        avoid_tags=list(dict.fromkeys([
            *[t for t in state.avoid_tags if t not in merged.da_bo_rang_buoc],
            *([t for t in merged.avoid_tags if t.startswith(ALLERGEN_PREFIX)]
              if merged.declared_avoidance else []),
        ])),
        hard_tags=[t for t in merged.require_tags if _group(t) in HARD_CONSTRAINT_GROUPS],
        context_tags=list(merged.prefer_tags)[:MAX_CONTEXT_TAGS],
        budget_max=merged.budget_max,
        budget_strict=merged.budget_strict,
        wants=merged.wants,
        suggested_item_ids=list(
            dict.fromkeys([*replied_item_ids, *state.suggested_item_ids])
        )[:MAX_SUGGESTED_MEMORY],
        rejected_item_ids=list(state.rejected_item_ids),
        # THAY chỉ khi lượt này NÊU MỘT DANH SÁCH. Giữ nguyên ở mọi dạng đáp án khác.
        #
        # Điều kiện là `reply_kind == "list"`, KHÔNG phải `replied_item_ids` khác rỗng. Khác biệt
        # đó là một lỗi thật, và nó chỉ hiện ra khi chạy qua backend thật chứ không hiện trong tập
        # kịch bản:
        #
        #   lượt 1  "cho mình món chay"            -> list 6 món     -> dãy = 6 món
        #   lượt 2  "món đầu tiên giá bao nhiêu?"  -> fact, 1 món     -> dãy CÒN 1 MÓN
        #   lượt 3  "món thứ hai có hải sản không?" -> "thứ hai" ngoài phạm vi -> KHÔNG trỏ được
        #
        # Khách ở lượt 3 vẫn đang nói về danh sách của lượt 1 — họ không coi câu trả lời về một món
        # là một danh sách mới. Nên một câu `fact` về một món KHÔNG được phá dãy mà khách còn đang
        # trỏ vào.
        #
        # Tập 25 kịch bản không bắt được vì mọi kịch bản `context_reference` chỉ có MỘT lượt tham
        # chiếu. Đây đúng là lý do "chạy thật" không thay được bằng test: test kiểm điều tôi nghĩ
        # ra để kiểm, còn một cuộc hội thoại thật có những chuỗi tôi không nghĩ tới.
        last_listed_ids=(
            list(replied_item_ids)[:MAX_LISTED_MEMORY]
            if (reply_kind == "list" and replied_item_ids) else list(state.last_listed_ids)
        ),
        last_categories=(
            list(merged.categories) if merged.categories else list(state.last_categories)
        ),
        # TIÊU ĐIỂM: đổi chỉ khi câu trả lời nói về ĐÚNG MỘT món. Giữ nguyên ở lượt danh sách.
        #
        # Điều kiện là "đúng một món", không phải `reply_kind == "fact"`: một câu `fact` có thể là
        # câu tri thức không món nào, và lúc đó tiêu điểm cũ vẫn là món khách đang nói tới.
        last_focus_id=(
            replied_item_ids[0] if len(replied_item_ids) == 1 else state.last_focus_id
        ),
        # CẶP SO SÁNH: chỉ đổi khi lượt này thật sự là một câu so sánh hai món. Giữ nguyên ở mọi
        # dạng khác, để "món nào cay hơn?" vẫn trỏ được sau một lượt xen giữa.
        last_compared_ids=(
            list(replied_item_ids)
            if (reply_kind == "compare" and len(replied_item_ids) == 2)
            else list(state.last_compared_ids)
        ),
        # Hệ thống VỪA HỎI gì — để lượt sau hiểu được câu trả lời.
        #
        # Chỉ ghi cho nhánh `exhausted_after_exclusions`, vì đó là nhánh DUY NHẤT đặt một câu có/không
        # mà câu trả lời làm hệ thống phải hành động khác đi. Các nhánh `clarify` khác hỏi câu MỞ
        # ("bạn muốn món ăn hay đồ uống?") và câu trả lời của chúng tự mang ràng buộc.
        # `empty_result_offer_drop` cũng đặt một câu CÓ/KHÔNG ("bỏ điều kiện 2-3 người không?"),
        # nên nó phải ghi cùng cờ. Thiếu dòng này thì hệ thống hỏi rồi không hiểu câu trả lời của
        # chính nó — đúng lớp lỗi mà cờ `cho_doi` được viết ra để chấm dứt.
        cho_doi=("bo_bot_dieu_kien"
                 if reply_branch in ("exhausted_after_exclusions", "empty_result_offer_drop")
                 else ""),
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
        # `constraints` là chỗ DUY NHẤT bộ nhớ đi được vòng tròn qua backend, và nó đi được vì
        # backend copy MỌI khóa của dict này vào `constraints_json` rồi trả lại nguyên vẹn
        # (`ChatAiProvider.ExtractSessionUpdates` dòng 740–742, đọc lại ở dòng 447). Nên thêm khóa
        # ở đây là đủ — KHÔNG cần đổi hợp đồng backend, không cần migration.
        #
        # `last_listed_ids` và `last_categories` phải nằm ở đây, nếu không tham chiếu ngược chỉ
        # chạy trong test và MẤT trong hệ thống thật: mỗi lượt qua backend sẽ trả về một
        # `SessionState` không có dãy món, và "món đầu tiên" lại không trỏ vào đâu. Đó đúng là
        # loại lỗi im lặng mà cả khâu này tồn tại để chống — 422 thì thấy ngay, mất bộ nhớ thì
        # không.
        "constraints": {
            "avoid_tags": list(state.avoid_tags),
            "hard_tags": list(state.hard_tags),
            "context_tags": list(state.context_tags),
            "budget_max": state.budget_max,
            "wants": state.wants,
            "last_listed_ids": list(state.last_listed_ids),
            "last_categories": list(state.last_categories),
            # Câu hệ thống VỪA HỎI. Phải đi qua vòng backend, nếu không cơ chế "hiểu câu trả lời cho
            # câu mình vừa hỏi" chỉ chạy trong test và MẤT ở hệ thống thật — đúng lớp lỗi mà
            # `test_MOI_truong_bo_nho_deu_song_qua_vong_JSON` tồn tại để chặn, và nó đã bắt được
            # trường này ngay lần thêm đầu tiên.
            "cho_doi": state.cho_doi,
            # `last_focus_id` và `last_compared_ids` cũng phải nằm ở đây, và cùng một lý do — chỉ
            # có điều lần này lỗi đã xảy ra TRƯỚC khi tôi kịp nhớ ra: hai trường được thêm vào
            # `SessionState`, chạy đúng trong tiến trình, và **sai qua backend**. Golden đầu-cuối
            # bắt được ("Món đó bao nhiêu tiền?" trỏ sai món, "Món nào cay hơn?" mất cặp món), còn
            # 87 lượt phiên vẫn xanh vì chúng chạy trong tiến trình.
            #
            # Đây là lần thứ hai đúng lớp lỗi này trong cùng một tệp. Quy tắc: THÊM TRƯỜNG VÀO
            # `SessionState` LÀ PHẢI THÊM KHÓA Ở ĐÂY — có test bất biến bên dưới ép điều đó.
            "last_focus_id": state.last_focus_id,
            "last_compared_ids": list(state.last_compared_ids),
        },
        "referenced_menu_item_ids": list(replied_item_ids),
        "suggested_menu_item_ids": list(state.suggested_item_ids),
        "rejected_menu_item_ids": list(state.rejected_item_ids),
        "rolling_summary": rolling_summary(state),
        "memory_version": MEMORY_VERSION,
    }
