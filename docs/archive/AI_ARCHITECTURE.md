# Kiến trúc hệ thống AI

> **Một tài liệu cho toàn bộ mảng này.** Gộp từ 2 tệp: `AI_CHATBOT.md`, `AI_RAG_ARCHITECTURE.md`.
>
> Hai tệp cùng mô tả một dịch vụ: một tệp nói đường đi của request, một tệp nói các lớp bên trong. Tách ra thì mỗi lần đổi kiến trúc phải nhớ sửa hai chỗ.


---

## Tổng quan dịch vụ và đường đi của một câu hỏi

*(gộp từ `docs/AI_CHATBOT.md`)*

Tài liệu này chốt hướng AI chatbot của CMC Restaurant sau khi nâng cấp lên kiến trúc Python RAG service. Mục tiêu là để AI trong app không chỉ là một ô chat gọi model, mà có dữ liệu, luật an toàn, đánh giá và ranh giới nghiệp vụ rõ ràng.

### 1. Bản Chất Hệ AI

Hệ thống sử dụng:

- **Model triển khai:** GPT-5.6 Luna (`cx/gpt-5.6-luna-review`) qua 9router; GPT-5.5 (`cx/gpt-5.5`) vẫn dùng cho quality gate / paired eval khi cần. DeepSeek (`oc/deepseek-v4-flash-free`) không còn là model chính thức — route của nó trong 9router từ chối `response_format:json_object`, field mọi request thật đều cần (xem `docs/ai/AI_DECISION_HISTORY.md` §1).
- **Cách truy cập model:** duy nhất qua gateway 9router tương thích OpenAI.
- **AI service:** Python FastAPI service trong thư mục `ai/`.
- **Knowledge grounding:** hybrid RAG (BM25 + multilingual E5 + RRF) từ `ai/knowledge-base/` và thực đơn live 91 món, bao gồm đồ uống.
- **Backend nghiệp vụ:** .NET backend vẫn kiểm tra menu, giá, trạng thái món, giỏ hàng và đơn hàng.

Mô tả cách gọi model:

> CMC Restaurant gọi **GPT-5.6 Luna** (mặc định staging/production) qua 9router, kết hợp RAG và guardrails để tư vấn món ăn an toàn.

### 2. Luồng Kiến Trúc

```text
Customer Web
  -> .NET Backend API
    -> Python AI Service
      -> RAG retriever
        -> BM25 + multilingual E5 + reciprocal-rank fusion
      -> 9router (OpenAI-compatible)
        -> GPT-5.6 Luna (mặc định) hoặc GPT-5.5 (eval)
```

Frontend chỉ gọi API chat của backend. Backend đặt `CHAT_AI_PROVIDER=python-rag` để chuyển phần AI sang service Python; chỉ service Python giữ khóa gateway và gọi 9router.

### 3. Biến Môi Trường

Backend:

```env
CHAT_AI_PROVIDER=python-rag
AI_SERVICE_URL=http://127.0.0.1:8001
BACKEND_AI_TIMEOUT_SECONDS=12
```

Python AI service:

```env
LLM_PROVIDER=9router
LLM_BASE_URL=http://localhost:20128/v1
LLM_API_KEY=<9router-gateway-secret>
LLM_MODEL=cx/gpt-5.6-luna-review
LLM_TIMEOUT_SECONDS=60
AI_MAX_RETRY=1
RAG_KNOWLEDGE_BASE_PATH=ai/knowledge-base
RAG_TOP_K=5
RAG_RETRIEVAL_METHOD=hybrid
AI_EMBEDDING_MODEL=e5_small
AI_LLM_FIRST=true
```

`AI_LLM_FIRST=true` (mặc định staging/production): mọi lượt hội thoại/gợi ý đi qua GPT-5.6 Luna; hybrid RAG và menu live được đưa vào prompt để model quyết dùng nguồn nào. **Ngoại lệ không gọi LLM:** guardrail bảo mật; tra **giá / calo / dị ứng** một món đã resolve (`live_data`); khi `AI_LLM_FIRST=false` các fast-path deterministic legacy (KB, party, pairing, budget) vẫn có thể trả lời sớm (lab).

Cấu hình trên khớp Part II notebook (Hybrid RRF + `intfloat/multilingual-e5-small`). Docker staging/production: xem `deploy/docker-compose.yml` service `ai-service`.

Để chạy sweep quality gate bằng GPT-5.5, đổi `LLM_MODEL=cx/gpt-5.5`. Không commit `LLM_API_KEY`, `.env` thật hoặc log chứa secret.

### 4. RAG Là Gì Trong Dự Án Này?

RAG là cơ chế cho AI tra cứu tài liệu nhà hàng trước khi trả lời. LLM không được tự đoán menu. Service Python dùng hybrid retrieval đã được benchmark trên tập dev, đồng thời áp bộ lọc cứng theo danh mục/tag và trạng thái còn bán. Service lấy context từ:

- menu và tag món;
- chính sách đặt món, mang về, thanh toán;
- FAQ nhà hàng;
- phong cách trả lời CMC Restaurant;
- insight từ notebook nghiên cứu `ai/notebooks/rag_llm_system_research.ipynb` (notebook duy nhất của dự án).

Nếu context không đủ, AI phải nói chưa có đủ thông tin thay vì bịa.

### 5. Guardrails Bắt Buộc

AI chatbot không được:

- tự tạo đơn hàng;
- tự thanh toán;
- tự thêm món vào giỏ khi khách chưa xác nhận;
- bịa món, bịa giá, bịa khuyến mãi;
- gợi ý món đang hết hàng như món có thể đặt;
- trả lời ngoài phạm vi nhà hàng nếu câu hỏi không liên quan.

Backend luôn là lớp kiểm tra cuối cùng. Dù Python service trả về gợi ý, backend vẫn phải validate món, giá, availability và quyền thao tác.

### 6. Ranh Giới Với Fine-Tune

Nhóm không fine-tune GPT-5.5 hoặc GPT-5.6 Luna. Hướng triển khai hiện tại là:

- RAG để kiểm soát tri thức;
- prompt engineering để kiểm soát hành vi;
- evaluation set để đo chất lượng;
- feedback loop để cập nhật knowledge base.

Fine-tune chỉ phù hợp ở giai đoạn nâng cao khi có nhiều dữ liệu thật, ví dụ fine-tune intent classifier hoặc một model nhỏ riêng. Với menu/giá thay đổi thường xuyên, RAG phù hợp hơn.

### 7. Output Của AI Service

Python service trả về:

```json
{
  "content": "Câu trả lời tiếng Việt có dấu",
  "provider_available": true,
  "model": "cx/gpt-5.5",
  "retrieved_sources": [
    {
      "source": "menu.md",
      "title": "Đồ Uống Và Tráng Miệng",
      "score": 0.42
    }
  ],
  "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
  "suggested_cart_actions": []
}
```

Ở giai đoạn này Python service **không trực tiếp tạo cart action**. Việc thêm món vào giỏ vẫn do backend/frontend thực hiện sau khi khách xác nhận.

### 8. Kiểm Thử Và Đánh Giá

Evaluation nằm trong `ai/evaluation/`:

- câu hỏi vàng;
- expected sources;
- expected guardrail flags;
- tiêu chí retrieval accuracy, faithfulness, hallucination rate và safety.

Notebook trong `coursework/ai-ml-data-mining/` chứng minh phần học máy và khai phá dữ liệu. Python AI service dùng các insight đó như context hỗ trợ, không thay thế menu backend.

---

## Các lớp bên trong dịch vụ RAG

*(gộp từ `docs/AI_RAG_ARCHITECTURE.md`)*

### Mục Tiêu

Tách phần AI khỏi backend nghiệp vụ để hệ thống có thể phát triển AI bằng Python, dùng RAG và đánh giá chất lượng một cách độc lập. Backend .NET vẫn giữ vai trò kiểm soát nghiệp vụ nhà hàng.

### Thành Phần

| Thành phần | Vai trò |
| --- | --- |
| Frontend | Gửi câu hỏi của khách tới backend chat API. |
| .NET Backend | Quản lý session chat, menu, giỏ hàng, đơn hàng và validate nghiệp vụ. |
| Python AI Service | Truy xuất RAG, dựng prompt, gọi trực tiếp Gemini 3.5 Flash. |
| Google Gemini API | API chính thức cung cấp model Gemini 3.5 Flash. |
| Knowledge Base | Tài liệu nhà hàng để grounding câu trả lời. |
| Evaluation Set | Bộ câu hỏi vàng để đo retrieval, safety và hallucination. |

### Luồng Request

```text
POST /api/chat/sessions/{id}/messages
  -> ChatAssistantService (.NET)
    -> IChatAiProvider
      -> AI_PROVIDER=python-rag
        -> POST /v1/chat (Python)
          -> LexicalRetriever
          -> Prompt Builder
          -> Google Gemini API / Gemini 3.5 Flash
          -> Guardrail metadata
    -> Backend validate business rules
  -> Chat response to frontend
```

### Vì Sao Dùng Python?

Python phù hợp cho phần AI vì:

- dễ xây RAG/retrieval;
- dễ tái sử dụng notebook học máy;
- dễ bổ sung vector search, embeddings, evaluation scripts;
- tách độc lập khỏi backend .NET để không làm lẫn business logic.

### Vì Sao Không Fine-Tune Ngay?

Fine-tune cần nhiều dữ liệu chất lượng cao, chi phí và quy trình kiểm soát model. Với bài toán nhà hàng, menu và giá thay đổi thường xuyên nên RAG hiệu quả hơn:

- cập nhật knowledge base nhanh;
- không cần train lại model;
- giảm rủi ro bịa giá/món;
- dễ giải thích trong báo cáo.

### Roadmap Kỹ Thuật

1. Lexical retriever trên Markdown knowledge base.
2. Thêm API service Python và backend provider `python-rag`.
3. Bổ sung evaluation set thủ công.
4. Nâng cấp sang embedding/vector store nếu dữ liệu lớn hơn.
5. Tự động chấm retrieval hit rate và guardrail precision.
6. Dùng log feedback để cập nhật knowledge base.
