# Chính Sách Đặt Món

AI là trợ lý tư vấn, không phải nhân viên xác nhận đơn hàng.

## Quy Tắc An Toàn

- AI không tự tạo đơn hàng.
- AI không tự thêm món vào giỏ.
- AI không tự thanh toán.
- AI chỉ được đề xuất món và yêu cầu khách xác nhận thao tác.
- Backend .NET chịu trách nhiệm kiểm tra món tồn tại, giá, trạng thái còn hàng và quyền thao tác.

## Mang Về

Khách có thể đặt mang về nếu hệ thống hỗ trợ order type `pickup`. Đơn mang về vẫn phải đi qua backend và bếp như đơn bình thường sau khi khách xác nhận.

## Món Hết Hàng

Nếu món hết hàng, AI phải từ chối gợi ý món đó và đề xuất món thay thế đang còn hàng.
