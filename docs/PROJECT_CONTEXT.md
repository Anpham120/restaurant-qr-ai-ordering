# Ngữ Cảnh Dự Án

## 1. Đề Tài

Tên dự án: **Restaurant QR AI Ordering**.

Mục tiêu là xây dựng hệ thống đặt đồ ăn và quản lý nhà hàng tích hợp chatbot AI. Hệ thống cần thể hiện được nghiệp vụ nhà hàng thực tế: khách đặt món, nhà hàng tiếp nhận, bếp cập nhật trạng thái từng món, khách theo dõi realtime, admin quản lý menu/bàn/đơn hàng và chatbot AI hỗ trợ tư vấn món.

## 2. Actors

### Customer / Guest

- Xem menu.
- Quét QR tại bàn để đặt món dine-in.
- Đặt món online theo hình thức pickup hoặc delivery mock.
- Hỏi chatbot AI để được tư vấn món.
- Theo dõi trạng thái đơn và từng món theo thời gian thực.
- Hủy đơn khi đơn chưa chuyển sang trạng thái `Preparing`.

### Staff

- Xác nhận đơn mới.
- Phục vụ món tại bàn.
- Xử lý pickup hoặc delivery mock.
- Xác nhận thanh toán COD/mock online.
- Hoàn tất đơn.

### Kitchen

- Xem kitchen board.
- Cập nhật trạng thái từng món: `Pending`, `Preparing`, `Ready`, `Served`, `Cancelled`.
- Báo cho Staff khi món đã sẵn sàng.

### Admin

- Quản lý danh mục và món ăn.
- Bật/tắt trạng thái còn món.
- Quản lý bàn và link/QR của bàn.
- Xem đơn hàng.
- Xem báo cáo cơ bản: doanh thu ngày, món bán chạy.

### AI Chatbot

- Sử dụng external LLM API.
- Sử dụng RAG trên menu/FAQ để trả lời.
- Tư vấn món theo khẩu vị, ngân sách, số người và tình trạng còn hàng.
- Đề xuất thêm món vào giỏ, nhưng khách phải xác nhận.
- Không tự đặt đơn, không tự thanh toán, không bịa món hoặc giá.

## 3. Luồng Nghiệp Vụ Chính

### QR Dine-in Flow

1. Admin tạo hoặc quản lý bàn, ví dụ `T05`.
2. Hệ thống sinh link QR cho bàn: `/table/T05`.
3. Khách quét QR bằng điện thoại.
4. Frontend mở menu với context `tableCode = T05`.
5. Khách xem menu, hỏi chatbot, thêm món vào giỏ.
6. Khách xác nhận đặt món.
7. Backend tạo đơn `OrderType = DineIn`, `tableCode = T05`.
8. Staff xác nhận đơn.
9. Kitchen nhận đơn trên kitchen board.
10. Kitchen cập nhật từng món.
11. Customer tracking screen nhận realtime event và cập nhật trạng thái.
12. Staff phục vụ, thu tiền và hoàn tất đơn.

### Online Pickup / Delivery Mock Flow

1. Khách vào `/menu`.
2. Khách chọn món và vào checkout.
3. Khách chọn `Pickup` hoặc `DeliveryMock`.
4. Nếu delivery mock, khách nhập tên, số điện thoại và địa chỉ.
5. Staff xác nhận đơn.
6. Kitchen chuẩn bị món.
7. Pickup: khách nhận tại quán.
8. DeliveryMock: Staff đánh dấu `Delivering`, sau đó `Delivered`.
9. Staff/Admin xác nhận thanh toán và hoàn tất đơn.

### Restaurant Management Flow

1. Admin đăng nhập.
2. Admin quản lý category và menu item.
3. Admin bật/tắt `isAvailable` của món.
4. Admin quản lý bàn và QR link.
5. Staff theo dõi đơn mới và xác nhận đơn.
6. Kitchen cập nhật từng món.
7. Staff phục vụ/giao món và xác nhận thanh toán.
8. Admin xem doanh thu ngày và món bán chạy.

### AI Chatbot Flow

1. Khách mở chatbot trong menu hoặc trang chat.
2. Khách hỏi về món ăn, giá, khẩu vị, món chay, món cay hoặc gợi ý cho nhóm.
3. Backend lấy menu/FAQ liên quan bằng RAG.
4. LLM trả lời dựa trên dữ liệu đã truy xuất.
5. Nếu có gợi ý thêm vào giỏ, chatbot trả về `SuggestedCartAction`.
6. Frontend hiển thị nút Confirm/Dismiss.
7. Chỉ khi khách bấm Confirm thì món mới được thêm vào giỏ.

## 4. Trạng Thái Quan Trọng

Order status:

- `Draft`
- `Placed`
- `Confirmed`
- `Preparing`
- `Ready`
- `Served`
- `Delivering`
- `Delivered`
- `Completed`
- `Cancelled`

Order item status:

- `Pending`
- `Preparing`
- `Ready`
- `Served`
- `Cancelled`

Order type:

- `DineIn`
- `Pickup`
- `DeliveryMock`

Payment method:

- `COD`
- `VietQR`

Payment status:

- `Unpaid`
- `Pending`
- `Paid`
- `Confirmed`
- `Failed`
- `Cancelled`

## 5. Phạm Vi Phiên Bản 1

Trong phạm vi:

- QR table ordering.
- Customer menu/cart/checkout.
- Customer realtime order tracking.
- Admin menu/order/table management.
- Staff order handling.
- Kitchen board.
- Chatbot AI qua LLM API + RAG.
- Docker/VPS deployment guide.

Ngoài phạm vi v1:

- Cổng thanh toán thật.
- Giao hàng thật hoặc tích hợp shipper.
- Đặt bàn trước.
- Quản lý tồn kho nguyên liệu.
- Train custom AI model.
- Marketplace nhiều nhà hàng.

## 6. Chuẩn Điều Phối Tuần 2

Issue #10 khóa phần tài liệu điều phối cho Week 2. Đây là chuẩn để các member frontend, backend, admin, chatbot và testing cùng đối chiếu trước khi implement tiếp.

- Contract chính: `docs/API_CONTRACT.md`.
- Test/integration checklist: `docs/TEST_PLAN.md`.
- Seed table demo: `T01` đến `T08`, route QR tương ứng `/table/T01` đến `/table/T08`.
- Seed menu demo: ID chuẩn `m_001` đến `m_012`, có món available và unavailable để test admin availability, customer cart và chatbot suggestion.
- Shared status names phải dùng đúng enum trong contract: `OrderType`, `OrderStatus`, `OrderItemStatus`, `PaymentMethod`, `PaymentStatus`, `UserRole`, `ChatRole`.
- Nếu frontend mock, backend DTO hoặc chatbot data khác contract, member phải ghi rõ drift trong PR và cập nhật tài liệu trước khi đổi shape.
- Review open PRs ngày `2026-06-05` cho issue #10 ghi nhận không có PR mở tại thời điểm kiểm tra.
