# AI/RAG Evaluation

Thư mục này chứa bộ câu hỏi vàng để kiểm tra Python AI service.

## Mục Tiêu Đánh Giá

- Retrieval accuracy: câu hỏi có lấy đúng tài liệu liên quan không.
- Faithfulness: câu trả lời có bám context không.
- Safety: AI có tránh tự tạo đơn, tự thêm giỏ, bịa món, bịa giá không.
- Usefulness: câu trả lời có giúp khách thao tác tốt hơn không.

## Cách Chạy Thủ Công

1. Chạy service Python.
2. Gửi từng câu trong `golden_questions.csv` vào `POST /v1/chat`.
3. Kiểm tra `expected_sources` có xuất hiện trong `retrieved_sources`.
4. Kiểm tra `expected_guardrail_flags` nếu có.
5. Đánh dấu pass/fail và ghi lỗi vào báo cáo tuần.

## Chỉ Số Đề Xuất

- Retrieval hit rate@5.
- Guardrail precision.
- Hallucination rate.
- Human acceptance rate.
