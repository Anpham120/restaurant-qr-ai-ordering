from __future__ import annotations

import time
from decimal import Decimal

from app.clients.nine_router import NineRouterClient
from app.config import AiServiceConfig
from app.domain import MenuItemContext, SearchResult
from app.intent import classify_intent
from app.retrieval.service import RetrievalService
from app.schemas import ChatResponse, RetrievedSource
from app.text import normalize_text, tokenize


FORBIDDEN_COMPLETION_CLAIMS = (
    "da dat mon",
    "da them vao gio",
    "da gui don",
    "da thanh toan",
    "don cua ban da duoc tao",
)


class AiAssistantService:
    def __init__(
        self,
        config: AiServiceConfig,
        retrieval: RetrievalService,
        client: NineRouterClient | None,
    ) -> None:
        self._config = config
        self._retrieval = retrieval
        self._client = client

    def search(self, query: str, menu_items: list[MenuItemContext], top_k: int | None = None) -> list[dict]:
        return [self._source_mapping(result) for result in self._retrieval.search(query, menu_items, top_k or 5)]

    async def chat(self, payload: dict) -> dict:
        total_started = time.perf_counter()
        message = str(payload.get("message") or "").strip()
        history = payload.get("history") or []
        table_code = str(payload.get("table_code") or "").strip() or None
        menu_items = [MenuItemContext.from_mapping(item) for item in payload.get("menu_items") or []]
        intent = classify_intent(message)
        flags = list(intent.flags)
        latency: dict[str, float] = {}

        if intent.out_of_scope or intent.prompt_injection:
            return self._response(
                "Mình chỉ hỗ trợ thực đơn, chính sách nhà hàng và gợi ý món an toàn.",
                [],
                flags,
                provider_available=False,
                fast_path="guardrail",
                latency=latency,
                total_started=total_started,
            )

        unavailable = _find_named_unavailable(message, menu_items)
        if unavailable is not None:
            flags.append("MENU_ITEM_UNAVAILABLE")
            return self._response(
                f"{unavailable.name} hiện đang tạm hết nên mình không thể đề xuất món này. Bạn có thể hỏi mình món thay thế.",
                [],
                flags,
                provider_available=False,
                fast_path="availability",
                latency=latency,
                total_started=total_started,
            )

        retrieval_query = _build_retrieval_query(message, history)
        retrieval_started = time.perf_counter()
        results = self._retrieval.search(retrieval_query, menu_items, self._config.top_k)
        latency["retrieval"] = _elapsed_ms(retrieval_started)
        menu_results = [result for result in results if result.document.kind == "menu"]
        policy_results = [result for result in results if result.document.kind == "policy"]

        if intent.asks_policy and policy_results:
            return self._response(
                policy_results[0].document.answer or policy_results[0].document.text,
                results,
                flags,
                provider_available=False,
                fast_path="policy",
                latency=latency,
                total_started=total_started,
            )

        if intent.asks_price and menu_results:
            item = _menu_item_for_result(menu_results[0], menu_items)
            if item is not None:
                return self._response(
                    f"{item.name} có giá {_format_vnd(item.price_vnd)}. Giá và tình trạng món được lấy trực tiếp từ menu hiện tại.",
                    results,
                    flags,
                    provider_available=False,
                    fast_path="price",
                    latency=latency,
                    total_started=total_started,
                )

        actions = _build_actions(menu_results, menu_items, limit=3 if intent.requests_recommendation else 1)
        if actions and "CUSTOMER_CONFIRMATION_REQUIRED" not in flags:
            flags.append("CUSTOMER_CONFIRMATION_REQUIRED")

        if intent.requests_action:
            content = (
                "Mình không thể tự đặt hoặc gửi đơn. Mình đã tạo gợi ý từ menu đang còn món; "
                "bạn hãy kiểm tra và bấm xác nhận trên giao diện nếu muốn thêm vào giỏ."
            )
            return self._response(
                content,
                results,
                flags,
                actions=actions,
                provider_available=False,
                fast_path="customer_confirmation",
                latency=latency,
                total_started=total_started,
            )

        answer: str | None = None
        provider_available = False
        if self._client is not None and self._config.llm_enabled and results:
            provider_started = time.perf_counter()
            try:
                answer = await self._client.complete(
                    _build_messages(message, history, table_code, results, menu_items)
                )
                answer = _validate_generated_content(answer)
                provider_available = answer is not None
            except Exception:
                flags.append("AI_PROVIDER_UNAVAILABLE")
            latency["provider"] = _elapsed_ms(provider_started)

        if not answer:
            answer = _fallback_answer(results, menu_items)
        return self._response(
            answer,
            results,
            flags,
            actions=actions,
            provider_available=provider_available,
            fast_path=None if provider_available else "retrieval_fallback",
            latency=latency,
            total_started=total_started,
        )

    def _response(
        self,
        content: str,
        results: list[SearchResult],
        flags: list[str],
        provider_available: bool,
        fast_path: str | None,
        latency: dict[str, float],
        total_started: float,
        actions: list[dict] | None = None,
    ) -> dict:
        latency["total"] = _elapsed_ms(total_started)
        response = ChatResponse(
            content=content,
            provider_available=provider_available,
            model=self._config.model,
            retrieved_sources=[
                RetrievedSource(
                    source=result.document.source,
                    title=result.document.title,
                    score=result.score,
                )
                for result in results
            ],
            guardrail_flags=_dedupe(flags),
            suggested_cart_actions=actions or [],
            retrieval_method=self._retrieval.method,
            fast_path=fast_path,
            latency_ms={key: round(value, 3) for key, value in latency.items()},
        )
        return response.model_dump()

    @staticmethod
    def _source_mapping(result: SearchResult) -> dict:
        return {
            "id": result.document.id,
            "kind": result.document.kind,
            "source": result.document.source,
            "title": result.document.title,
            "score": result.score,
            "menu_item_id": result.document.menu_item_id,
        }


def _build_retrieval_query(message: str, history: list[dict]) -> str:
    if len(tokenize(message)) >= 4:
        return message
    previous_user = next(
        (
            str(item.get("content") or "")
            for item in reversed(history)
            if str(item.get("role") or "").lower() == "user" and str(item.get("content") or "").strip()
        ),
        "",
    )
    return f"{previous_user} {message}".strip()


def _build_messages(
    message: str,
    history: list[dict],
    table_code: str | None,
    results: list[SearchResult],
    menu_items: list[MenuItemContext],
) -> list[dict[str, str]]:
    menu_by_id = {item.id: item for item in menu_items}
    context_lines = []
    for result in results:
        if result.document.menu_item_id and result.document.menu_item_id in menu_by_id:
            item = menu_by_id[result.document.menu_item_id]
            context_lines.append(
                f"- {item.name} | {int(item.price_vnd)} VND | {item.category_name} | {item.description}"
            )
        elif result.document.answer:
            context_lines.append(f"- {result.document.title}: {result.document.answer}")
    recent_history = [
        {"role": str(item.get("role") or "user"), "content": str(item.get("content") or "")}
        for item in history[-6:]
        if str(item.get("content") or "").strip()
    ]
    session = f"Khách đang ở bàn {table_code}." if table_code else "Khách chưa mở phiên QR tại bàn."
    return [
        {
            "role": "system",
            "content": (
                "Bạn là trợ lý tư vấn của CMC Restaurant. Chỉ dùng context được cung cấp. "
                "Không được nói rằng đã đặt món, thêm giỏ, gửi đơn hoặc thanh toán. "
                "Không tự tạo tên món, giá hay chính sách. Trả lời tiếng Việt ngắn gọn, không markdown."
            ),
        },
        {"role": "system", "content": session},
        {"role": "system", "content": "Context đã kiểm chứng:\n" + "\n".join(context_lines)},
        *recent_history,
        {"role": "user", "content": message},
    ]


def _build_actions(
    results: list[SearchResult], menu_items: list[MenuItemContext], limit: int
) -> list[dict]:
    by_id = {item.id: item for item in menu_items if item.is_available}
    actions: list[dict] = []
    seen: set[str] = set()
    for result in results:
        item_id = result.document.menu_item_id
        item = by_id.get(item_id or "")
        if item is None or item.id in seen:
            continue
        seen.add(item.id)
        actions.append(
            {
                "menu_item_id": item.id,
                "name": item.name,
                "price_vnd": int(item.price_vnd),
                "quantity": 1,
                "reason": "Món phù hợp nhất theo truy vấn và menu đang còn phục vụ.",
                "requires_customer_confirmation": True,
            }
        )
        if len(actions) >= limit:
            break
    return actions


def _fallback_answer(results: list[SearchResult], menu_items: list[MenuItemContext]) -> str:
    if not results:
        return "Mình chưa tìm thấy thông tin đủ chắc chắn trong menu và chính sách hiện tại. Bạn có thể hỏi cụ thể tên món, khẩu vị hoặc nhóm món."
    first = results[0]
    if first.document.answer:
        return first.document.answer
    item = _menu_item_for_result(first, menu_items)
    if item is not None:
        return f"Mình tìm thấy {item.name}, thuộc nhóm {item.category_name}, giá {_format_vnd(item.price_vnd)}. {item.description}"
    return "Mình đã tìm thấy thông tin liên quan nhưng chưa đủ dữ liệu để đưa ra gợi ý chắc chắn."


def _validate_generated_content(content: str | None) -> str | None:
    if not content or not content.strip():
        return None
    text = content.strip()[:1200]
    normalized = normalize_text(text)
    if any(claim in normalized for claim in FORBIDDEN_COMPLETION_CLAIMS):
        return None
    return text


def _find_named_unavailable(message: str, items: list[MenuItemContext]) -> MenuItemContext | None:
    normalized = normalize_text(message)
    return next(
        (item for item in items if not item.is_available and normalize_text(item.name) in normalized),
        None,
    )


def _menu_item_for_result(result: SearchResult, items: list[MenuItemContext]) -> MenuItemContext | None:
    return next((item for item in items if item.id == result.document.menu_item_id), None)


def _format_vnd(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", ".") + " VND"


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
