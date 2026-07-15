---
id: kb.policy.payment.v1
title: Phương Thức Thanh Toán
domain: payment
tags: [payment, vietqr, cash]
language: vi
source: restaurant_ops_manual
reviewed_by: restaurant_manager
reviewed_at: 2026-07-13
expires_at: 2027-01-13
safety_level: high
---

# Phương Thức Thanh Toán

## Tổng Quan

CMC Restaurant hỗ trợ 3 phương thức thanh toán chính. Tất cả đơn hàng được tính tổng tự động trên hệ thống, bao gồm mọi round gọi món trong cùng phiên bàn.

## VietQR (Khuyến Khích)

### Quy Trình VietQR

1. Khách nhấn "Tính tiền" trên giao diện web.
2. Hệ thống tạo mã VietQR với số tiền chính xác, mã đơn hàng trong nội dung chuyển khoản.
3. Khách mở ứng dụng ngân hàng, quét mã QR.
4. Xác nhận chuyển khoản trong app ngân hàng.
5. Hệ thống nhận webhook từ ngân hàng, tự cập nhật trạng thái "Đã thanh toán".
6. Phiên bàn đóng tự động sau thanh toán thành công.

### Thông Tin Tài Khoản

| Thông tin | Giá trị |
|---|---|
| Ngân hàng | Vietcombank |
| Chủ tài khoản | CONG TY TNHH CMC RESTAURANT |
| Số tài khoản | 1234567890 |
| Chi nhánh | Hồ Chí Minh |

### Lưu Ý VietQR

- Nội dung chuyển khoản được tự động điền bởi mã QR, khách **không cần sửa**.
- Nếu chuyển sai số tiền: gọi nhân viên để xử lý chênh lệch.
- Thời gian xác nhận: 5–30 giây sau khi chuyển thành công.
- Hỗ trợ tất cả ngân hàng liên kết VietQR (40+ ngân hàng).

## Tiền Mặt

### Quy Trình Tiền Mặt

1. Khách gọi nhân viên hoặc nhấn "Tính tiền bằng tiền mặt" trên giao diện.
2. Nhân viên in hóa đơn, mang đến bàn.
3. Khách trả tiền mặt cho nhân viên.
4. Nhân viên xác nhận thanh toán trên hệ thống POS.
5. Phiên bàn đóng.

### Lưu Ý Tiền Mặt

- Nhận tiền VNĐ, không nhận ngoại tệ.
- Thối tiền lẻ: nhà hàng luôn có sẵn.
- Hóa đơn in bao gồm chi tiết từng món, từng round.

## Thẻ Ngân Hàng (Visa / MasterCard / JCB)

### Quy Trình Thẻ

1. Gọi nhân viên yêu cầu thanh toán bằng thẻ.
2. Nhân viên mang máy POS đến bàn.
3. Khách quẹt/chạm/insert thẻ, nhập PIN nếu cần.
4. Nhận biên lai từ máy POS.
5. Nhân viên xác nhận trên hệ thống, phiên bàn đóng.

### Lưu Ý Thẻ

- Không phụ thu khi thanh toán bằng thẻ.
- Hỗ trợ: Visa, MasterCard, JCB, UnionPay.
- Thẻ nội địa (Napas): hỗ trợ.
- Không hỗ trợ trả góp.

## Chia Bill

- Hệ thống **không** hỗ trợ chia bill tự động.
- Nếu cần chia: gọi nhân viên, nhân viên sẽ tách hóa đơn thủ công.
- Có thể kết hợp nhiều phương thức (ví dụ: một phần VietQR, một phần tiền mặt).

## Hóa Đơn VAT

- Xuất hóa đơn VAT theo yêu cầu.
- Cung cấp: tên công ty, mã số thuế, địa chỉ, email nhận hóa đơn.
- Hóa đơn điện tử gửi qua email trong vòng 3 ngày làm việc.
- Yêu cầu xuất VAT trước khi thanh toán hoặc trong ngày.

## Voucher Và Mã Giảm Giá

| Loại | Cách dùng |
|---|---|
| Voucher giấy CMC Restaurant | Đưa nhân viên trước khi thanh toán |
| Voucher điện tử (email/SMS) | Nhập mã trên giao diện checkout |
| Mã giảm giá từ đối tác | Nhập mã trên giao diện checkout |

### Quy Định Voucher

- Mỗi đơn chỉ áp dụng **1 voucher**.
- Không áp dụng đồng thời với chương trình khuyến mãi khác.
- Voucher có ngày hết hạn, kiểm tra trước khi dùng.
- Voucher giảm giá % được áp dụng trên tổng đơn trước thuế.
- Voucher giảm giá cố định (ví dụ: 50.000đ) trừ trực tiếp vào tổng đơn.

## Xử Lý Sự Cố Thanh Toán

| Sự cố | Cách xử lý |
|---|---|
| VietQR không nhận được | Chờ 1 phút, kiểm tra app ngân hàng. Nếu đã trừ tiền → gọi nhân viên |
| Máy POS lỗi | Thử lại hoặc chuyển sang VietQR/tiền mặt |
| Chuyển sai số tiền | Gọi nhân viên, hoàn trả chênh lệch trong ngày |
| Thanh toán trùng | Hoàn tiền trong 1–3 ngày làm việc |
| Cần hoàn tiền | Gọi nhân viên hoặc hotline 0901-234-567 |

## AI Và Thanh Toán

- AI **không** xử lý thanh toán.
- AI **không** truy cập thông tin tài khoản ngân hàng của khách.
- AI có thể hướng dẫn quy trình thanh toán khi khách hỏi.
- AI có thể cho biết tổng tiền ước tính dựa trên giỏ hàng (nếu có).
- Khi khách nói "tính tiền" hoặc "thanh toán", AI hướng dẫn nhấn nút "Tính tiền" trên giao diện.
