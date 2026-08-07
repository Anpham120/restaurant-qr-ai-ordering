# Kiểm thử — kế hoạch, checklist, bằng chứng

> **Một tài liệu cho toàn bộ mảng này.** Gộp từ 6 tệp: `TEST_PLAN.md`, `E2E_MULTI_DEVICE_CHECKLIST.md`, `SMOKE_TEST_EVIDENCE.md`, `ai-context-and-guardrail-regressions.tdd.md`, `ai-timeout-budget.tdd.md`, `chat-context-regression-tdd.md`.
>
> Năm tệp cùng nói việc kiểm thử, trong đó ba tệp là BẰNG CHỨNG một lần (TDD, smoke test) vốn nên nằm cạnh kế hoạch để đọc được mạch.


---

## Kế hoạch kiểm thử

*(gộp từ `docs/TEST_PLAN.md`)*

Tài liệu này ghi checklist tích hợp thủ công cho issue #10. Phạm vi là review contract, seed data plan và scenario test; không implement feature code.

> Lưu ý lịch sử: đây là snapshot tại thời điểm issue #10 (Tuần 2). Backend hiện đã có order/chat/payment/realtime endpoints kèm test; tài liệu giữ lại làm hồ sơ kịch bản kiểm thử thủ công.

### 1. Nguồn Kiểm Tra

- Issue: [#10](https://github.com/Anpham120/restaurant-qr-ai-ordering/issues/10).
- Branch docs: `issue-10/anpham120-api-contract-seed-integration`.
- API contract: [docs/API_CONTRACT.md](../backend/API_CONTRACT.md).
- Seed data chuẩn: `T01` đến `T08`, menu item `m_001` đến `m_012`.
- Open PR review ngày `2026-06-05`: `gh pr list --repo Anpham120/restaurant-qr-ai-ordering --state open --json number,title,headRefName,baseRefName,author,url,updatedAt` trả `[]`; không có PR mở tại thời điểm kiểm tra.

### 2. Drift / Risk Cần Theo Dõi

Các điểm dưới đây được ghi nhận để member xử lý trong issue code tương ứng, không sửa trong issue #10:

- Frontend admin mock đang dùng table code `T-05`; contract chuẩn là `T05`.
- Frontend admin mock đang dùng `paymentStatus: "Pending"`; contract chuẩn là `Unpaid`, `Paid`, `Failed`, `Cancelled`.
- Frontend menu mock đang dùng menu ID `mi-001`; contract/backend DTO chuẩn dùng `m_001`.
- Frontend `MenuItem` type hiện thiếu `categoryId`; contract public menu cần `categoryId` để admin/chatbot đồng bộ.
- Tại thời điểm issue #10, backend chưa có order/chat/realtime endpoints hoàn chỉnh nên các scenario dưới đây là kế hoạch kiểm thử; hiện các endpoint Orders/Chat/Payments/Realtime đã được implement kèm test.

### 3. Scenario QR Customer Order

Mục tiêu: khách quét QR tại bàn, xem menu, đặt món và theo dõi đơn.

Tiền điều kiện:

- Seed table `T05` active.
- Menu có ít nhất `m_001` và `m_009` đang `isAvailable: true`.
- Frontend route `/table/T05` lưu context `tableCode = T05`.

Các bước:

1. Mở `/table/T05`.
2. Frontend gọi `GET /api/tables/T05`.
3. Backend trả `tableCode: "T05"`, `displayName: "Bàn 05"`, `isActive: true`.
4. Frontend gọi `GET /api/menu`.
5. Khách thêm `m_001` số lượng `2` và `m_009` số lượng `1`.
6. Frontend gửi `POST /api/orders` với `orderType: "DineIn"`, `tableCode: "T05"`, `paymentMethod: "COD"`.
7. Backend trả `201 Created`, `status: "Placed"`, `paymentStatus: "Unpaid"`, item status `Pending`.
8. Frontend mở `/orders/{orderCode}` và gọi `GET /api/orders/{orderCode}`.

Kỳ vọng:

- Không có field dùng dạng `T-05`.
- Không có món `isAvailable: false` trong payload tạo đơn.
- UI tracking hiển thị order status và item status theo enum trong contract.
- Nếu thử `tableCode = ABC`, backend trả `400 TABLE_CODE_INVALID`.

### 4. Scenario Từ Chối OrderType Không Hợp Lệ (Pickup)

Mục tiêu: đảm bảo backend chỉ chấp nhận `DineIn` (đã bỏ Pickup mang về).

Tiền điều kiện:

- Menu public có item available.
- Có `tableSessionId` hợp lệ (hoặc context bàn từ QR).

Các bước:

1. Gửi `POST /api/orders` với `orderType: "Pickup"`, `tableCode: "T05"`, `paymentMethod: "COD"`, `items` hợp lệ.

Kỳ vọng:

- Backend trả `400 ORDER_TYPE_INVALID`.
- Không tạo đơn mới.

### 5. Scenario Admin Availability Change

Mục tiêu: admin đổi trạng thái còn món và customer/chatbot tôn trọng trạng thái đó.

Tiền điều kiện:

- Admin đăng nhập với role `Admin`.
- Menu item `m_003` hoặc `m_010` dùng làm unavailable demo.

Các bước:

1. Admin gọi `GET /api/admin/menu-items`.
2. Admin gọi `PATCH /api/admin/menu-items/m_003/availability` với `{ "isAvailable": false }`.
3. Frontend customer gọi lại `GET /api/menu`.
4. UI vẫn thấy món nhưng hiển thị hết hàng và disable thao tác thêm vào giỏ.
5. Chatbot không đề xuất món `isAvailable: false` trong `suggestedCartActions`.
6. Nếu customer cố gửi `POST /api/orders` chứa `m_003`, backend trả `400 MENU_ITEM_UNAVAILABLE`.

Kỳ vọng:

- Contract trả `isAvailable` rõ ràng trong public menu và admin menu.
- Admin response sau PATCH giữ cùng shape menu item.
- Không có cache/mock frontend giữ trạng thái cũ sau khi reload dữ liệu.

### 7. Verification Cho Issue #10

Do issue #10 là docs-only, verification bắt buộc:

- `git diff --check`.
- Kiểm tra file tồn tại: `docs/API_CONTRACT.md`, `docs/archive/PROJECT_CONTEXT.md`, `docs/TEST_PLAN.md`.
- Kiểm tra link nội bộ trong docs trỏ tới file tồn tại.
- Review open PRs cho contract drift.

Verification nên chạy nếu môi trường có đủ dependency:

- Frontend: `npm run build` trong `frontend`.
- Backend: `dotnet test RestaurantQrAiOrdering.sln` trong `backend`.

Nếu build/test không chạy được, report phải ghi rõ lỗi môi trường hoặc dependency thay vì đánh dấu pass.

---

## Checklist đa thiết bị đầu-cuối

*(gộp từ `docs/E2E_MULTI_DEVICE_CHECKLIST.md`)*

### Mục tiêu

Chứng minh hệ thống chạy qua backend/database thật giữa nhiều thiết bị hoặc nhiều browser profile, không dựa vào `localStorage`, mock data, hoặc một tab duy nhất.

### Môi trường

- Local: backend API + PostgreSQL + frontend trỏ về `VITE_API_BASE_URL` thật.
- Staging: domain/subdomain staging trỏ về backend và database staging.
- Gemini API có thể bật thật; nếu provider lỗi, chatbot phải fallback an toàn và không tự sửa giỏ hàng.

### Kịch bản smoke bắt buộc

1. Customer device mở route QR/table hoặc session khách, chọn món, gửi đơn.
2. Kitchen hoặc staff device khác đăng nhập role vận hành, gọi danh sách đơn từ backend và thấy đơn mới.
3. Kitchen cập nhật trạng thái món sang `Preparing` hoặc `Ready`.
4. Customer tracking device refresh hoặc theo dõi đơn và thấy trạng thái mới từ backend.
5. Customer tạo thanh toán VietQR hoặc chọn COD.
6. Staff xác nhận thanh toán bằng endpoint/hành động vận hành; customer tracking thấy `Confirmed`.
7. Customer dùng AI chat để hỏi gợi ý món. AI chỉ trả về đề xuất hoặc fallback, mọi `SuggestedCartAction` phải yêu cầu khách xác nhận.

### Ops deep-link smoke (manual)

1. **Payment toast → counter filter:** Khách yêu cầu thanh toán → staff thấy toast → click mở `/counter?tab=payments&table=…` → danh sách lọc đúng bàn.
2. **Floor drawer → kanban:** Từ sơ đồ bàn, mở link kanban `?table=` → đơn của bàn được highlight trên board.

### Script/test tự động trong repo

Chạy test tích hợp nhiều client:

```bash
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj --filter MultiDeviceE2ETests --nologo
```

Test này tạo nhiều `HttpClient` độc lập để mô phỏng customer, kitchen, staff và tracking device. Dữ liệu đi qua API/backend store chung, không dùng `localStorage` hay mock frontend.

### Evidence khi đóng issue

- Log test `MultiDeviceE2ETests` pass.
- Log backend test tổng pass.
- Screenshot hoặc video ngắn nếu chạy manual trên local/staging:
  - màn hình khách gửi đơn;
  - màn hình bếp/staff thấy cùng order code;
  - màn hình tracking thấy trạng thái/payment mới;
  - màn hình AI chat có fallback hoặc suggested action yêu cầu xác nhận.

---

## Bằng chứng smoke test API

*(gộp từ `docs/SMOKE_TEST_EVIDENCE.md`)*

Run date: 2026-06-08 12:18:43 +07:00

Command used:

```powershell
dotnet run --project backend/src/RestaurantQrAiOrdering.Api
```

Base URL: `http://localhost:5084` / `http://127.0.0.1:5084`

### Results

| Step | Endpoint | Status | Result | Response summary |
| --- | --- | ---: | --- | --- |
| Health | `GET /api/health` | 200 | PASS | `status=Healthy`, `service=RestaurantQrAiOrdering.Api`, environment `Development`. |
| Menu seed data | `GET /api/menu` | 200 | PASS | Returned 6 categories and 12 menu items. |
| Active table | `GET /api/tables/T05` | 200 | PASS | Returned `tableCode=T05`, `displayName=Ban 05`, `isActive=true`. |
| Invalid table | `GET /api/tables/T00` | 400 | PASS | Returned error code `TABLE_CODE_INVALID`. |
| Create order | `POST /api/orders` | 201 | PASS | Created `orderCode=ORD-1002`, `orderType=DineIn`, `tableCode=T05`, `status=Placed`, one item `m_001`. |
| Get order | `GET /api/orders/ORD-1002` | 200 | PASS | Returned persisted `orderCode=ORD-1002`, `tableCode=T05`, `status=Placed`, one order item. |

### Conclusion

Manual API smoke test passed. Health, menu seed data, table validation, order creation, and order persistence all matched the issue #18 API contract expectations in the same API process.

---

## TDD — ngữ cảnh chat và hàng rào

*(gộp từ `docs/testing/ai-context-and-guardrail-regressions.tdd.md`)*

Source plan: user journeys and acceptance criteria derived during the production
repair on 2026-07-26; no external plan file was used.

### User journeys

1. As a Vietnamese guest, I can say "gợi ý hai món" and receive two cards.
2. As a guest, I can ask "món thứ hai giá bao nhiêu?" and receive the price
   for the second card I was shown, not an arbitrary recent dish.
3. As an operator, the canonical safety catalogue verifies the exact flag
   emitted by the deterministic prompt-injection guardrail.

### RED → GREEN evidence

| Guarantee | Test target | RED | GREEN |
| --- | --- | --- | --- |
| Vietnamese word count limits cards | `test_conversation_policy.py::test_vietnamese_word_count_limits_recommendations` | `requested_count` was `None` | Passed after deterministic word-count parsing |
| Ordinal price refers to second displayed dish | `test_assistant_llm_first.py::test_price_for_second_suggested_dish_uses_second_item_in_order` | Resolver returned `m_050`, not `m_009` | Passed after ordered-card ordinal resolution |
| Canonical injection case expects runtime flag | `test_canonical_research_data.py::test_pipeline_runner_receives_cases_adapted_only_from_the_catalogue` | Manifest projected `PROMPT_INJECTION` | Passed after aligning it to `PROMPT_INJECTION_BLOCKED` |

RED command (with the repository Python import path):

```powershell
$env:PYTHONPATH='ai'; py -3 -m pytest ai/tests/test_conversation_policy.py ai/tests/test_assistant_llm_first.py ai/tests/test_canonical_research_data.py -q
```

Result: 3 intended failures, 23 passing tests.

GREEN and focused integration command:

```powershell
$env:PYTHONPATH='ai'; py -3 -m pytest ai/tests/test_conversation_policy.py ai/tests/test_assistant_llm_first.py ai/tests/test_canonical_research_data.py ai/tests/test_prompt_injection_guardrail.py ai/tests/test_pipeline_profile_eval.py ai/tests/test_pipeline_selection.py ai/tests/test_verify_pipeline_selection.py ai/tests/test_ai_ops_deploy_contract.py -q
```

Result: `56 passed, 15 subtests passed in 1.35s`.

### Coverage and limits

The current Python runtime does not expose `pytest-cov` (`pytest --help` has no
`--cov` option), so a numerical coverage percentage was not invented. The
focused suite covers the changed word-count parser, the end-to-end deterministic
price resolver, the canonical dataset adapter, prompt injection, profile
selection, artifact verification, and deploy contract. Full-suite execution is
delegated to CI before merge.

---

## TDD — ngân sách timeout AI

*(gộp từ `docs/testing/ai-timeout-budget.tdd.md`)*

### Source and user journey

Derived from the approved production rollout: as a diner, I need the browser-facing
API to wait for the bounded AI request so a valid DeepSeek/Luna answer is not
discarded as a premature timeout.

### RED → GREEN

| Stage | Command | Result | What it proves |
| --- | --- | --- | --- |
| RED | `dotnet test backend/RestaurantQrAiOrdering.sln --configuration Release --no-restore --filter "FullyQualifiedName~DeploymentConfigurationTests.DockerCompose_AllowsPythonRequestBudgetToFinishBeforeBackendTimeout"` | Failed: the compose file did not expose a 50-second backend timeout. | The former 18-second API timeout was incompatible with the 45-second AI budget. |
| GREEN | Same focused command after the compose correction, plus `docker compose -f deploy/docker-compose.yml config --quiet` with required CI-safe variables. | Passed; compose validation passed. | The deployed defaults give the AI service 45 seconds and the API 50 seconds. |

The guard lives in `backend/tests/RestaurantQrAiOrdering.Api.Tests/DeploymentConfigurationTests.cs` and checks the compose defaults directly. It does not claim that an external model always responds before 45 seconds; it protects the internal timeout ordering used by deployment.

### Checkpoints

- `bb06fc3 test: reproduce AI timeout budget contract` — RED test update and observed failure.
- `cb6c3d8 fix(deploy): keep backend alive through AI budget` — minimal compose correction and GREEN evidence.

### Coverage and limits

The focused configuration test is a static deployment-contract test. Full backend regression and CI/security suites remain required before merge and deployment; their result is intentionally not claimed by this document.

---

## TDD — hồi quy ngữ cảnh món đã gợi ý

*(gộp từ `docs/ai/chat-context-regression-tdd.md`)*

### User journey

A guest receives two suggested dishes, then asks for the price of the second
dish. The assistant must resolve that dish from the current menu rather than
asking the guest to repeat its name.

### RED

`ChatStoreTests.DbStore_LedgerKeepsSuggestedItemsAvailableForFactualFollowUps`
was changed to assert that a `suggested` recommendation is not placed in the
backend's exclusion set. Before the fix it failed because `m_001` was present
in the set.

Command:

```powershell
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj --filter FullyQualifiedName~ChatStoreTests.DbStore_LedgerKeepsSuggestedItemsAvailableForFactualFollowUps --no-restore
```

### GREEN

The ledger now treats only `rejected`, `accepted`, and `added_to_cart` as
recommendation exclusions. `suggested` remains in typed state and chat history,
which lets factual follow-ups resolve it while the Python recommendation policy
still prevents duplicate suggestions.

Validation:

```powershell
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj --no-restore
## Passed: 81

$env:PYTHONPATH='ai'
ai/.venv/Scripts/python.exe -m unittest ai.tests.test_assistant_llm_first.AssistantLlmFirstTests.test_price_for_second_suggested_dish_uses_second_item_in_order -v
## Passed: 1
```

The deployed staging smoke remains the final integration gate: it must answer
the price of the second suggested dish and preserve the winner from
`pipeline_selection.json` before merge or production deployment.

### Safe recovery when an LLM claim is unverified

#### Failure mode

For an evidence-first recommendation, the model can return valid action cards
whose IDs and prices resolve against the live menu, alongside one unsupported
sentence.  The previous response gate correctly detected the unsupported
sentence, but then removed every action card as well.  A guest consequently
saw the generic "not enough verified evidence" fallback even though the menu
already contained safe, verified recommendations.

#### RED

`AssistantLlmFirstTests.test_grounded_recommendation_survives_an_unverified_model_claim`
uses a deterministic test client that returns the real `m_009` card together
with the false claim that its price is 1 VND.  Before the change the response
contained no suggested actions, so the test failed.

```powershell
$env:PYTHONPATH='ai'
ai/.venv/Scripts/python.exe -m unittest ai.tests.test_assistant_llm_first.AssistantLlmFirstTests.test_grounded_recommendation_survives_an_unverified_model_claim -v
## Before fix: suggested action IDs were []
```

#### GREEN

When at least one action card resolves to the current menu, the response gate
keeps those resolved cards, replaces the model prose with deterministic text
rendered from the live menu, and rebuilds claims from those cards.  It records
`MODEL_CLAIM_REPLACED_WITH_LIVE_MENU_EVIDENCE` for audit.  If no valid card
exists, the original fail-closed abstention remains unchanged.

```powershell
$env:PYTHONPATH='ai'
ai/.venv/Scripts/python.exe -m unittest `
  ai.tests.test_assistant_llm_first.AssistantLlmFirstTests.test_grounded_recommendation_survives_an_unverified_model_claim `
  ai.tests.test_fastpath_claim_grounding.FastPathClaimGroundingTests.test_claim_marked_unverified_cannot_pass_the_response_gate -v
## Passed: 2

ai/.venv/Scripts/python.exe -m unittest discover -s ai/tests -p "test_*.py"
## Passed: 393
```

This recovery is deliberately narrower than a fallback: it does not trust
model-generated facts, and it cannot introduce a dish, ID, or price that is
not present in the permitted menu evidence.  The subsequent staging smoke
checks the real Vietnamese recommendation journey before a merge is allowed.
