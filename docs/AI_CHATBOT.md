# AI Chatbot: 9router, RAG Và Guardrails

Tài liệu này chốt thiết kế AI chatbot cho issue #11. Mục tiêu là dùng LLM API thật qua 9router nhưng vẫn kiểm soát được câu trả lời bằng menu, FAQ, quy tắc nhà hàng và guardrails rõ ràng.

## 1. Phạm Vi

AI chatbot hỗ trợ khách hàng:

- hỏi thông tin món ăn, giá, mô tả, tình trạng còn/hết;
- hỏi gợi ý món theo nhu cầu, khẩu vị hoặc số người;
- hỏi FAQ cơ bản như giờ mở cửa, thanh toán, phục vụ tại bàn;
- đề xuất hành động thêm món vào giỏ qua `SuggestedCartAction`.

AI chatbot không được:

- tự tạo đơn hàng;
- tự thanh toán;
- tự thêm món vào giỏ khi khách chưa xác nhận;
- bịa món, bịa giá, bịa khuyến mãi hoặc gợi ý món đang hết hàng;
- trả lời ngoài phạm vi nhà hàng nếu câu hỏi không liên quan.

## 2. Chiến Lược LLM API

Provider chốt dùng `9router`. Frontend không gọi 9router trực tiếp. Luồng đúng:

```text
Frontend/browser
  -> Backend API: /api/chat/sessions/{chatSessionId}/messages
    -> AI service
      -> RAG retriever
      -> 9router
        -> LLM provider
```

### 2.1. Biến Môi Trường

Backend đọc cấu hình từ environment hoặc secret store:

```env
AI_PROVIDER=9router
AI_BASE_URL=http://127.0.0.1:<9router_port>
AI_API_KEY=<secret>
AI_MODEL=<model_name>
AI_TIMEOUT_SECONDS=20
AI_MAX_RETRY=1
```

Quy ước môi trường:

- Local hiện tại: backend chạy local và gọi 9router local bằng `AI_BASE_URL=http://127.0.0.1:<9router_port>`.
- CI/build test: dùng mock/stub AI, không cần API key thật và không gọi 9router thật.
- Production/VPS: backend và 9router chạy cùng VPS hoặc cùng private network; backend gọi 9router bằng URL nội bộ.
- Docker Compose production-like: nếu 9router là service trong cùng compose network, dùng `AI_BASE_URL=http://ai-router:<port>`.

Không commit `AI_API_KEY`, `.env` thật hoặc log chứa secret.

### 2.2. Provider Abstraction

Backend nên tách interface provider để dễ mock và đổi model:

```text
IAiChatProvider
  - GenerateChatAsync(AiChatRequest request, CancellationToken ct)

Implementations:
  - NineRouterChatProvider
  - MockAiChatProvider
```

`NineRouterChatProvider` chỉ nhận prompt đã được backend dựng sẵn từ RAG context và policy. Frontend không được tự gửi system prompt hoặc provider config.

## 3. Nguồn Dữ Liệu RAG

RAG lấy context từ dữ liệu có kiểm soát:

- menu public: `GET /api/menu`;
- FAQ nhà hàng;
- quy tắc vận hành: khách phải xác nhận trước khi thêm món, không đặt món đã hết hàng, không tự thanh toán;
- insight ML/Data Mining từ issue #39 nếu có, ví dụ món thường đi kèm nhau.

Notebook issue #39 không gọi 9router và không gọi LLM API. Notebook chỉ sinh insight/data mining để có thể đưa vào context sau này.

### 3.1. KnowledgeEntry Shape

```json
{
  "id": "menu:m_001",
  "source": "menu",
  "title": "Cơm gà xối mỡ",
  "content": "Cơm gà xối mỡ giá 45000 VND, thuộc nhóm Món chính, còn bán.",
  "metadata": {
    "menuItemId": "m_001",
    "categoryId": "cat_main",
    "categoryName": "Món chính",
    "price": 45000,
    "isAvailable": true,
    "tags": ["phổ biến"]
  },
  "updatedAt": "2026-06-05T00:00:00Z"
}
```

`source` hợp lệ:

| Source | Mục đích |
| --- | --- |
| `menu` | Món ăn, giá, danh mục, trạng thái còn/hết. |
| `faq` | Câu hỏi thường gặp về vận hành nhà hàng. |
| `policy` | Quy tắc guardrail bắt buộc. |
| `insight` | Gợi ý từ data mining/recommendation nếu có. |

### 3.2. Retrieval Rules

- Chỉ đưa vào prompt các entry liên quan nhất, ưu tiên `menu`, `faq`, `policy`.
- Không đưa món `isAvailable=false` vào danh sách gợi ý mua; chỉ được nhắc rằng món đang hết hàng.
- Nếu câu hỏi về giá, giá trong response phải lấy từ `metadata.price`.
- Nếu context không đủ, chatbot phải nói chưa có thông tin thay vì tự suy đoán.
- `insight` chỉ là tín hiệu phụ; không được ghi đè giá, tên món hoặc trạng thái món từ `menu`.

## 4. Prompt Policy

System prompt backend cần thể hiện các quy tắc sau:

```text
Bạn là trợ lý AI của CMC Restaurant.
Chỉ trả lời dựa trên context menu, FAQ, policy và insight được cung cấp.
Không bịa món, giá, tình trạng còn hàng, khuyến mãi hoặc chính sách.
Nếu context không có thông tin, hãy nói chưa có thông tin trong hệ thống.
Không tự tạo đơn hàng, không tự thanh toán và không tự thêm món vào giỏ.
Nếu muốn đề xuất món, chỉ trả SuggestedCartAction để khách xác nhận.
Không gợi ý món isAvailable=false như món có thể đặt.
```

Backend không nên để model tự quyết định toàn bộ JSON. Sau khi gọi LLM, backend phải validate lại `suggestedCartActions` bằng menu hiện tại.

## 5. API Output Và SuggestedCartAction

Chat response có thể có `suggestedCartActions`, nhưng đây chỉ là đề xuất.

```json
{
  "menuItemId": "m_001",
  "name": "Cơm gà xối mỡ",
  "price": 45000,
  "quantity": 1,
  "reason": "Món chính phổ biến, phù hợp bữa trưa.",
  "requiresCustomerConfirmation": true
}
```

Validation bắt buộc:

- `menuItemId` phải tồn tại trong menu.
- `name` và `price` phải khớp menu hiện tại.
- `isAvailable` phải là `true`.
- `quantity` phải từ `1` đến `10`.
- `requiresCustomerConfirmation` luôn là `true`.

Nếu validation fail, backend loại bỏ action đó và có thể trả `guardrailFlags`.

## 6. Guardrails

| Rủi ro | Cách chặn |
| --- | --- |
| Bịa món | Chỉ cho phép action với `menuItemId` tồn tại trong menu. |
| Bịa giá | Backend ghi đè/validate `price` theo menu, không tin giá từ LLM. |
| Gợi ý món hết hàng | Lọc `isAvailable=false` khỏi cart action. |
| Tự đặt đơn | Không có endpoint AI tạo order; khách phải dùng cart/order flow. |
| Lộ secret | API key chỉ ở backend env/secrets, không log raw request chứa key. |
| Trả lời ngoài phạm vi | Nếu không liên quan nhà hàng, trả lời ngắn và kéo về menu/FAQ. |
| Prompt injection | Không cho user override system prompt, policy hoặc source priority. |

## 7. Fallback

Nếu 9router lỗi, timeout hoặc response không hợp lệ:

```json
{
  "message": {
    "role": "assistant",
    "content": "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống."
  },
  "suggestedCartActions": [],
  "guardrailFlags": ["AI_PROVIDER_UNAVAILABLE"]
}
```

Fallback không được tạo action giả.

## 8. Sample Q&A

### Case 1: Hỏi món còn bán

User: "Có cơm gà không?"

Expected:

- Nếu `m_001` còn bán, trả lời có món, mô tả ngắn và giá đúng.
- Nếu hết hàng, nói món đang hết hàng và gợi ý món thay thế còn bán.

### Case 2: Hỏi món không tồn tại

User: "Nhà hàng có pizza hải sản không?"

Expected:

- Không bịa món.
- Trả lời chưa có thông tin/món này trong menu hiện tại.
- Có thể gợi ý món cùng nhóm nếu context có.

### Case 3: Gợi ý cho 2 người

User: "Gợi ý món cho 2 người ăn trưa"

Expected:

- Trả lời bằng món có trong menu và còn bán.
- Có thể trả `suggestedCartActions`.
- Mọi action đều `requiresCustomerConfirmation=true`.

### Case 4: Hỏi ngoài phạm vi

User: "Viết code Python giúp tôi"

Expected:

- Từ chối nhẹ.
- Kéo về nhiệm vụ nhà hàng: "Mình có thể hỗ trợ chọn món hoặc giải đáp thông tin CMC Restaurant."

## 9. Evaluation Checklist

Khi review issue/PR AI, kiểm tra:

- câu trả lời dùng đúng món và giá trong menu;
- món hết hàng không xuất hiện trong `suggestedCartActions`;
- món không tồn tại không bị bịa ra;
- `SuggestedCartAction` luôn yêu cầu khách xác nhận;
- lỗi provider có fallback an toàn;
- CI/unit test không cần API key thật;
- không có secret trong commit, log, README hoặc notebook.

## 10. Quan Hệ Với Issue Khác

- Issue #12 implement backend chat/session/API theo contract này.
- Issue #14 implement UI chatbot nhưng chỉ gọi backend, không gọi 9router trực tiếp.
- Issue #16 triển khai production/VPS cho backend và 9router.
- Issue #39 làm notebook ML/Data Mining, không gọi 9router/LLM API.
