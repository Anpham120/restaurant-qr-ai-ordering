# Test Plan Tuần 2

Tài liệu này ghi checklist tích hợp thủ công cho issue #10. Phạm vi là review contract, seed data plan và scenario test; không implement feature code.

## 1. Nguồn Kiểm Tra

- Issue: [#10](https://github.com/Anpham120/restaurant-qr-ai-ordering/issues/10).
- Branch docs: `issue-10/anpham120-api-contract-seed-integration`.
- API contract: [docs/API_CONTRACT.md](API_CONTRACT.md).
- Seed data chuẩn: `T01` đến `T08`, menu item `m_001` đến `m_012`.
- Open PR review ngày `2026-06-05`: `gh pr list --repo Anpham120/restaurant-qr-ai-ordering --state open --json number,title,headRefName,baseRefName,author,url,updatedAt` trả `[]`; không có PR mở tại thời điểm kiểm tra.

## 2. Drift / Risk Cần Theo Dõi

Các điểm dưới đây được ghi nhận để member xử lý trong issue code tương ứng, không sửa trong issue #10:

- Frontend admin mock đang dùng table code `T-05`; contract chuẩn là `T05`.
- Frontend admin mock đang dùng `paymentStatus: "Pending"`; contract chuẩn là `Unpaid`, `Paid`, `Failed`, `Cancelled`.
- Frontend menu mock đang dùng menu ID `mi-001`; contract/backend DTO chuẩn dùng `m_001`.
- Frontend `MenuItem` type hiện thiếu `categoryId`; contract public menu cần `categoryId` để admin/chatbot đồng bộ.
- Backend hiện chưa có order/chat/realtime endpoints hoàn chỉnh; các phần này trong contract là mục tiêu triển khai tiếp, không phải feature được implement bởi issue #10.

## 3. Scenario QR Customer Order

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
6. Frontend gửi `POST /api/orders` với `orderType: "DineIn"`, `tableCode: "T05"`, `paymentMethod: "COD"`, `deliveryInfo: null`.
7. Backend trả `201 Created`, `status: "Placed"`, `paymentStatus: "Unpaid"`, item status `Pending`.
8. Frontend mở `/orders/{orderCode}` và gọi `GET /api/orders/{orderCode}`.

Kỳ vọng:

- Không có field dùng dạng `T-05`.
- Không có món `isAvailable: false` trong payload tạo đơn.
- UI tracking hiển thị order status và item status theo enum trong contract.
- Nếu thử `tableCode = ABC`, backend trả `400 TABLE_CODE_INVALID`.

## 4. Scenario Online Pickup

Mục tiêu: khách đặt món mang đi không cần QR.

Tiền điều kiện:

- Menu public có item available.
- Frontend route `/menu` không có table context.

Các bước:

1. Mở `/menu`.
2. Frontend gọi `GET /api/menu`.
3. Khách chọn `Pickup`.
4. Frontend gửi `POST /api/orders` với `orderType: "Pickup"`, `tableCode: null`, `paymentMethod: "COD"`, `deliveryInfo: null`.
5. Backend trả order `Placed`.
6. Staff/admin kiểm tra đơn trong màn vận hành khi endpoint tương ứng được triển khai.

Kỳ vọng:

- Backend không yêu cầu `tableCode` cho `Pickup`.
- Response không dùng `paymentStatus: "Pending"`.
- `orderCode` dùng dạng `ORD-####`.

## 5. Scenario Delivery Mock

Mục tiêu: mô phỏng giao hàng nội bộ, không tích hợp shipper thật.

Tiền điều kiện:

- Menu public có item available.
- Customer nhập đủ tên, số điện thoại và địa chỉ.

Các bước:

1. Mở `/menu`.
2. Khách chọn `DeliveryMock`.
3. Frontend nhập `recipientName`, `phoneNumber`, `address`, optional `note`.
4. Frontend gửi `POST /api/orders` với `orderType: "DeliveryMock"` và `deliveryInfo` đầy đủ.
5. Backend trả order `Placed`.
6. Staff cập nhật trạng thái vận hành theo luồng `Confirmed` -> `Preparing` -> `Ready` -> `Delivering` -> `Delivered` -> `Completed` khi feature code có endpoint.

Kỳ vọng:

- Thiếu `deliveryInfo.address` trả `400 DELIVERY_INFO_REQUIRED`.
- Không gọi cổng giao hàng/thanh toán thật.
- Customer tracking không hiển thị bàn cho order delivery.

## 6. Scenario Admin Availability Change

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

## 7. Verification Cho Issue #10

Do issue #10 là docs-only, verification bắt buộc:

- `git diff --check`.
- Kiểm tra file tồn tại: `docs/API_CONTRACT.md`, `docs/PROJECT_CONTEXT.md`, `docs/TEST_PLAN.md`, `docs/reports/week-2-report.md`.
- Kiểm tra link nội bộ trong docs trỏ tới file tồn tại.
- Review open PRs cho contract drift.

Verification nên chạy nếu môi trường có đủ dependency:

- Frontend: `npm run build` trong `frontend`.
- Backend: `dotnet test RestaurantQrAiOrdering.sln` trong `backend`.

Nếu build/test không chạy được, report phải ghi rõ lỗi môi trường hoặc dependency thay vì đánh dấu pass.
