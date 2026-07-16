# Kế Hoạch Đánh Giá AI/RAG

## Mục Tiêu

Đánh giá AI không chỉ bằng cảm giác "trả lời hay", mà bằng tiêu chí có thể kiểm tra:

- câu hỏi có truy xuất đúng tài liệu không;
- câu trả lời có bám context không;
- AI có tránh bịa món, bịa giá, tự tạo đơn không;
- câu trả lời có hữu ích cho khách không.

## Bộ Dữ Liệu Đánh Giá

File chính:

```text
ai/evaluation/golden_questions.csv
```

Mỗi dòng gồm:

- `case_id`;
- câu hỏi khách;
- nguồn RAG kỳ vọng;
- guardrail flag kỳ vọng;
- ghi chú nghiệp vụ.

## Chỉ Số

| Chỉ số | Ý nghĩa |
| --- | --- |
| Retrieval hit rate@5 | Top 5 context có chứa nguồn đúng không. |
| Faithfulness | Câu trả lời có bám context không. |
| Hallucination rate | Tỷ lệ câu trả lời bịa món, giá, chính sách. |
| Guardrail precision | Khi có rủi ro, flag có bật đúng không. |
| Human acceptance rate | Người review có chấp nhận câu trả lời không. |

## Quy Trình Review

1. Chạy Python AI service.
2. Gửi các câu trong `golden_questions.csv`.
3. Lưu response, retrieved sources và guardrail flags.
4. So sánh với expected sources/flags.
5. Ghi lỗi vào báo cáo tuần.
6. Cập nhật knowledge base hoặc prompt.

## Liên Hệ Với Học Máy Và Khai Phá Dữ Liệu

Notebook `coursework/ai-ml-data-mining/CMC_Restaurant_AI_ML_Data_Mining.ipynb` chứng minh:

- dataset schema;
- association rule mining;
- content-based recommendation;
- baseline;
- evaluation.

Python AI service dùng kết quả đó như tri thức hỗ trợ trong RAG. Đây là cách kết nối phần học thuật với sản phẩm thật mà không tuyên bố sai rằng nhóm đã huấn luyện lại Gemini.
