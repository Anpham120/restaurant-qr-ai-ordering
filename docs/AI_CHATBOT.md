# AI Chatbot: Gemini 3.5 Flash, Python RAG Và Guardrails

Tài liệu này chốt hướng AI chatbot của CMC Restaurant sau khi nâng cấp lên kiến trúc Python RAG service. Mục tiêu là để AI trong app không chỉ là một ô chat gọi model, mà có dữ liệu, luật an toàn, đánh giá và ranh giới nghiệp vụ rõ ràng.

## 1. Bản Chất Hệ AI

Hệ thống sử dụng:

- **Model:** Gemini 3.5 Flash.
- **Cách truy cập model:** Google Gemini API chính thức.
- **AI service:** Python FastAPI service trong thư mục `ai/`.
- **Knowledge grounding:** RAG từ `ai/knowledge-base/`.
- **Backend nghiệp vụ:** .NET backend vẫn kiểm tra menu, giá, trạng thái món, giỏ hàng và đơn hàng.

Mô tả cách gọi model:

> CMC Restaurant gọi trực tiếp Gemini 3.5 Flash qua Google Gemini API, kết hợp RAG và guardrails để tư vấn món ăn an toàn.

## 2. Luồng Kiến Trúc

```text
Customer Web
  -> .NET Backend API
    -> Python AI Service
      -> RAG retriever
      -> Google Gemini API
        -> Gemini 3.5 Flash
```

Frontend chỉ gọi API chat của backend. Backend bật provider `python-rag` để chuyển phần AI sang service Python; chỉ service Python giữ khóa và gọi Google Gemini API.

## 3. Biến Môi Trường

Backend:

```env
AI_PROVIDER=python-rag
AI_SERVICE_URL=http://127.0.0.1:8001
AI_TIMEOUT_SECONDS=30
AI_MAX_RETRY=1
```

Python AI service:

```env
AI_PROVIDER=gemini
AI_MODEL=gemini-3.5-flash
GEMINI_API_KEY=<secret>
RAG_KNOWLEDGE_BASE_PATH=ai/knowledge-base
RAG_TOP_K=5
```

Không commit `GEMINI_API_KEY`, `.env` thật hoặc log chứa secret.

## 4. RAG Là Gì Trong Dự Án Này?

RAG là cơ chế cho AI tra cứu tài liệu nhà hàng trước khi trả lời. Gemini không tự đoán menu. Service Python lấy context từ:

- menu và tag món;
- chính sách đặt món, mang về, thanh toán;
- FAQ nhà hàng;
- phong cách trả lời CMC Restaurant;
- insight từ notebook học máy và khai phá dữ liệu ở `coursework/ai-ml-data-mining/`.

Nếu context không đủ, AI phải nói chưa có đủ thông tin thay vì bịa.

## 5. Guardrails Bắt Buộc

AI chatbot không được:

- tự tạo đơn hàng;
- tự thanh toán;
- tự thêm món vào giỏ khi khách chưa xác nhận;
- bịa món, bịa giá, bịa khuyến mãi;
- gợi ý món đang hết hàng như món có thể đặt;
- trả lời ngoài phạm vi nhà hàng nếu câu hỏi không liên quan.

Backend luôn là lớp kiểm tra cuối cùng. Dù Python service trả về gợi ý, backend vẫn phải validate món, giá, availability và quyền thao tác.

## 6. Ranh Giới Với Fine-Tune

Nhóm không fine-tune Gemini. Hướng triển khai hiện tại là:

- RAG để kiểm soát tri thức;
- prompt engineering để kiểm soát hành vi;
- evaluation set để đo chất lượng;
- feedback loop để cập nhật knowledge base.

Fine-tune chỉ phù hợp ở giai đoạn nâng cao khi có nhiều dữ liệu thật, ví dụ fine-tune intent classifier hoặc một model nhỏ riêng. Với menu/giá thay đổi thường xuyên, RAG phù hợp hơn.

## 7. Output Của AI Service

Python service trả về:

```json
{
  "content": "Câu trả lời tiếng Việt có dấu",
  "provider_available": true,
  "model": "gh/gemini-3.1-pro-preview",
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

## 8. Kiểm Thử Và Đánh Giá

Evaluation nằm trong `ai/evaluation/`:

- câu hỏi vàng;
- expected sources;
- expected guardrail flags;
- tiêu chí retrieval accuracy, faithfulness, hallucination rate và safety.

Notebook trong `coursework/ai-ml-data-mining/` chứng minh phần học máy và khai phá dữ liệu. Python AI service dùng các insight đó như context hỗ trợ, không thay thế menu backend.
