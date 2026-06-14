# Kế Hoạch Nâng Cấp Dự Án CMC Restaurant

## 1. Quyết Định Chốt

Dự án sẽ chuyển sang hướng **backend-first**:

- Tạm dừng cải thiện giao diện cũ.
- Không tiếp tục vá các màn hình đang dùng mock/localStorage nếu chưa bám backend thật.
- Hoàn thiện backend nghiệp vụ trước.
- Sau khi backend và API ổn định mới thiết kế lại giao diện theo logic thật.
- UI production không hiển thị JSON payload, API sample, debug data hoặc nội dung kỹ thuật cho khách hàng.

Kiến trúc chốt:

```text
Frontend mới
  -> Backend Modular Monolith
       -> PostgreSQL
       -> AI Service riêng
            -> RAG
            -> 9router
            -> Gemini/LLM
```

Backend chính dùng **Modular Monolith**. AI dùng **một service riêng bằng Python**.

## 2. Mục Tiêu Nâng Cấp

Mục tiêu là biến dự án từ trạng thái **MVP nhiều mock/in-memory** thành **hệ thống có backend thật, dữ liệu thật và giao diện bám nghiệp vụ thật**.

Các mục tiêu chính:

- Có PostgreSQL thật thay cho in-memory store.
- Có lifecycle đơn hàng rõ ràng.
- Có payment module hỗ trợ COD và VietQR.
- Có luồng bếp và nhân viên thật.
- Có AI/RAG service riêng, backend chỉ đóng vai trò tích hợp.
- Có API contract ổn định để frontend bám theo.
- Có UI mới không lệch logic backend.
- Có DevOps đủ để deploy staging/production.

## 3. Phạm Vi Backend Modular Monolith

Cấu trúc backend mục tiêu:

```text
backend/
  src/
    CmcRestaurant.Api/
      Program.cs
      Modules/
        Auth/
        Users/
        Menu/
        Tables/
        Orders/
        Payments/
        Kitchen/
        Admin/
        Realtime/
        Ai/
        Reporting/
      Shared/
        Domain/
        Application/
        Infrastructure/
        Errors/
        Security/
      Data/
        RestaurantDbContext.cs
        Migrations/
```

Module cần có:

| Module | Trách nhiệm |
|---|---|
| Auth | Đăng nhập, JWT, role-based access |
| Users | Quản lý người dùng, nhân viên, vai trò |
| Menu | Danh mục, món ăn, giá, trạng thái còn/hết |
| Tables | Bàn, mã QR, table session |
| Orders | Tạo đơn, trạng thái đơn, trạng thái món |
| Payments | COD, VietQR, payment intent, xác nhận thanh toán |
| Kitchen | Bếp nhận món, cập nhật trạng thái chế biến |
| Admin | Quản trị menu, đơn, bàn, nhân viên |
| Realtime | SignalR/order tracking |
| Ai | Tích hợp AI service, validate SuggestedCartAction |
| Reporting | Báo cáo cơ bản |

## 4. AI Service Riêng

AI không nhét vào backend chính.

Cấu trúc giữ theo hướng:

```text
ai/
  app/
    main.py
    rag/
    clients/
      nine_router.py
    services/
    schemas.py
  knowledge-base/
  evaluation/
  tests/
```

Vai trò AI service:

- Nhận request từ backend.
- Truy xuất knowledge base bằng RAG.
- Gọi 9router/Gemini.
- Trả về câu trả lời và SuggestedCartAction.
- Không tự tạo đơn.
- Không tự thêm món vào giỏ.
- Không tự thanh toán.

Backend chịu trách nhiệm:

- Gửi context cần thiết sang AI service.
- Validate response từ AI.
- Chỉ cho phép khách xác nhận thủ công nếu muốn thêm món.

## 5. Payment Chốt

Không làm VNPay/MoMo ngay nếu chưa có merchant/sandbox đầy đủ.

Thứ tự triển khai:

1. COD / Pay at counter.
2. VietQR manual confirmation.
3. VietQR auto confirmation qua provider như PayOS/Casso/Sepay nếu có điều kiện.
4. VNPay/MoMo ở giai đoạn sau.

Payment module cần có:

- `PaymentIntent`
- `PaymentStatus`
- `PaymentMethod`
- API tạo payment intent.
- API xem trạng thái payment.
- API nhân viên xác nhận thanh toán thủ công.
- Thiết kế sẵn webhook endpoint cho provider.

Quy tắc bắt buộc:

> Đơn online không được gửi sang bếp nếu chưa `Paid` hoặc chưa được nhân viên xác nhận COD/VietQR.

## 6. PostgreSQL Chốt

PostgreSQL là bắt buộc trong giai đoạn nâng cấp backend.

Việc cần làm:

- Thêm EF Core/Npgsql.
- Tạo `RestaurantDbContext`.
- Tạo migration ban đầu.
- Chuyển `RestaurantDataStore`, `OrderStore`, `ChatStore`, `UserStore` sang database-backed implementation.
- Thêm PostgreSQL service vào `deploy/docker-compose.yml`.
- Thêm `DATABASE_URL` hoặc connection string vào env.
- Cập nhật test để chạy với test database hoặc provider phù hợp.

Entity chính:

- User
- Role
- Category
- MenuItem
- RestaurantTable
- TableSession
- Order
- OrderItem
- PaymentIntent
- PaymentEvent
- ChatSession
- ChatMessage
- AiSuggestion
- AuditLog

## 7. Frontend Chốt

Giao diện cũ không tiếp tục làm nền chính nếu còn lệch backend.

Nguyên tắc:

- UI mới phải bám API thật.
- Không show API payload/debug JSON trên UI khách hàng.
- Mock chỉ được dùng trong dev mode hoặc story/demo riêng.
- Customer flow phải đơn giản, mobile-first.
- Admin/staff/kitchen UI phải ưu tiên đúng nghiệp vụ hơn trang trí.

Các màn hình cần làm lại sau khi backend ổn:

| Nhóm | Màn hình |
|---|---|
| Customer | Home/Menu, Cart, Checkout, Payment, Order Tracking, AI Chat |
| Staff | Xác nhận COD/VietQR, xử lý pickup/delivery |
| Kitchen | Bảng món cần chế biến, cập nhật item status |
| Admin | Menu, bàn QR, nhân viên, đơn hàng, báo cáo |
| Auth | Login nội bộ cho Manager/CounterStaff/KitchenStaff |

## 8. Lộ Trình Thực Hiện

### Phase 1: Backend Foundation

- Chuẩn hóa module structure.
- Thêm PostgreSQL + EF Core/Npgsql.
- Migration ban đầu.
- Auth + role thật.
- Seed data cơ bản.
- Health check database.

Kết quả:

- Backend có database thật.
- Test backend vẫn pass.
- Docker Compose có PostgreSQL.

### Phase 2: Core Restaurant Workflow

- Menu/category CRUD database-backed.
- Table/QR/table session.
- Order create/read/update.
- Order item status.
- Kitchen ticket flow.
- SignalR order updates.

Kết quả:

- Khách tạo đơn thật.
- Bếp nhận món thật.
- Trạng thái đơn/món lưu database.

### Phase 3: Payment

- PaymentIntent.
- COD confirmation.
- VietQR manual confirmation.
- Payment status mapping với order status.
- Audit log cho xác nhận thanh toán.

Kết quả:

- Đơn chưa thanh toán không đi bếp.
- Nhân viên xác nhận thanh toán được.
- Có nền để tích hợp webhook sau.

### Phase 4: AI Integration

- Backend gọi Python AI service.
- Chuẩn hóa request/response.
- Validate SuggestedCartAction.
- Fallback khi AI lỗi.
- Test các guardrail quan trọng.

Kết quả:

- AI gợi ý món dựa RAG.
- AI không can thiệp trực tiếp vào order/payment.

### Phase 5: Frontend Rebuild

- Bỏ/ẩn UI cũ lệch logic.
- Viết lại service layer theo API thật.
- Làm customer flow trước.
- Làm staff/kitchen/admin sau.
- Loại bỏ debug payload khỏi UI thật.

Kết quả:

- UI bám backend.
- Flow demo trọn vẹn từ khách đến bếp.

### Phase 6: DevOps Production Readiness

- Cập nhật Docker Compose.
- Nginx config.
- Env/secrets.
- Backup PostgreSQL.
- Smoke test deploy.
- Monitoring cơ bản.
- Rollback script.

Kết quả:

- Có thể deploy staging/production ổn định.

## 9. Thứ Tự Ưu Tiên Issue

1. PostgreSQL + EF Core foundation.
2. Auth/User/Role database-backed.
3. Menu/Category database-backed.
4. Table/QR/TableSession.
5. Order lifecycle.
6. Kitchen workflow.
7. Payment COD + VietQR manual.
8. AI service integration cleanup.
9. API contract freeze.
10. Frontend service layer rebuild.
11. Customer UI rebuild.
12. Staff/Kitchen/Admin UI rebuild.
13. DevOps production hardening.
14. E2E smoke tests.

## 10. Tiêu Chí Chốt Hoàn Thành

Dự án được xem là nâng cấp thành công khi:

- Backend không còn phụ thuộc in-memory store cho nghiệp vụ chính.
- PostgreSQL lưu menu, bàn, user, order, payment, chat/audit quan trọng.
- Khách đặt món được qua API thật.
- Payment rule hoạt động đúng.
- Bếp chỉ nhận đơn hợp lệ.
- AI có thể gợi ý món nhưng không tự sửa order.
- Frontend không còn show API/debug payload trong UI thật.
- Build/test CI pass.
- Docker Compose deploy được với backend, frontend, AI service, PostgreSQL.

