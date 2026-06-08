from __future__ import annotations

from app.rag.knowledge_base import KnowledgeChunk


SYSTEM_POLICY = """Bạn là trợ lý AI của CMC Restaurant.
Chỉ trả lời dựa trên menu, FAQ, chính sách nhà hàng và context RAG được cung cấp.
Không bịa món, không bịa giá, không tự tạo đơn, không tự thêm món vào giỏ và không tự thanh toán.
Nếu thiếu dữ liệu, hãy nói rõ hệ thống chưa có đủ thông tin.
Trả lời ngắn gọn, lịch sự, bằng tiếng Việt có dấu.
"""


def build_messages(
    user_message: str,
    context_chunks: list[KnowledgeChunk],
    menu_items: list[dict],
    history: list[dict],
) -> list[dict[str, str]]:
    context_text = "\n\n".join(
        f"[{index}] {chunk.citation}\n{chunk.content}"
        for index, chunk in enumerate(context_chunks, start=1)
    )
    menu_text = "\n".join(_format_menu_item(item) for item in menu_items[:20])
    recent_history = [
        {"role": item.get("role", "user"), "content": item.get("content", "")}
        for item in history[-8:]
        if item.get("content")
    ]

    return [
        {"role": "system", "content": SYSTEM_POLICY},
        {"role": "system", "content": f"RAG context:\n{context_text or 'Không có context phù hợp.'}"},
        {"role": "system", "content": f"Menu hiện có:\n{menu_text or 'Menu chưa được cung cấp.'}"},
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
    price = item.get("price_vnd") or item.get("price") or item.get("unit_price_vnd") or "chưa rõ"
    tags = item.get("tags") or []
    if isinstance(tags, str):
        tags_text = tags
    else:
        tags_text = ", ".join(str(tag) for tag in tags)
    available = "còn món" if bool(item.get("is_available", True)) else "hết món"
    return f"- {item_id}: {name}, giá {price} VND, {available}, tags: {tags_text}"
