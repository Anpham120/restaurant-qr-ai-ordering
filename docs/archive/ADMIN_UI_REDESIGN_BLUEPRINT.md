# Blueprint Thiết Kế Lại Giao Diện Quản Lý Nhà Hàng

## Mục tiêu

Giao diện quản lý phải tối giản, dễ thao tác, nhưng bám đúng nghiệp vụ đang có trong backend. Không thêm màn hình trang trí hoặc tính năng demo không gọi API thật.

## Nguyên tắc thiết kế

- Mỗi màn hình có một nghiệp vụ chính.
- Mỗi nút tạo/sửa/xóa/đổi trạng thái phải gọi service thật và có trạng thái loading/error/success.
- Navigation chính chỉ giữ các module dùng hằng ngày.
- Module ít dùng chuyển vào nhóm hệ thống hoặc trang cấu hình.
- Admin, Staff, Kitchen dùng chung shell có đăng xuất rõ ràng.

## Palette và giao diện

| Token | Màu | Vai trò |
|---|---|---|
| `ops-ink` | `#17211b` | Text chính |
| `ops-paper` | `#fbfaf6` | Nền chính |
| `ops-line` | `#ded8cc` | Border |
| `ops-green` | `#2f6f4e` | Hành động chính |
| `ops-gold` | `#b88932` | Cảnh báo/điểm nhấn |
| `ops-danger` | `#b42318` | Xóa/hủy |

Phong cách: dashboard vận hành yên tĩnh, mật độ thông tin vừa phải, không hero marketing, không card lồng card.

## Navigation mục tiêu

### Admin

| Nhóm | Màn | Backend/service |
|---|---|---|
| Vận hành | Tổng quan | reports/orders/tables summary |
| Vận hành | Đơn hàng | `orders`, realtime hub |
| Vận hành | Phiên bàn | `tables`, `table-sessions` |
| Thực đơn | Món ăn | `menu` admin endpoints |
| Thực đơn | Danh mục | `categories` admin endpoints |
| Tài chính | Hóa đơn/Thanh toán | `payments`, `orders` |
| Khách hàng | Khuyến mãi | `promotions` |
| Khách hàng | Tích điểm | `loyalty` |
| Hệ thống | Người dùng | `users/auth` |

`Báo cáo` chỉ giữ nếu gọi dữ liệu backend thật. Nếu còn mock, đưa vào backlog.

### Staff

- Đơn đang phục vụ.
- Thu ngân/thanh toán.

### Kitchen

- Bảng bếp realtime.
- Cập nhật trạng thái món.

## Màn thực đơn admin

Mục tiêu: thêm/sửa/xóa món phải dùng được thật.

Luồng:

1. Load danh sách món từ backend.
2. Load danh mục từ backend.
3. Tạo món: validate tên, giá, danh mục, ảnh URL.
4. Sửa món: mở form cùng dữ liệu backend.
5. Đổi trạng thái còn/hết: optimistic update, rollback nếu API lỗi.
6. Xóa món: confirm, gọi API, reload danh sách.

Trạng thái bắt buộc:

- Loading skeleton.
- Empty state khi chưa có món.
- Error state có nút tải lại.
- Save state không cho bấm lặp.

## Màn phiên bàn và giỏ hàng

Mục tiêu: mọi order dine-in đi qua phiên bàn.

Luồng khách:

1. Quét QR.
2. Backend mở `TableSession`.
3. UI lưu `tableCode`, `qrToken`, `sessionId`.
4. Floating cart luôn hiển thị khi có món.
5. Checkout gửi `tableCode`, `qrToken`, `tableSessionId`.
6. Order xuất hiện ở Staff/Kitchen realtime.
7. Khi thanh toán và đóng phiên, backend xóa chat session của phiên đó.

## AI trong vận hành thật

AI chỉ có quyền:

- Tư vấn món.
- Giải thích thành phần/chính sách.
- Tạo `SuggestedCartAction`.

AI không có quyền:

- Tự tạo order.
- Tự thêm cart khi khách chưa xác nhận.
- Tự xác nhận thanh toán.
- Dùng memory của phiên bàn đã đóng.

## Checklist nghiệm thu

- Admin logout nhìn thấy trong mọi màn quản trị.
- Menu admin tạo/sửa/xóa/đổi trạng thái gọi backend thật.
- Customer AI không thêm cart nếu chưa có phiên bàn.
- Floating cart xuất hiện phía trên nội dung và kéo được.
- Checkout luôn gửi `tableSessionId`.
- Staff/Kitchen thấy đơn mới sau checkout.
- RAG benchmark có số liệu trước khi chọn cấu hình production.

