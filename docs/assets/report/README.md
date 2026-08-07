# Ảnh dùng trong báo cáo học phần

Thư mục này chứa ảnh chụp màn hình dành riêng cho
[`docs/bao-cao/BAO_CAO_CONG_NGHE_PHAN_MEM.md`](../../bao-cao/BAO_CAO_CONG_NGHE_PHAN_MEM.md).
Ảnh giao diện dùng chung với README gốc nằm ở [`../readme/`](../readme/).

## Ảnh đang được báo cáo tham chiếu

Toàn bộ danh sách dưới đây **đã chụp xong**. Không còn ảnh nào phải chụp thêm.

| Tệp | Hình | Nội dung |
|---|---|---|
| `github-milestones.png` | 5 | 5 milestone đều 100 % complete |
| `github-issues.png` | 6 | 46 issue đã đóng, có nhãn và người được gán |
| `github-commit-activity.png` | 7 | Commit theo tuần, trải đều tháng 6 → tháng 8 |
| `github-pulls.png` | 8 | 305 pull request đã merge |
| `github-actions.png` | 9 | 2.468 lần chạy workflow trên 9 workflow |
| `github-releases.png` | 10 | Ba bản phát hành v0.1.0 → v0.3.0 |
| `anhci.jpg` | 11 | Branch ruleset: bắt buộc PR, bắt buộc CI xanh, chặn force push |
| `prod-ordering-entry.png` | 13 | Điểm vào gọi món ở khung hình điện thoại 414×896 |
| `trolyaitraloi1.jpg` | 14a | Trợ lý AI trả lời câu hỏi mở — sáu gợi ý kèm giá |
| `trolyaitraloi2.jpg` | 14b | Cùng phiên, sau khi khách nêu dị ứng tôm — còn ba món |
| `Trangthaibankhach.jpg` | 15 | Khách theo dõi trạng thái đơn, thanh 4 bước, hóa đơn toàn phiên |
| `trangbep.jpg` | 16 | Bảng bếp, đơn ở cả bốn trạng thái, có sự kiện realtime |
| `trangquay.jpg` | 17 | Quầy thu ngân, hóa đơn phiên bàn gộp hai lượt gọi, VietQR |
| `quanlythucdon.jpg` | 18 | Quản lý thực đơn — bộ lọc xác nhận 91 món, mỗi danh mục 7 món |
| `quanlyban.jpg` | 19 | Quản lý bàn — 30 bàn, thống kê realtime |
| `qrban.jpg` | 20 | Sinh mã QR theo bàn — **xem cảnh báo bên dưới** |
| `Quanlynguoidung.jpg` | 21 | Quản lý người dùng, ba vai trò vận hành |

Bốn ảnh giao diện khách gộp thành **Hình 12** ở mục 5.1.1 (`customer-home`, `customer-menu`, `order-scan`,
`operations-login`) dùng lại từ [`../readme/`](../readme/), không nhân bản sang đây.

## Cảnh báo — `qrban.jpg` lộ mã QR của bàn T01 trên production

Ảnh hiển thị đầy đủ liên kết đặt món kèm tham số `?qr=<token>` của bàn T01 trên
`order.cmcrestaurant.app`. Mã này vốn được thiết kế để công khai — nó được in và dán tại bàn — nên
đây **không phải rò rỉ thông tin xác thực**: nó chỉ mở được phiên của đúng bàn T01, và mỗi lần quét
backend vẫn cấp một capability token riêng.

Tuy nhiên repository là public, nên bất kỳ ai đọc cũng có thể mở phiên trên bàn T01 của bản triển
khai thật. Trước khi nộp, nên chọn một trong hai cách:

1. **Làm mờ vùng "LINK ĐẶT MÓN"** trong ảnh (giữ nguyên hình QR cho đẹp) — cách nhanh nhất.
2. **Xoay lại mã QR của T01** sau khi nộp, để mã trong ảnh hết hiệu lực.

Quy ước của thư mục này đã yêu cầu che token trên thanh địa chỉ; ảnh này là ngoại lệ chưa xử lý.

## Vì sao không có `github-contributors.png`

GitHub chỉ hiển thị biểu đồ Insights → Contributors cho người đã đăng nhập, nên ảnh này không chụp
được ở dạng ẩn danh. Báo cáo ghi rõ điều đó ở mục 3.3 và thay bằng ba hình 3.2, 3.3, 3.4 vốn phủ
cùng nội dung.

## Quy ước

- Ảnh desktop rộng 1200–1600 px; ảnh mobile giữ tỷ lệ gốc.
- **Che thông tin nhạy cảm** trước khi commit: email thật, token trên thanh địa chỉ, số tài khoản.
- Đặt tên bằng chữ thường, dùng gạch nối; **không** đổi tên tệp đã được báo cáo tham chiếu — mọi
  tệp trong bảng trên đều đang được trỏ tới từ báo cáo.
- Khi thay ảnh, kiểm lại con số hiện trong ảnh có khớp con số viết trong báo cáo không. Đã từng có
  lần ảnh ghi 303 pull request trong khi báo cáo ghi 305.
