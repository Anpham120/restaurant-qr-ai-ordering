---
id: kb.guide.context-disambiguation.v1
title: Hướng Dẫn Phân Biệt Ngữ Cảnh
domain: guardrails
tags: [context, disambiguation, intent]
language: vi
source: ai_engineering_team
reviewed_by: ai_lead
reviewed_at: 2026-07-19
expires_at: 2027-01-19
safety_level: medium
---

# Hướng Dẫn Phân Biệt Ngữ Cảnh Câu Hỏi

## Nguyên Tắc Chung

AI phải đọc TOÀN BỘ câu hỏi trước khi quyết định cách trả lời. Không phản xạ theo từ đơn lẻ. Một từ có thể mang nhiều nghĩa khác nhau tùy theo ngữ cảnh.

## Từ "Đặt" Có Nhiều Nghĩa

| Câu hỏi | Ý nghĩa | Intent đúng |
|---|---|---|
| "Đặt món phở bò" | Gọi món ăn | order |
| "Đặt bàn trước được không?" | Hỏi chính sách đặt bàn | restaurant_info |
| "Đặt phòng VIP" | Hỏi phòng riêng | restaurant_info |
| "Đặt riêng cho nhóm" | Hỏi dịch vụ | service |

## Từ "Giá" Có Nhiều Nghĩa

| Câu hỏi | Ý nghĩa | Intent đúng |
|---|---|---|
| "Giá phở bò bao nhiêu?" | Hỏi giá món ăn | ask_price |
| "Giá phòng VIP thế nào?" | Hỏi phí dịch vụ | restaurant_info |
| "Món nào giá rẻ?" | Gợi ý theo ngân sách | budget/recommend |
| "Có phụ giá cuối tuần không?" | Hỏi chính sách | restaurant_info |

## Từ "Người" Có Nhiều Nghĩa

| Câu hỏi | Ý nghĩa | Intent đúng |
|---|---|---|
| "4 người ăn gì?" | Gợi ý món cho nhóm | recommend |
| "2 người ngồi đâu?" | Hỏi bàn/chỗ ngồi | restaurant_info |
| "Gọi người quản lý" | Escalation | staff_escalation |
| "Bao nhiêu người vào được?" | Hỏi sức chứa | restaurant_info |

## Từ "Có" Có Nhiều Nghĩa

| Câu hỏi | Ý nghĩa | Intent đúng |
|---|---|---|
| "Có món chay không?" | Hỏi menu có loại món | dietary |
| "Có wifi không?" | Hỏi dịch vụ | restaurant_info |
| "Có nhận đặt bàn trước?" | Hỏi chính sách | restaurant_info |
| "Có chỗ đậu xe không?" | Hỏi tiện ích | restaurant_info |

## Câu Hỏi Về Món Cụ Thể — Trả Lời Từ Menu, Không Cần RAG

Khi khách hỏi về một món ăn cụ thể có trong menu (giá, mô tả, còn hàng), trả lời trực tiếp từ dữ liệu menu. KHÔNG cần tìm trong RAG context.

Ví dụ:
- "Phở bò giá bao nhiêu?" → Trả giá từ menu data.
- "Còn lẩu thái không?" → Kiểm tra is_available trong menu.
- "Cơm sườn có gì?" → Mô tả từ menu data.

## Câu Hỏi Chính Sách — Dùng RAG Context

Khi khách hỏi về chính sách, thông tin nhà hàng, dịch vụ → dùng RAG context nhưng DIỄN ĐẠT LẠI cho phù hợp câu hỏi.

Ví dụ:
- "Giờ mở cửa?" → RAG: restaurant-info hoặc faq.
- "Thanh toán bằng gì?" → RAG: payment-methods.
- "Wifi mật khẩu gì?" → RAG: faq.

## Câu Hỏi Follow-Up — Dùng History

Khi khách nói "thêm gì nữa?", "rồi sao?", "ok, vậy..." → xem lịch sử hội thoại, KHÔNG search RAG mới.

## Khi Câu Hỏi Mơ Hồ — Hỏi Lại

Nếu không chắc ý khách, hỏi lại ngắn gọn thay vì đoán sai:
- "Có gì không?" → "Bạn muốn xem thực đơn hay cần gợi ý món phù hợp?"
- "Cho hỏi" → "Dạ, bạn muốn hỏi về thực đơn, dịch vụ, hay thanh toán ạ?"
