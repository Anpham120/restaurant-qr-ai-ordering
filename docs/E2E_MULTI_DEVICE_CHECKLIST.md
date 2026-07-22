# E2E multi-device checklist

## Mục tiêu

Chứng minh hệ thống chạy qua backend/database thật giữa nhiều thiết bị hoặc nhiều browser profile, không dựa vào `localStorage`, mock data, hoặc một tab duy nhất.

## Môi trường

- Local: backend API + PostgreSQL + frontend trỏ về `VITE_API_BASE_URL` thật.
- Staging: domain/subdomain staging trỏ về backend và database staging.
- Gemini API có thể bật thật; nếu provider lỗi, chatbot phải fallback an toàn và không tự sửa giỏ hàng.

## Kịch bản smoke bắt buộc

1. Customer device mở route QR/table hoặc session khách, chọn món, gửi đơn.
2. Kitchen hoặc staff device khác đăng nhập role vận hành, gọi danh sách đơn từ backend và thấy đơn mới.
3. Kitchen cập nhật trạng thái món sang `Preparing` hoặc `Ready`.
4. Customer tracking device refresh hoặc theo dõi đơn và thấy trạng thái mới từ backend.
5. Customer tạo thanh toán VietQR hoặc chọn COD.
6. Staff xác nhận thanh toán bằng endpoint/hành động vận hành; customer tracking thấy `Confirmed`.
7. Customer dùng AI chat để hỏi gợi ý món. AI chỉ trả về đề xuất hoặc fallback, mọi `SuggestedCartAction` phải yêu cầu khách xác nhận.

## Ops deep-link smoke (manual)

1. **Payment toast → counter filter:** Khách yêu cầu thanh toán → staff thấy toast → click mở `/counter?tab=payments&table=…` → danh sách lọc đúng bàn.
2. **Floor drawer → kanban:** Từ sơ đồ bàn, mở link kanban `?table=` → đơn của bàn được highlight trên board.

## Script/test tự động trong repo

Chạy test tích hợp nhiều client:

```bash
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj --filter MultiDeviceE2ETests --nologo
```

Test này tạo nhiều `HttpClient` độc lập để mô phỏng customer, kitchen, staff và tracking device. Dữ liệu đi qua API/backend store chung, không dùng `localStorage` hay mock frontend.

## Evidence khi đóng issue

- Log test `MultiDeviceE2ETests` pass.
- Log backend test tổng pass.
- Screenshot hoặc video ngắn nếu chạy manual trên local/staging:
  - màn hình khách gửi đơn;
  - màn hình bếp/staff thấy cùng order code;
  - màn hình tracking thấy trạng thái/payment mới;
  - màn hình AI chat có fallback hoặc suggested action yêu cầu xác nhận.
