# CMC Restaurant Python AI Service

Thư mục này chứa lớp AI viết bằng Python cho CMC Restaurant. Service này tách khỏi backend .NET để phần AI/RAG có thể phát triển, kiểm thử và trình bày độc lập cho học phần Học máy và Khai phá dữ liệu.

## Vai Trò

- Nhận câu hỏi của khách từ backend.
- Truy xuất tri thức nhà hàng từ `ai/knowledge-base/`.
- Dựng prompt an toàn và gọi **DeepSeek** (mặc định) qua 9router; GPT-5.5 cho paired eval khi cần.
- Trả về câu trả lời, nguồn RAG đã dùng và guardrail flags.
- Không tự tạo đơn hàng, không tự thêm món vào giỏ và không tự thanh toán.

## Luồng

```text
Customer Web
  -> .NET Backend API
    -> Python AI Service
      -> RAG retriever
      -> 9router (OpenAI-compatible API)
        -> DeepSeek (mặc định triển khai)
```

## Chạy Local

```bash
cd ai
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Biến môi trường khuyến nghị (khớp notebook Part II + Docker):

```env
LLM_PROVIDER=9router
LLM_BASE_URL=http://localhost:20128/v1
LLM_MODEL=oc/deepseek-v4-flash-free
LLM_API_KEY=replace-with-your-9router-key
AI_INTERNAL_TOKEN=replace-with-a-long-random-internal-token
RAG_KNOWLEDGE_BASE_PATH=ai/knowledge-base
RAG_TOP_K=5
RAG_RETRIEVAL_METHOD=hybrid
AI_EMBEDDING_MODEL=e5_small
```

Backend (.NET): `CHAT_AI_PROVIDER=python-rag`, `AI_SERVICE_URL=http://127.0.0.1:8001`, `AI_INTERNAL_TOKEN` trùng với service Python.

Nếu không có `LLM_API_KEY`, service vẫn trả về fallback có kiểm soát để demo RAG và guardrails, nhưng sẽ không gọi 9router.

## Endpoint

- `GET /health`: kiểm tra service.
- `POST /v1/rag/search`: truy xuất context từ knowledge base.
- `POST /v1/chat`: tạo trả lời AI dựa trên RAG và optional LLM call.

## Kiểm Thử Core RAG

```bash
python -m compileall ai/app
python -m unittest discover -s ai/tests
```

Smoke thật (9router): `py scripts/smoke_9router.py` — không in secret.

Smoke chat (giống deploy health-check):

```powershell
curl -H "Authorization: Bearer $env:AI_INTERNAL_TOKEN" -H "Content-Type: application/json" -d "{\"message\":\"Xin chào\"}" http://127.0.0.1:8001/v1/chat
```

## Notebook nghiên cứu RAG

- Notebook duy nhất: `notebooks/rag_llm_system_research.ipynb` (5 phần, mọi số liệu đọc từ
  artifact JSON trong `evaluation/results/`).
- Dựng lại: `py scripts/build_rag_llm_research.py`
- Thực thi để sinh số và biểu đồ: `py -m nbconvert --to notebook --inplace --execute
  notebooks/rag_llm_system_research.ipynb --ExecutePreprocessor.timeout=900`
- Cần `requirements-notebook.txt`. Artifact live (`notebook_live_test.json`) sinh bằng
  `py scripts/_run_live_tests.py` và cần 9router.
- Hợp đồng: `tests/test_research_notebook.py` kiểm tra thứ tự 5 phần, mọi artifact bắt buộc có
  mặt, mọi code cell đã chạy và không cell nào lỗi.

Artifact release (§16): `dev_retrieval_summary.v3.json`, `session_e2e_eval.json`, `knowledge_manifest.json` — tái tạo bằng script trong `evaluation/` (xem `docs/ai/AI_STAGING_READINESS.md`).

## Deploy staging

Xem [`docs/ai/VPS_STAGING_AI_RUNBOOK.md`](../docs/ai/VPS_STAGING_AI_RUNBOOK.md) và workflow GitHub **Deploy Staging**.
