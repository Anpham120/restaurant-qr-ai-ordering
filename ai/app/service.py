# -*- coding: utf-8 -*-
"""Dịch vụ HTTP — lớp vỏ mỏng quanh phần đã đo được.

Vì sao tệp này là LỚP VỎ, không phải một tầng nữa
--------------------------------------------------
Mọi con số của dự án (122/122 tất định, 122/122 có mô hình, 0 lỗi an toàn) đo trên `understand`
→ `session` → `answer`. Nếu `service.py` thêm bất kỳ quyết định nào về nội dung câu trả lời thì
những con số đó **không còn nói về thứ khách nhận được**.

Nên tệp này chỉ làm bốn việc, và không việc nào chạm vào nội dung:

    1. xác thực token
    2. đọc bộ nhớ phiên từ payload  ->  gọi ba hàm đã có  ->  ghi bộ nhớ ra payload
    3. dịch `Reply` sang đúng tên trường backend đang đọc
    4. không bao giờ để một lỗi nội bộ thành 500 cho khách

Có một test đòi đúng điều đó: 5 câu chạy qua HTTP phải cho **cùng `text` và cùng `items`** với
khi gọi `respond()` trực tiếp.

Vì sao hợp đồng khách hàng không đổi
------------------------------------
Backend .NET đọc JSON của AI **hoàn toàn bằng `TryGetProperty`**, nên mọi trường đều optional.
Dịch vụ này trả **tập trường nhỏ hơn** với **đúng tên cũ** — không phá hợp đồng, không sửa
`ChatContracts.cs`, không sửa frontend.

Cố ý KHÔNG trả `accepted_menu_item_ids` và `added_to_cart_menu_item_ids`: backend đã bỏ qua chúng
(`ApplyAiSessionUpdates` ghi rõ hai trường đó thuộc backend). Không gửi thì ranh giới quyền rõ hơn
là gửi rồi bị bỏ — **AI đề xuất, khách xác nhận, backend quyết.**

Vì sao lỗi nội bộ KHÔNG được thành 500
--------------------------------------
Khách đang ngồi ở bàn và vừa gõ một câu. Trả 500 là khách thấy màn hình lỗi; trả câu "mình chưa
có dữ liệu, bạn hỏi nhân viên giúp nhé" là khách vẫn được phục vụ. Dự án đã mắc đúng lỗi này một
lần theo hướng ngược: `urllib.request.Request(...)` nằm ngoài khối `try` nên thiếu cấu hình là
**sập**, trong khi tài liệu khẳng định nó thoái hóa êm.

Bài học đã ghi: **khẳng định về hành vi khi lỗi thì phải có test cho đúng đường lỗi đó.** Nên ở
đây có test tiêm lỗi vào `respond()` và đòi HTTP 200 kèm câu chuyển nhân viên.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request as HttpRequest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from answer import STAFF_NOTE, Reply, load_facts, respond
from cart import CartError, build_cart, cart_payload
from llm_understand import enrich, load_env
from rag.chunker import all_chunks, load_all
from session import MEMORY_VERSION, SessionState, merge_into_request, session_updates, update_state
from understand import understand

APP_DIR = Path(__file__).resolve().parent
MENU_PATH = APP_DIR.parents[1] / "backend" / "data" / "menu-dataset.json"
KNOWLEDGE_PATH = APP_DIR.parent / "knowledge"

SERVICE_VERSION = "rebuild-1"

# Câu trả lời khi có lỗi nội bộ. Cùng câu chữ với nhánh `no_data` của `answer.py`, để khách không
# phân biệt được "hệ thống lỗi" với "chưa có dữ liệu" — họ không cần phân biệt, và câu này giữ họ
# ở đúng đường tiếp theo là hỏi nhân viên.
FALLBACK_TEXT = f"Mình chưa có dữ liệu về việc này ạ. {STAFF_NOTE}"


class MenuCache:
    """Thực đơn nạp một lần, nạp lại khi admin sửa món.

    Là một lớp chứ không phải biến toàn cục để `/v1/cache/invalidate` có chỗ bám và test có chỗ
    thay. Nạp thất bại thì `items` rỗng — và `/ready` sẽ báo chưa sẵn sàng, thay vì dịch vụ nhận
    lưu lượng rồi trả lời sai.
    """

    def __init__(self) -> None:
        self.items: list[dict] = []
        # Bảng tra `cat_vegetarian` -> "Món chay", cho câu lý do của thẻ giỏ. Là BẢNG TRA TÊN,
        # không phải danh sách món, nên nó không mở lại đường lọc thứ hai.
        self.category_names: dict[str, str] = {}
        self.loaded_at: float | None = None
        self.error: str | None = None
        self.reload()

    def reload(self) -> None:
        try:
            data = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
            self.items = data["items"]
            self.category_names = {c["categoryId"]: c["name"] for c in data.get("categories", [])}
            self.loaded_at = time.time()
            self.error = None
        except (OSError, ValueError, KeyError) as exc:
            self.items = []
            self.category_names = {}
            self.error = f"{type(exc).__name__}: {exc}"


MENU = MenuCache()


def _knowledge_counts() -> tuple[int, int]:
    """(số tài liệu, số đoạn). Dùng cho `/ready`, và lỗi ở đây không được làm `/ready` sập."""
    try:
        docs = load_all(KNOWLEDGE_PATH)
        return len(docs), len(all_chunks(KNOWLEDGE_PATH))
    except Exception:  # noqa: BLE001 — `/ready` phải trả lời được cả khi kho tri thức hỏng
        return 0, 0


def require_token(
    x_internal_token: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Xác thực token nội bộ. Nhận HAI cách gửi, vì bên gọi thật dùng cách thứ hai.

        Authorization: Bearer <token>    backend .NET gửi thế này
                                         (`ChatAiProvider.TryAddInternalAuthorization`)
        X-Internal-Token: <token>        hợp đồng dịch vụ, dùng bởi test và công cụ nội bộ

    Bản đầu chỉ đọc `X-Internal-Token`, nên mọi lượt chat từ backend nhận **401** và khách thấy
    "Xin lỗi, hệ thống hơi chậm". Không test nào bắt được — mọi test đều tự gửi
    `X-Internal-Token`, tức chúng kiểm hợp đồng tôi TƯỞNG, không kiểm hợp đồng bên gọi DÙNG.

    Đây là lỗi tích hợp thứ ba cùng một lớp trong lần chạy thật này (`message` vs `question`, hình
    dạng `session_state`, và header token). Bài học chung: **hợp đồng do BÊN GỌI định, không do
    bên nhận định** — và cách duy nhất biết bên gọi gửi gì là đọc mã của nó hoặc chạy thật.

    Token trống trong môi trường thì TỪ CHỐI mọi yêu cầu (503), không cho qua. Cấu hình thiếu mà
    mở cửa là cách một dịch vụ nội bộ thành công khai mà không ai biết.
    """
    expected = os.environ.get("AI_INTERNAL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="AI_INTERNAL_TOKEN chưa được cấu hình")

    supplied = x_internal_token
    if supplied is None and authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            supplied = value.strip()

    if supplied != expected:
        raise HTTPException(status_code=401, detail="token không hợp lệ")


class ChatTurnIn(BaseModel):
    """Một lượt. Dịch vụ chỉ DÙNG ba thứ, nhưng phải NHẬN được hình dạng backend gửi.

    `ChatRequestV2Payload` của backend có 24 trường, trong đó `promotions`, `orders`,
    `catalog_version` hiện luôn rỗng. Dịch vụ **bỏ qua** phần không dùng thay vì từ chối, vì
    backend là bên gọi và hợp đồng gọi do bên gọi định — bắt backend đổi tên trường để khớp dịch
    vụ mới là phá hợp đồng khách hàng, đúng thứ bản dựng lại cam kết không làm.

    Trường câu hỏi nhận CẢ HAI tên:

        message     backend .NET gửi tên này (`ChatRequestV2Payload.Message`, snake_case)
        question    tên của hợp đồng dịch vụ, dùng bởi test và công cụ nội bộ

    Bản đầu chỉ nhận `question`, nên backend gọi thật bị **422** — và không test nào bắt được vì
    mọi test đều tự gửi `question`. Chỉ chạy thật mới thấy.
    """

    model_config = {"populate_by_name": True, "extra": "ignore"}

    # `alias="message"` để backend gửi `message` là khớp; `question` vẫn dùng được nhờ
    # `populate_by_name`.
    question: str = Field(min_length=1, max_length=2000, alias="message")
    session_state: dict[str, Any] | None = None
    use_model: bool = True

    # Backend gửi danh sách món KHÔNG được gợi ý lại (nó tự quản `GetExcludedMenuItemIds`). Nhận
    # để tôn trọng, thay vì bỏ qua rồi gợi lại đúng món khách vừa từ chối.
    excluded_menu_item_ids: list[str] = Field(default_factory=list)


app = FastAPI(title="AI tư vấn đặt món", version=SERVICE_VERSION)


@app.get("/health")
def health() -> dict[str, Any]:
    """Sống chưa. KHÔNG kiểm dữ liệu — đó là việc của `/ready`.

    Trộn hai thứ này là lỗi thường gặp: nếu `/health` cũng kiểm dữ liệu thì một lỗi dữ liệu sẽ
    làm orchestrator khởi động lại container, mà khởi động lại không sửa được lỗi dữ liệu.
    """
    return {"ok": True, "service": "ai", "version": SERVICE_VERSION}


@app.get("/ready")
def ready() -> dict[str, Any]:
    """Đã nạp xong dữ liệu chưa, và nạp được bao nhiêu.

    Báo **con số**, không chỉ `true/false`. Một dịch vụ trả `ready: true` với 0 món trong thực đơn
    là dịch vụ sẽ trả lời sai mọi câu — và đó đúng là lỗi đã xảy ra ở bản cũ theo dạng khác: kho
    tri thức nằm ngoài phạm vi `COPY` của Dockerfile nên trong container mọi chủ đề chính sách
    trả "chưa có dữ liệu", im lặng.
    """
    docs, chunks = _knowledge_counts()
    facts = load_facts()
    env = load_env()
    ok = bool(MENU.items) and bool(facts)
    return {
        "ready": ok,
        "menu_items": len(MENU.items),
        "menu_error": MENU.error,
        "knowledge_docs": docs,
        "knowledge_chunks": chunks,
        "verbatim_topics": len(facts),
        "model": env.get("LLM_MODEL") or None,
        "model_configured": bool(env.get("LLM_BASE_URL") and env.get("LLM_MODEL")),
        "memory_version": MEMORY_VERSION,
    }


def _run_turn(turn: ChatTurnIn) -> dict[str, Any]:
    """Một lượt trọn vẹn. Đây là chỗ DUY NHẤT trong tệp này gọi vào phần đã đo được.

    Thứ tự cố định: hiểu → hợp nhất bộ nhớ → (mô hình đọc thêm) → trả lời → ghi bộ nhớ.

    Mô hình chạy SAU khi hợp nhất bộ nhớ, không phải trước. Nếu chạy trước thì nó thấy một yêu
    cầu thiếu ràng buộc đã nhớ, và nó có thể "bổ sung" lại chính cái vừa bị bỏ — tức bộ nhớ mất
    tác dụng theo một đường rất khó thấy.
    """
    state = SessionState.from_payload(turn.session_state)
    merged = merge_into_request(understand(turn.question, MENU.items), state)

    # Món backend nói đừng gợi lại. Cộng vào bộ nhớ chứ không lọc riêng, để chỉ có MỘT chỗ quyết
    # định "món nào đã xem" — hai chỗ sẽ lệch nhau.
    if turn.excluded_menu_item_ids:
        state.suggested_item_ids = list(
            dict.fromkeys([*turn.excluded_menu_item_ids, *state.suggested_item_ids])
        )

    outcome = None
    if turn.use_model:
        # Không bọc `try` ở đây: `enrich()` tự thoái hóa êm và trả `LlmOutcome` kể cả khi gọi
        # thất bại. Bọc thêm một lớp `try` sẽ che mất lý do thất bại khỏi `decision.model`.
        outcome = enrich(merged, load_env(), use_cache=True)

    reply = respond(merged, MENU.items)

    # Thẻ giỏ sinh từ ĐÚNG danh sách món `respond()` đã chọn, không lọc lại. `cart.build_cart`
    # cố tình không nhận thực đơn nên nó không thể trở thành đường chọn món thứ hai.
    #
    # `CartError` nghĩa là lọc fail-closed đã hỏng — món mang nhãn cần tránh lọt qua
    # `answer.select()`. Không bắt nó ở đây: để nó nổi lên `chat()` và thành `internal_error`,
    # tức khách nhận câu chuyển nhân viên chứ KHÔNG nhận thẻ giỏ chứa món gây dị ứng.
    by_id = {m["id"]: m for m in MENU.items}
    chosen = [by_id[i] for i in reply.items if i in by_id]
    cart = build_cart(merged, chosen, reply.branch, reply.kind, MENU.category_names)

    new_state = update_state(state, merged, reply.items, reply.kind)
    return _to_payload(reply, new_state, outcome, cart)


def _to_payload(
    reply: Reply, state: SessionState, outcome: Any, cart: list[Any] | None = None
) -> dict[str, Any]:
    """Dịch `Reply` sang đúng tên trường backend đang đọc. Không quyết định gì về nội dung."""
    return {
        "ok": True,
        "provider_available": True,
        "content": reply.text,
        "suggested_cart_actions": cart_payload(cart or []),
        "guardrail_flags": _flags(reply, state),
        "suggest_staff_handoff": reply.kind in ("no_data", "refuse") or bool(state.avoid_tags),
        "session_updates": {
            **session_updates(state, reply.items),
            "session_state": state.to_payload(),
        },
        "decision": {
            "kind": reply.kind,
            "branch": reply.branch,
            "asks_back": reply.asks_back,
            "model": None if outcome is None else {
                "used": outcome.used,
                "ok": outcome.ok,
                "reason": outcome.reason,
                "latency_ms": outcome.latency_ms,
                "added_require": outcome.added_require,
                "added_prefer": outcome.added_prefer,
                "added_avoid": outcome.added_avoid,
                "dropped": outcome.dropped,
            },
        },
    }


def _flags(reply: Reply, state: SessionState) -> list[str]:
    """Cờ cho backend ghi log. Sinh từ trạng thái thật, không phải từ ý định."""
    flags: list[str] = []
    if state.avoid_tags:
        flags.append("allergen_filter_applied")
    if reply.kind == "no_data":
        flags.append("no_data")
    if reply.kind == "refuse":
        flags.append("out_of_scope")

    # Gắn cờ theo `kind`, KHÔNG theo `asks_back` — và đây là chỗ tôi đã lặp lại đúng một lỗi cũ
    # của dự án trước khi chạy thật phát hiện ra.
    #
    # `asks_back` bật ở HAI trường hợp khác nhau: nhánh `clarify` (chưa hiểu câu hỏi, phải hỏi
    # lại) và nhánh `filter` (đã liệt kê món RỒI MỜI THÊM). Gộp hai thứ đó lại thì câu "Món nào
    # không cay?" — trả 6 món kèm 3 thẻ giỏ — bị gắn cờ là câu hỏi lại.
    #
    # Bản cũ mắc đúng lỗi này ở THƯỚC ĐO: "tỷ lệ hỏi lại đọc ra 43% vì câu trả lời liệt kê món
    # rồi mời thêm bị tính là hỏi lại". Nó đã được sửa ở bước 3, và tôi mang nó trở lại trong
    # phần cờ log — nơi hậu quả giống hệt: người vận hành đọc log sẽ thấy một con số sai.
    if reply.kind == "clarify":
        flags.append("asked_clarifying_question")
    return flags


@app.post("/v1/chat", dependencies=[Depends(require_token)])
def chat(turn: ChatTurnIn) -> dict[str, Any]:
    """Trả lời một lượt.

    Bắt `Exception` rộng là CÓ CHỦ Ý ở đây, và chỉ ở đây. Khách đang ngồi ở bàn: trả 500 là họ
    thấy màn hình lỗi, còn trả câu chuyển nhân viên là họ vẫn được phục vụ. Lý do thật nằm trong
    `decision.error` để người vận hành đọc log, không nằm trong câu khách thấy.
    """
    try:
        return _run_turn(turn)
    except Exception as exc:  # noqa: BLE001 — xem docstring
        return {
            "ok": False,
            "provider_available": False,
            "content": FALLBACK_TEXT,
            "suggested_cart_actions": [],
            "guardrail_flags": ["internal_error"],
            "suggest_staff_handoff": True,
            "session_updates": {},
            "decision": {"kind": "no_data", "branch": "internal_error",
                         "error": f"{type(exc).__name__}: {exc}"},
        }


@app.post("/v1/chat/stream", dependencies=[Depends(require_token)])
def chat_stream(turn: ChatTurnIn) -> StreamingResponse:
    """Cùng nội dung với `/v1/chat`, phát dạng SSE.

    Câu trả lời được tính **trọn vẹn trước** rồi mới phát ra từng đoạn. Không phải streaming thật,
    và nói rõ ở đây thay vì để người đọc mã tự đoán: câu trả lời là kết quả của phép lọc tất định
    nên nó có sẵn ngay, không có gì để streaming dần. Endpoint này tồn tại vì frontend đã gọi nó.

    Phát theo TỪ, không theo ký tự — tiếng Việt có dấu tổ hợp nên cắt giữa ký tự sẽ hiện ra ô
    vuông trên màn hình khách.
    """
    payload = chat(turn)

    def stream():
        for word in str(payload["content"]).split(" "):
            yield f"data: {json.dumps({'delta': word + ' '}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True, **payload}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/v1/cache/invalidate", dependencies=[Depends(require_token)])
def invalidate() -> dict[str, Any]:
    """Nạp lại thực đơn sau khi admin sửa món.

    Trả về số món SAU khi nạp, để người gọi biết việc nạp có thật sự thành công — trả `{"ok": true}`
    thì một lần nạp thất bại nhìn giống một lần nạp thành công.
    """
    MENU.reload()
    return {"ok": MENU.error is None, "menu_items": len(MENU.items), "error": MENU.error}
