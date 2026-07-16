# Kế Hoạch Refactor — CMC Restaurant QR AI Ordering

> **Trạng thái: KẾ HOẠCH (plan-only). Chưa thực thi thay đổi code nào.** Tài liệu này liệt kê phần _thừa cần bỏ_ và _thiếu cần thêm_, kèm trình tự PR và rủi ro, để review trước khi bắt tay refactor.
>
> Nguồn chuẩn kiến trúc: [`docs/SYSTEM_ANALYSIS_DESIGN.md`](SYSTEM_ANALYSIS_DESIGN.md).

## 0. Nguyên Tắc

- **Đã kiểm chứng với code branch `develop`.** Mỗi mục dưới đều trỏ tới `file:line` thật. Không đưa vào danh sách những "vấn đề" chưa verify.
- **Surgical.** Mỗi PR một mục, xanh (build/test) trước khi sang PR kế tiếp. Không gộp refactor với UI rebuild.
- **Có 2 quyết định cần owner chốt trước khi execute** (đánh dấu ⚠️ ở mục 1.2 và 1.3).

---

## 1. THỪA — Cần Bỏ (đã verify)

### 1.1 Frontend drift domain Delivery — **11 file**

Backend đã bỏ hoàn toàn Delivery và Pickup (enum `OrderStatus` không còn `Delivering/Delivered`, `OrderType` chỉ còn `DineIn`, không có `deliveryInfo`/`pickupInfo`). Frontend vẫn còn tham chiếu "ma":

- `frontend/packages/shared-types/src/index.ts` — `OrderStatus` còn `Delivering/Delivered`; type `DeliveryInfo`; field `deliveryInfo` trong order type/request.
- 10 file còn lại tham chiếu delivery (cần dọn theo):
  - `frontend/src/types/index.ts`, `frontend/src/types/order.ts`, `frontend/src/types/api.ts`
  - `frontend/src/services/orderService.ts`, `frontend/src/services/adminOrderService.ts`
  - `frontend/src/pages/customer/CustomerCartPage.tsx`, `frontend/src/pages/StaffPaymentsPage.tsx`
  - `frontend/src/components/admin/AdminOrderManager.tsx`, `frontend/src/components/admin/AdminStatusBadge.tsx`, `frontend/src/components/staff/StaffOrderBoard.tsx`

**Việc cần làm:** bỏ `Delivering/Delivered` khỏi `OrderStatus`; xóa `DeliveryInfo` + field `deliveryInfo`; xóa mọi tham chiếu Pickup/`pickupInfo`; dọn UI hiển thị "Giao tận nơi" / "Mang về" ở các file trên.

**Rủi ro:** đổi shared type → lan ra typecheck 4 app. Medium. **Gate:** `npm run typecheck` + `vitest` + build cả 4 app.

### 1.2 ⚠️ `KnowledgeEntry` — bảng DB chết

- Định nghĩa: `backend/Entities/KnowledgeEntry.cs:8`. DbSet: `RestaurantDbContext.cs:38`. Config (map cột `embedding` jsonb): `RestaurantDbContext.cs:677`. Có trong mọi migration snapshot.
- **Không nơi nào populate hay query** entity này. Toàn bộ RAG (retrieval, embedding, KB) chạy ở Python AI service; backend .NET không làm retrieval.

**Việc cần làm (quyết định):**
- **Phương án A (khuyến nghị): bỏ.** Xóa entity + DbSet + config, migration `DropTable`. Lý do: Python sở hữu RAG, bảng này chỉ là schema chết gây hiểu nhầm "backend có vector store".
- **Phương án B: giữ + document** nếu có kế hoạch chuyển RAG về .NET (hiện chưa có).

**Rủi ro:** migration drop bảng → kiểm tra prod có dữ liệu không (hiện không có đường ghi nên gần như trống). Low–Medium. **Gate:** `dotnet build` + `dotnet ef database update` trên scratch DB.

### 1.3 ⚠️ `antigravity-awesome-skills/` — thư mục untracked ở repo root

- `git status`: `?? antigravity-awesome-skills/`. Không thuộc dự án (vendored skills).

**Việc cần làm:** thêm vào `.gitignore` **hoặc** xóa. **FLAG:** untracked = có thể do owner cố ý để cục bộ → **xác nhận với owner trước khi xóa**. Rủi ro: Low (không ảnh hưởng build).

---

## 2. THIẾU — Cần Thêm (đã verify)

### 2.1 Chat persistence: in-memory → DB

- `ChatStore` đăng ký singleton in-memory: `backend/src/RestaurantQrAiOrdering.Api/Chat/ChatApiRegistration.cs:7` (`AddSingleton<IChatStore, ChatStore>()`).
- Entity + DbSet **đã tồn tại nhưng không dùng**: `DbSet<ChatSession>` / `DbSet<ChatMessage>` tại `RestaurantDbContext.cs:36-37`.
- **Hệ quả:** lịch sử chat mất khi restart process; `GET /api/chat/sessions/{id}/messages` không bền vững.

**Việc cần làm:** thêm `DbChatStore : IChatStore` ghi/đọc qua EF (giống mẫu `DbUserStore`), đổi đăng ký sang scoped/`DbChatStore`. Không cần migration (bảng đã map).

**Rủi ro:** Medium (đổi vòng đời store, transaction). **Gate:** `dotnet test` + smoke test chat flow.

### 2.2 Test cho AI service

- Hiện chỉ có `ai-service/.../test_assistant.py` (~45 LOC). Thiếu test cho retriever (BM25), guardrails (5 input flag + 2 system flag), và `output_parser` (clamp qty 1..20, ép `requiresCustomerConfirmation=true`).

**Việc cần làm:** bổ sung unit test cho `retriever`, `guardrails`, `output_parser`. **Rủi ro:** Low (additive). **Gate:** `pytest`.

### 2.3 (Tùy chọn) Job quét TableSession hết hạn

- Hiện TTL 4h được enforce **lazy** khi `ResolveTableSession` (đóng/mở lại session khi có request). Chưa có background sweep đóng session "mồ côi" khi không còn traffic.

**Việc cần làm (nice-to-have):** hosted service quét định kỳ đóng session quá hạn. **Ưu tiên thấp** — lazy check đã đủ cho nghiệp vụ hiện tại.

---

## 3. KHÔNG Phải Vấn Đề (đã verify — đừng đụng)

Danh sách này để tránh "refactor nhầm" thứ đang chạy đúng:

| Nghi ngờ ban đầu | Thực tế (verified) |
| --- | --- |
| `RestaurantDataStore` là dead code | **Live** — dùng bởi `ChatAiProvider` (`ChatAiProvider.cs:362,365`), đăng ký `MenuTableApiRegistration.cs:10`. |
| `--cmc-brown` không định nghĩa | **Có** — `tokens.css:110` → `var(--color-ink)`. |
| Frontend legacy entry còn sót | **Đã xóa** (main.tsx/App.tsx/index.html/vite.config.ts cũ). |
| Thiếu `.env.example` | **Có** — backend/frontend/deploy đều có. |
| Thiếu OpenAPI | **Có** — `AddOpenApi()` + `MapOpenApi()` (Development). |
| Docs mâu thuẫn code | **Đã sửa session này** — `SYSTEM_ANALYSIS_DESIGN.md` (mới) + drift-fix `API_CONTRACT.md` / `PROJECT_CONTEXT.md` / `BA_SA_SYSTEM_DESIGN.md`. |

---

## 4. Trình Tự PR Đề Xuất

| PR | Phạm vi | Rủi ro | Gate xanh |
| --- | --- | --- | --- |
| **R1** | 1.1 — Dọn Delivery/Pickup drift frontend (11 file) | Med | `typecheck` + `vitest` + build 4 app |
| **R2** | 2.1 — `DbChatStore` (chat bền vững) | Med | `dotnet test` + smoke chat |
| **R3** | 1.2 — Bỏ `KnowledgeEntry` (sau khi chốt A/B) | Low–Med | `dotnet build` + `ef database update` scratch |
| **R4** | 2.2 — Test AI service | Low | `pytest` |
| **H** | 1.3 — Xử lý `antigravity-awesome-skills/` (sau khi owner xác nhận) | Low | — |

**Lý do thứ tự:** R1 tự chứa và mở khóa "type = sự thật" cho UI rebuild → làm trước. R4 additive, chèn lúc nào cũng được. R2/R3 là migration/backend, làm tuần tự từng cái. H chờ owner.

---

## 5. Quyết Định Cần Chốt Trước Khi Execute

1. **`KnowledgeEntry`**: bỏ (A) hay giữ + document (B)? → khuyến nghị **A**.
2. **`antigravity-awesome-skills/`**: gitignore hay xóa? → cần owner xác nhận (untracked, có thể cố ý).

---

## 6. Ngoài Phạm Vi Bản Refactor Này

- **UI rebuild toàn diện** (customer/staff/kitchen/admin) — đã có kế hoạch riêng, không gộp vào đây.
- **Backend business hardening (P0–P3)** — đã hoàn tất và merge (`develop`). Không lặp lại.
