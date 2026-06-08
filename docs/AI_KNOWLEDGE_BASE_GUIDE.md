# Hướng Dẫn Xây Knowledge Base Cho RAG

Knowledge base là phần "dạy" AI theo nghĩa RAG: AI không học lại trọng số model, mà đọc tài liệu đã kiểm soát trước khi trả lời.

## Vị Trí

```text
ai/knowledge-base/
  menu.md
  ordering-policy.md
  faq.md
  brand-voice.md
  data-mining-insights.md
```

## Nguyên Tắc Viết

- Viết tiếng Việt có dấu.
- Mỗi file tập trung vào một nhóm tri thức.
- Ưu tiên câu ngắn, rõ, có thể truy xuất.
- Không ghi API key, thông tin nhạy cảm hoặc dữ liệu cá nhân.
- Nếu có giá, phải khớp menu backend hoặc ghi rõ chỉ là ví dụ.

## Ưu Tiên Nguồn Khi Trả Lời

1. Menu backend trong request.
2. Policy/guardrails.
3. FAQ.
4. Knowledge base menu.
5. Insight ML/Data Mining.

Nếu insight mâu thuẫn với menu backend, ưu tiên menu backend.

## Ví Dụ Nội Dung Tốt

```text
Nếu khách hỏi món thanh mát, ưu tiên Trà đào cam sả hoặc Chè khúc bạch nếu còn hàng.
AI không được tự tạo combo mới. Nếu muốn gợi ý nhóm món, hãy nói đây là đề xuất và yêu cầu khách xác nhận.
```

## Ví Dụ Nội Dung Không Tốt

```text
Nếu khách muốn, tự thêm món vào giỏ luôn.
```

Lý do: vi phạm guardrail, AI không được tự tạo thao tác đặt hàng.

## Cách Cải Thiện Sau Mỗi Tuần

- Thu thập câu hỏi khách hay hỏi.
- Ghi lại câu trả lời lỗi hoặc thiếu context.
- Bổ sung FAQ/policy/menu insight.
- Chạy lại evaluation set.
- Ghi evidence bằng screenshot, log hoặc bảng pass/fail.
