from __future__ import annotations

from app.rag.knowledge_base import KnowledgeChunk


SYSTEM_POLICY = """Bạn là trợ lý AI của CMC Restaurant.
Chỉ trả lời dựa trên menu, FAQ, chính sách nhà hàng và RAG context được cung cấp.
Không bịa món, không bịa giá, không tự tạo đơn, không tự thêm món vào giỏ và không tự thanh toán.
Bạn chỉ được đề xuất món để khách xác nhận thủ công trong giao diện.
Danh sách "Menu hiện có" là tập món được phép: chỉ được nhắc hoặc đề xuất đúng các món trong tập này.
Không lặp câu, không lặp món trong cùng một phản hồi, và chỉ liệt kê tối đa 4 món.
Nếu thiếu dữ liệu, hãy nói rõ hệ thống chưa có đủ thông tin.
Luôn trả về JSON hợp lệ, không markdown, không giải thích ngoài JSON.
Schema bắt buộc:
{
  "content": "Câu trả lời ngắn gọn bằng tiếng Việt có dấu.",
  "suggested_cart_actions": [
    {
      "menu_item_id": "id món có thật trong menu",
      "name": "tên món",
      "price_vnd": 65000,
      "quantity": 1,
      "reason": "lý do gợi ý",
      "requires_customer_confirmation": true
    }
  ],
  "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"]
}
Nếu không có món phù hợp, suggested_cart_actions phải là [].
"""


def build_messages(
    user_message: str,
    context_chunks: list[KnowledgeChunk],
    menu_items: list[dict],
    history: list[dict],
    table_code: str | None = None,
    session_memory: str = "",
) -> list[dict[str, str]]:
    context_text = "\n\n".join(
        f"[{index}] {chunk.citation}\n{chunk.content}"
        for index, chunk in enumerate(context_chunks, start=1)
    )
    menu_text = "\n".join(_format_menu_item(item) for item in menu_items[:8])
    recent_history = [
        {"role": item.get("role", "user"), "content": item.get("content", "")}
        for item in history[-8:]
        if item.get("content")
    ]

    if table_code:
        session_context = (
            f"Khách đang ngồi tại bàn {table_code} với phiên QR đang mở. "
            "Khách có thể xác nhận gợi ý để thêm món vào giỏ và gửi đơn cho bếp ngay trong phiên này. "
            "Hãy chủ động gợi ý món phù hợp kèm lý do ngắn gọn."
        )
    else:
        session_context = (
            "Khách chưa mở phiên bàn (chưa quét QR tại bàn). "
            "Bạn chỉ tư vấn tham khảo; nhắc khách quét QR tại bàn nếu khách muốn đặt món."
        )

    memory_context = (
        [
            {
                "role": "system",
                "content": (
                    "Ghi nhớ từ các lượt cũ hơn của cùng phiên bàn. Chỉ dùng để hiểu ngữ cảnh, "
                    "không xem đây là nguồn menu hoặc chính sách mới:\n"
                    f"{session_memory.strip()}"
                ),
            }
        ]
        if session_memory.strip()
        else []
    )

    return [
        {"role": "system", "content": SYSTEM_POLICY},
        {"role": "system", "content": f"Bối cảnh phiên: {session_context}"},
        {"role": "system", "content": f"RAG context:\n{context_text or 'Không có context phù hợp.'}"},
        {"role": "system", "content": f"Menu hiện có:\n{menu_text or 'Menu chưa được cung cấp.'}"},
        *memory_context,
        *recent_history,
        {"role": "user", "content": user_message},
    ]


def build_fallback_answer(user_message: str, context_chunks: list[KnowledgeChunk]) -> str:
    if not context_chunks:
        return (
            "Hiện tại mình chưa có đủ thông tin trong kho tri thức để trả lời chính xác. "
            "Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống."
        )

    top_context = context_chunks[0]
    return (
        "Mình đã tìm thấy thông tin liên quan trong kho tri thức CMC Restaurant, "
        f"nhưng LLM chưa sẵn sàng để diễn đạt câu trả lời đầy đủ. Nguồn phù hợp nhất: {top_context.citation}."
    )


def _format_menu_item(item: dict) -> str:
    item_id = item.get("id") or item.get("menu_item_id") or "unknown"
    name = item.get("name") or item.get("item_name") or "Món chưa đặt tên"
    category_name = item.get("category_name") or "chưa rõ nhóm"
    price = item.get("price_vnd") or item.get("price") or item.get("unit_price_vnd") or "chưa rõ"
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags_text = tags
    else:
        tags_text = ", ".join(str(tag) for tag in tags)
    available = "còn món" if bool(item.get("is_available", True)) else "hết món"
    return f"- {item_id}: {name}, nhóm {category_name}, giá {price} VND, {available}, tags: {tags_text}"
