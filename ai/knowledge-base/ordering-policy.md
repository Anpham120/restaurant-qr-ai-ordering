---
id: kb.policy.ordering.v1
title: Chính Sách Đặt Món
domain: policy
tags: [ordering, policy, safety]
language: vi
source: restaurant_ops_manual
reviewed_by: restaurant_manager
reviewed_at: 2026-07-13
expires_at: 2027-01-13
safety_level: high
---

# Chính Sách Đặt Món

AI là trợ lý tư vấn, không phải nhân viên xác nhận đơn hàng.

## Quy Tắc An Toàn

- AI không tự tạo đơn hàng.
- AI không tự thêm món vào giỏ.
- AI không tự thanh toán.
- AI chỉ được đề xuất món và yêu cầu khách xác nhận thao tác.
- Backend .NET chịu trách nhiệm kiểm tra món tồn tại, giá, trạng thái còn hàng và quyền thao tác.

## Quy Trình Đặt Món Chi Tiết

### Bước 1: Mở Phiên Bàn

Khách quét mã QR dán trên bàn bằng camera điện thoại. Hệ thống tự tạo phiên bàn (TableSession) với mã bàn (ví dụ: T01, T12). Phiên bàn giữ nguyên cho đến khi khách thanh toán hoặc nhân viên đóng phiên thủ công.

### Bước 2: Chọn Món

Khách duyệt menu trên giao diện web, chọn món, điều chỉnh số lượng. Có thể thêm ghi chú cho từng món (ví dụ: "Không hành", "Giảm cay", "Thêm đá"). Ngoài ra khách có thể hỏi AI chatbot để được tư vấn, gợi ý món phù hợp.

### Bước 3: Xác Nhận Giỏ Hàng

Khách xem lại giỏ hàng, kiểm tra số lượng, tổng tiền. Nhấn "Xác nhận đơn" để gửi đơn đến bếp. Đơn chưa gửi có thể sửa, xóa thoải mái.

### Bước 4: Bếp Nhận Đơn

Sau khi xác nhận, đơn được gửi đến màn hình bếp (Kitchen Display System). Bếp bắt đầu chế biến. Khách không thể hủy đơn đã gửi qua hệ thống — phải gọi nhân viên.

### Bước 5: Phục Vụ

Nhân viên mang món đến bàn. Nếu món sai hoặc thiếu, khách gọi nhân viên trực tiếp.

## Tại Bàn (Dine-In)

Khách chỉ đặt món tại bàn qua QR: quét mã bàn, mở phiên, chọn món và xác nhận. Đơn phải đi qua backend và bếp sau khi khách xác nhận. Hệ thống **không** hỗ trợ đặt mang về / pickup online.

## Gọi Thêm Món (Round Mới)

Sau khi gửi đơn đầu tiên, khách vẫn có thể gọi thêm trong cùng phiên bàn:

1. Mở lại trang đặt món (quét QR hoặc quay lại tab cũ).
2. Chọn thêm món mới.
3. Xác nhận gửi → đơn mới (round mới) được gửi bếp riêng.

Mỗi round xử lý độc lập. Không giới hạn số round. Tổng hóa đơn cộng dồn tất cả các round trong phiên.

## Giới Hạn Đặt Món

| Giới hạn | Giá trị | Lý do |
|---|---|---|
| Số món tối đa / đơn | 20 | Tránh nhầm lẫn, quá tải bếp |
| Số lượng tối đa / món | 10 | Đảm bảo nguyên liệu đủ |
| Giá trị tối thiểu / đơn | Không yêu cầu | — |
| Giá trị tối đa / đơn | 10.000.000đ | Bảo vệ thanh toán |
| Số round / phiên | Không giới hạn | — |

## Món Hết Hàng

Nếu món hết hàng, AI phải từ chối gợi ý món đó và đề xuất món thay thế đang còn hàng. Trạng thái hết hàng được cập nhật real-time bởi nhân viên hoặc hệ thống inventory.

## Thời Gian Chờ Ước Tính

| Loại món | Thời gian trung bình |
|---|---|
| Đồ uống (nước ép, trà, cà phê) | 3–5 phút |
| Khai vị (gỏi cuốn, chả giò) | 5–8 phút |
| Món chính (phở, cơm, bún) | 10–15 phút |
| Lẩu | 15–20 phút |
| Hải sản cao cấp (tôm hùm) | 20–25 phút |
| Tráng miệng | 5–10 phút |

Giờ cao điểm (11:30–13:00, 18:30–20:00): thời gian chờ có thể tăng 30–50%.

## Hủy Và Sửa Đơn

### Trước khi gửi bếp
- Khách tự sửa/xóa trong giỏ hàng trên giao diện.
- Không giới hạn số lần sửa.

### Sau khi gửi bếp
- **Không thể hủy qua hệ thống.**
- Gọi nhân viên để yêu cầu hủy.
- Món đã chế biến xong: không hoàn tiền, không hủy.
- Món chưa chế biến: nhân viên hủy trên Kitchen Display, hoàn tiền.

### Đơn Nhầm / Sai Món
- Nếu bếp làm sai so với đơn → đổi miễn phí, nhân viên xử lý.
- Nếu khách đặt nhầm → tùy trường hợp, nhân viên quyết định.

## Chính Sách Ghi Chú

Ghi chú được gửi cùng đơn đến bếp. Bếp cố gắng đáp ứng, nhưng:
- Một số món có vị cố định, không thể thay đổi (ví dụ: lẩu chua cay luôn có ớt).
- Ghi chú quá phức tạp: nhân viên có thể đến bàn xác nhận.
- Ghi chú hợp lệ: "Không hành", "Giảm cay", "Không rau mùi", "Thêm đá", "Ít đường", "Để riêng nước chấm".

## AI Gợi Ý Món Trong Chat

Khi AI gợi ý món trong chat:

1. AI hiển thị thẻ gợi ý với tên món, giá, lý do.
2. Khách nhấn nút "Thêm vào giỏ" trên thẻ gợi ý.
3. Món được thêm vào giỏ hàng, chờ khách xác nhận đơn.
4. AI **không** tự gửi đơn đến bếp.
5. AI gợi ý tối đa 4 món / lượt (hoặc theo yêu cầu khách).
6. AI không gợi ý lại món đã gợi ý trước đó hoặc món bị khách từ chối.

## Chính Sách Giá

- Giá hiển thị trên menu là giá cuối cùng, đã bao gồm VAT.
- Không phụ thu cuối tuần, lễ, tết.
- Khuyến mãi (nếu có) được áp dụng tự động tại checkout.
- AI **không** tự tạo giá, không giảm giá, không tính khuyến mãi — chỉ hiển thị giá từ hệ thống.
