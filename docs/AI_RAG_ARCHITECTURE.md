# Kiến Trúc Python RAG Service

## Mục Tiêu

Tách phần AI khỏi backend nghiệp vụ để hệ thống có thể phát triển AI bằng Python, dùng RAG và đánh giá chất lượng một cách độc lập. Backend .NET vẫn giữ vai trò kiểm soát nghiệp vụ nhà hàng.

## Thành Phần

| Thành phần | Vai trò |
| --- | --- |
| Frontend | Gửi câu hỏi của khách tới backend chat API. |
| .NET Backend | Quản lý session chat, menu, giỏ hàng, đơn hàng và validate nghiệp vụ. |
| Python AI Service | Truy xuất RAG, dựng prompt, gọi trực tiếp Gemini 2.5 Flash. |
| Google Gemini API | API chính thức cung cấp model Gemini 2.5 Flash. |
| Knowledge Base | Tài liệu nhà hàng để grounding câu trả lời. |
| Evaluation Set | Bộ câu hỏi vàng để đo retrieval, safety và hallucination. |

## Luồng Request

```text
POST /api/chat/sessions/{id}/messages
  -> ChatAssistantService (.NET)
    -> IChatAiProvider
      -> AI_PROVIDER=python-rag
        -> POST /v1/chat (Python)
          -> LexicalRetriever
          -> Prompt Builder
          -> Google Gemini API / Gemini 2.5 Flash
          -> Guardrail metadata
    -> Backend validate business rules
  -> Chat response to frontend
```

## Vì Sao Dùng Python?

Python phù hợp cho phần AI vì:

- dễ xây RAG/retrieval;
- dễ tái sử dụng notebook học máy;
- dễ bổ sung vector search, embeddings, evaluation scripts;
- tách độc lập khỏi backend .NET để không làm lẫn business logic.

## Vì Sao Không Fine-Tune Ngay?

Fine-tune cần nhiều dữ liệu chất lượng cao, chi phí và quy trình kiểm soát model. Với bài toán nhà hàng, menu và giá thay đổi thường xuyên nên RAG hiệu quả hơn:

- cập nhật knowledge base nhanh;
- không cần train lại model;
- giảm rủi ro bịa giá/món;
- dễ giải thích trong báo cáo.

## Roadmap Kỹ Thuật

1. Lexical retriever trên Markdown knowledge base.
2. Thêm API service Python và backend provider `python-rag`.
3. Bổ sung evaluation set thủ công.
4. Nâng cấp sang embedding/vector store nếu dữ liệu lớn hơn.
5. Tự động chấm retrieval hit rate và guardrail precision.
6. Dùng log feedback để cập nhật knowledge base.
