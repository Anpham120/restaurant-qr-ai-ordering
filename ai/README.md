# CMC Restaurant Python AI Service

Thư mục này chứa lớp AI viết bằng Python cho CMC Restaurant. Service này tách khỏi backend .NET để phần AI/RAG có thể phát triển, kiểm thử và trình bày độc lập cho học phần Học máy và Khai phá dữ liệu.

## Vai Trò

- Nhận câu hỏi của khách từ backend.
- Truy xuất tri thức nhà hàng từ `ai/knowledge-base/`.
- Dựng prompt an toàn cho Gemini 3.1 thông qua 9router.
- Trả về câu trả lời, nguồn RAG đã dùng và guardrail flags.
- Không tự tạo đơn hàng, không tự thêm món vào giỏ và không tự thanh toán.

## Luồng

```text
Customer Web
  -> .NET Backend API
    -> Python AI Service
      -> RAG retriever
      -> 9router API gateway
        -> Gemini 3.1
```

## Chạy Local

```bash
cd ai
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Biến môi trường khuyến nghị:

```env
AI_PROVIDER=9router
AI_BASE_URL=http://127.0.0.1:20128/v1
AI_MODEL=gh/gemini-3.1-pro-preview
AI_API_KEY=replace-with-9router-key
RAG_KNOWLEDGE_BASE_PATH=ai/knowledge-base
```

Nếu không có `AI_API_KEY`, service vẫn trả về fallback có kiểm soát để demo RAG và guardrails, nhưng sẽ không gọi Gemini 3.1.

## Endpoint

- `GET /health`: kiểm tra service.
- `POST /v1/rag/search`: truy xuất context từ knowledge base.
- `POST /v1/chat`: tạo trả lời AI dựa trên RAG và optional LLM call.

## Kiểm Thử Core RAG

```bash
python -m compileall ai/app
```

Các test này kiểm tra retriever và guardrails bằng thư viện chuẩn Python, không cần gọi 9router và không cần API key.
