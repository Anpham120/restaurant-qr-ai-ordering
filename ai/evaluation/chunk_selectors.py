# -*- coding: utf-8 -*-
"""Ngôn ngữ điều kiện chọn ĐOẠN — khóa đáp án của tập đánh giá truy hồi.

Vì sao khóa đáp án là TRUY VẤN, không phải danh sách `chunk_id`
---------------------------------------------------------------
Cách viết thông thường là: câu hỏi → danh sách `chunk_id` đúng. Cách đó có một điểm yếu chết
người mà dự án này đã trả giá một lần: **danh sách viết tay thì không có cách nào kiểm.** Nó luôn
"đúng" theo định nghĩa. Bản cũ có **96 khóa đáp án trỏ vào những đoạn văn dành cho AI đọc** chứ
không dành cho khách, và không ai phát hiện suốt nhiều tháng.

Ở đây khóa đáp án là **điều kiện chọn**, và nó được **giải ra tập `chunk_id` khi chạy**. Nhờ vậy:

- kho tri thức đổi thì khóa đáp án đổi theo, không cần sửa tay 120 ca;
- một khóa trỏ vào chỗ không tồn tại là **lỗi thấy được** (`validate_retrieval_cases.py` báo),
  không phải một dòng JSON sai âm thầm;
- người đọc ca thấy được **ý định** ("đoạn nói về miền Trung") thay vì một mã máy vô nghĩa.

Hai loại điều kiện, và loại thứ hai quan trọng hơn
--------------------------------------------------
    expected    đoạn NÀO trả lời được câu này
    forbidden   đoạn nào TUYỆT ĐỐI không được trích cho câu này

`forbidden` là loại quan trọng hơn, và nó đo thứ mà Hit@k không đo: **trích đúng chủ đề**. Một bộ
truy hồi lấy 5 đoạn trong đó có 1 đoạn đúng và 4 đoạn về chủ đề khác vẫn được Hit@5 = 1,0 — nhưng
khách nhận một câu trả lời trộn bốn thứ không liên quan.

Đó là lý do chỉ số **forbidden@5** là chỉ số quan trọng nhất của phép so, không phải Hit@5.

Bốn khóa điều kiện
------------------
    doc_id          đúng một tài liệu
    doc_id_prefix   nhóm tài liệu, ví dụ "kb.region." cho mọi tài liệu vùng miền
    topic_keys_any  đoạn thuộc tài liệu có một trong các khóa chủ đề này
    heading_any     đoạn có tiêu đề mục nằm trong danh sách (dùng để nhắm mục cụ thể)

Khóa bắt đầu bằng `_` là ghi chú cho người đọc, bị bỏ qua khi giải — cùng quy ước với
`menu_selectors.clean_selector`.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

from rag.chunker import KnowledgeChunk, retrievable_chunks  # noqa: E402

KNOWLEDGE_PATH = REPO_ROOT / "ai" / "knowledge"

ALLOWED_KEYS = ("doc_id", "doc_id_prefix", "topic_keys_any", "heading_any")


class SelectorError(ValueError):
    """Điều kiện chọn viết sai. Là lỗi trong tập đánh giá, không phải lỗi hệ thống."""


_CACHE: list[KnowledgeChunk] | None = None


def corpus() -> list[KnowledgeChunk]:
    """Chỉ đoạn ĐƯỢC XẾP HẠNG (`answer_mode: synthesize`).

    Đoạn `verbatim` bị loại có chủ ý: chúng có đường tới khách riêng (tra khóa, trả nguyên văn),
    nên đưa chúng vào tập đánh giá truy hồi là đo một đường không tồn tại.
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = retrievable_chunks(KNOWLEDGE_PATH)
    return _CACHE


def clean_selector(selector: dict[str, Any]) -> dict[str, Any]:
    """Bỏ khóa ghi chú (`_why`, `_note`). Giữ nguyên phần còn lại để `validate` thấy khóa lạ."""
    return {k: v for k, v in selector.items() if not k.startswith("_")}


def validate_selector(selector: dict[str, Any]) -> None:
    """Báo lỗi ngay khi điều kiện viết sai, thay vì trả tập rỗng.

    Cố ý KHÔNG bỏ qua khóa lạ: một khóa gõ sai (`topic_key_any` thiếu chữ `s`) mà bị bỏ qua thì
    ca đó lặng lẽ đòi "mọi đoạn", và nó sẽ XANH mãi mãi. Cùng lý do với `menu_selectors`.
    """
    if not isinstance(selector, dict) or not selector:
        raise SelectorError("điều kiện chọn phải là dict không rỗng")
    for key in clean_selector(selector):
        if key not in ALLOWED_KEYS:
            raise SelectorError(f"khóa điều kiện không có: {key!r}, phải thuộc {ALLOWED_KEYS}")


def select_chunk_ids(selector: dict[str, Any]) -> set[str]:
    """Giải điều kiện chọn thành tập `chunk_id`.

    Các khóa trong cùng một điều kiện kết hợp bằng **AND** — `{"doc_id_prefix": "kb.region.",
    "heading_any": ["Danh sách món"]}` là "mục Danh sách món của mọi tài liệu vùng miền".
    """
    validate_selector(selector)
    sel = clean_selector(selector)
    out: set[str] = set()
    for chunk in corpus():
        if "doc_id" in sel and chunk.doc_id != sel["doc_id"]:
            continue
        if "doc_id_prefix" in sel and not chunk.doc_id.startswith(sel["doc_id_prefix"]):
            continue
        if "topic_keys_any" in sel and not set(chunk.topic_keys) & set(sel["topic_keys_any"]):
            continue
        if "heading_any" in sel and chunk.heading not in sel["heading_any"]:
            continue
        out.add(chunk.chunk_id)
    return out


def select_many(selectors: list[dict[str, Any]]) -> set[str]:
    """HỢP của nhiều điều kiện — dùng khi một câu hỏi có nhiều đoạn trả lời được."""
    out: set[str] = set()
    for selector in selectors:
        out |= select_chunk_ids(selector)
    return out


def describe(selector: dict[str, Any]) -> str:
    """Mô tả đọc được cho người, dùng trong thông báo lỗi của bộ kiểm tra."""
    sel = clean_selector(selector)
    parts = [f"{k}={v!r}" for k, v in sorted(sel.items())]
    n = len(select_chunk_ids(selector))
    return f"{{{', '.join(parts)}}} -> {n} đoạn"
