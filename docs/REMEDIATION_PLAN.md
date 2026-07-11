# Kế Hoạch Khắc Phục Toàn Bộ — CMC Restaurant QR AI Ordering

> Mục tiêu: xử lý dứt điểm các vấn đề bảo mật, kiến trúc, CI/CD và vệ sinh repo đã phát hiện.
> Nguyên tắc: chia thành PR nhỏ, CI xanh trước khi merge, ưu tiên bảo mật trước.

Thứ tự đề xuất: **Phase 1 → 2 → 3 (gộp thành 1 PR bảo mật)** → 4 → 5 → 6.

---

## Phase 0 — Containment (làm ngay, ~30 phút)

Vì `admin@restaurant.local / Admin@123` đã public trên repo → coi tài khoản admin production hiện tại là **đã lộ**.

- [ ] Tạo mới `JWT_SIGNING_KEY` và `PRODUCTION_POSTGRES_PASSWORD` (random dài) → lưu vào GitHub Secrets, KHÔNG dùng lại giá trị dev đã commit.
- [ ] Sau khi Phase 1 deploy: buộc đổi mật khẩu mọi tài khoản vận hành.
- [ ] Xác nhận secret prod/staging trên GitHub đã set đủ (deploy script yêu cầu: `JWT_SIGNING_KEY`, `*_POSTGRES_PASSWORD`, `AI_API_KEY`, SSH...).

---

## Phase 1 — Diệt backdoor mật khẩu 🔴 (Critical)

> ✅ **Đã triển khai** trên `fix/security-remediation`. Phát hiện quan trọng: backdoor nằm ở **HAI** nơi, không chỉ Program.cs:
> - **Program.cs**: tách seed khỏi flag `RUN_DB_MIGRATIONS_ON_STARTUP`; bootstrap admin create-if-missing từ `BOOTSTRAP_ADMIN_EMAIL/PASSWORD` (không bao giờ reset); demo gated bằng `SEED_DEMO_USERS` (create-if-missing, không reset password).
> - **`Data/RestaurantDbContext.cs`**: bỏ `HasData` 4 user + 4 hằng password-hash đã commit.
> - **Migration mới `20260619074121_RemoveSeededUsers`**: `DeleteData` 4 row seed khỏi DB đã tồn tại. Tiện thể reconcile drift cũ (drop cột mồ côi `orders.mock_delivery_fee` — property đã bị xoá khỏi entity trước đó mà chưa có migration).
> - `User` entity **không có** field `IsActive` → snippet minh hoạ bên dưới (có `IsActive`) là sai; code thật bỏ field này. `UserRole.Admin` là `const string`, hợp lệ.
> - **`deploy/docker-compose.yml`**: thêm passthrough `BOOTSTRAP_ADMIN_EMAIL/PASSWORD` + `SEED_DEMO_USERS` cho service `api` (nếu không các env mới sẽ không tới container).

**File:** `backend/src/RestaurantQrAiOrdering.Api/Program.cs` (khối seed ~dòng 80–110)

**Vấn đề lịch sử:** seed cố định từng reset hash khi deploy cũ dùng startup migration; hiện bootstrap/demo seed đã tách khỏi migration và được kiểm soát bằng biến môi trường.

**Cách sửa:**
1. Tách seed khỏi flag migration.
2. Demo accounts chỉ chạy khi `SEED_DEMO_USERS=true` (mặc định `false`; chỉ bật ở local/staging).
3. Admin production: bootstrap **create-if-missing** từ env, KHÔNG bao giờ ghi đè user đã tồn tại.

```csharp
// Bootstrap admin: chỉ tạo nếu chưa có, không reset
var adminEmail = builder.Configuration["BOOTSTRAP_ADMIN_EMAIL"];
var adminPassword = builder.Configuration["BOOTSTRAP_ADMIN_PASSWORD"];
if (!string.IsNullOrWhiteSpace(adminEmail) && !string.IsNullOrWhiteSpace(adminPassword))
{
    var exists = await dbContext.Users.AnyAsync(u => u.Email == adminEmail);
    if (!exists)
    {
        dbContext.Users.Add(new User {
            Email = adminEmail,
            FullName = "System Admin",
            Role = UserRole.Admin,
            PasswordHash = hasher.HashPassword(adminPassword),
            IsActive = true
        });
        await dbContext.SaveChangesAsync();
    }
}

// Demo users: chỉ khi bật flag, vẫn create-if-missing (không reset)
if (builder.Configuration.GetValue<bool>("SEED_DEMO_USERS"))
{
    // ... tạo các tài khoản demo nếu chưa tồn tại, KHÔNG ghi đè PasswordHash
}
```

4. Cập nhật env:
   - `deploy/env/production.example.env`: bỏ phụ thuộc demo, thêm `SEED_DEMO_USERS=false`, `BOOTSTRAP_ADMIN_EMAIL=`, `BOOTSTRAP_ADMIN_PASSWORD=` (giá trị thật để ở GitHub Secrets).
   - `staging.example.env`: có thể `SEED_DEMO_USERS=true` cho tiện demo.

**Verify:**
- [x] `dotnet build` (Release) + `dotnet test` xanh — **50/50 pass**, giữ `AuthEndpointTests`/`MenuEndpointTests` cũ (chúng dùng seed riêng của test factory, không phụ thuộc HasData prod).
- [ ] (Hoãn) Test startup create-if-missing / `SEED_DEMO_USERS=false`: cần Postgres integration harness vì khối seed chỉ chạy khi có connection string thật — test factory dùng in-memory nên bỏ qua khối này. Đề xuất tách seed thành service inject được rồi unit-test.

---

## Phase 2 — Bỏ secret khỏi config tracked 🔴

> ✅ **Đã triển khai.** `appsettings.json` `Jwt.SigningKey` → `""`; xoá `ConnectionStrings` giả khỏi `appsettings.Production.json` + `appsettings.Staging.json`. Vì `appsettings.Development.json` **không có** section `Jwt` (kế thừa base), đã thêm `Jwt.SigningKey` dev-only vào Development.json để `dotnet run` local không chạy với HMAC key rỗng. Key này chỉ load khi `ASPNETCORE_ENVIRONMENT=Development` → không bao giờ vào prod/staging.

**Files:**
- `backend/src/RestaurantQrAiOrdering.Api/appsettings.json` — `Jwt.SigningKey` → `""` (env `Jwt__SigningKey` đã cấp ở compose).
- `appsettings.Production.json` / `appsettings.Staging.json` — **xóa** chuỗi `ConnectionStrings` giả `${DB_HOST}...` (`.NET không expand `${}`; env `ConnectionStrings__DefaultConnection` mới là nguồn thật). Chỉ giữ `Logging` + `AllowedHosts`.
- `appsettings.Development.json` — giá trị local (`ChangeMe123!`, VietQR demo) chấp nhận được cho local; tùy chọn chuyển sang `dotnet user-secrets`.

**Lịch sử git:** key dev cũ vẫn nằm trong history. Vì đã rotate ở Phase 0, **không cần** `git filter-repo` (rewrite history ảnh hưởng cả team). Chấp nhận, coi key cũ là vô hiệu.

**Verify:**
- [ ] Backend boot bằng env override qua `deploy/docker-compose.yml` (chưa chạy — cần Docker; compose có `${JWT_SIGNING_KEY:?required}` nên thiếu key sẽ fail-fast, đúng mong muốn).
- [x] Integration tests xanh (50/50).

---

## Phase 3 — Migration & prod hardening 🟠

> ✅ **Đã triển khai:** deploy start PostgreSQL, chạy container `migrate --migrate-only`, rồi mới start API; `RUN_DB_MIGRATIONS_ON_STARTUP=false` mặc định. `AllowedHosts` production/staging đã giới hạn hostname API và loopback cho health check.

- [x] `RUN_DB_MIGRATIONS_ON_STARTUP` mặc định **false** cho production. Chạy migration thành bước deploy riêng qua container `migrate --migrate-only` trước khi `api` start.
  - File: `.github/workflows/deploy-production.yml:44`, `deploy-staging.yml:38`, `deploy/docker-compose.yml:32`.
- [x] `AllowedHosts: "*"` → hostname thật theo môi trường, kèm `localhost`/`127.0.0.1` cho health check.
- [ ] (Tùy chọn) thu hẹp CORS list localhost trong `Program.cs` cho production.

**Verify:** deploy script chạy migrate step; `/api/health` xanh sau deploy.

---

## Phase 4 — Gộp frontend, bỏ bản trùng 🟡

**Hiện trạng:** `frontend/apps/*-web` là entry chuẩn (build:all build chúng), import code qua `../../../src/...`. Bản legacy đã được xóa: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/index.html`, `frontend/vite.config.ts`, script `dev:legacy`/`build:legacy`.

**Option A (làm ngay, rủi ro thấp):**
- [x] Xóa: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/index.html`, `frontend/vite.config.ts`.
- [x] Bỏ script `dev:legacy`, `build:legacy` trong `frontend/package.json`.
- [x] Giữ `frontend/src/{pages,components,services,types,utils,mocks,styles.css}` làm code dùng chung cho apps.
- [x] Giữ `frontend/tsconfig.json` theo workspace hiện tại; typecheck/build bốn portal đã pass.

**Option B (refactor sau, sạch hơn):**
- [ ] Chuyển `src/{pages,components,services...}` vào `packages/` (đã có `shared-ui`), thay import `../../../src` bằng `@cmc/...`.

**Verify:** `npm run build` (cả 4 app) xanh, `npm test` xanh, e2e smoke (`frontend/e2e/portal-smoke.spec.ts`).

---

## Phase 5 — AI: nói đúng bản chất 🟡

`ai/app/rag/retriever.py` là **lexical retrieval** (token overlap + idf), không phải vector RAG.

- [ ] **Ngắn hạn:** sửa `README.md` + `docs/AI_RAG_ARCHITECTURE.md` ghi rõ "lexical retrieval", bỏ từ "vector/embeddings" nếu chưa có.
- [ ] **Dài hạn (tùy chọn):** thêm embeddings thật (API embeddings + cosine) nếu cần chất lượng.

---

## Phase 6 — Vệ sinh repo & CI 🟢

- [x] `coursework/` và scratch artifact không còn tracked.
- [x] `.github/workflows/ci.yml` chạy `npm test`, backend regression và AI guardrail tests.
- [ ] Dọn branch cũ: `merge/develop-into-main`, `fix/production-deploy-health`, các `codex/*` đã merge.
- [ ] Dọn file scratch local (đã gitignore): `commit_msg.txt`, `pr_*.txt`, `issue_comment.txt`, `tmp/`, `output/`, `site-demo/`.

---

## Tổng kết ưu tiên

| Phase | Vấn đề | Mức | Ước lượng |
|---|---|---|---|
| 0 | Rotate secret, coi admin lộ | 🔴 | 30p |
| 1 | Backdoor mật khẩu (Program.cs) | 🔴 | 2–3h |
| 2 | Secret trong appsettings tracked | 🔴 | 1h |
| 3 | Migrate-on-startup + AllowedHosts | 🟠 | 2h |
| 4 | Gộp frontend (Option A) | 🟡 | 1–2h |
| 5 | Sửa nhãn AI RAG | 🟡 | 30p |
| 6 | coursework + CI test + dọn branch | 🟢 | 1h |

**Gợi ý gói PR:** PR#1 = Phase 1+2+3 (security), PR#2 = Phase 4, PR#3 = Phase 5+6.
