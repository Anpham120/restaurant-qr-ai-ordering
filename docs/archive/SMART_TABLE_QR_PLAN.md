# Kế hoạch nâng cấp QR bàn thông minh

## 1. Mục tiêu và hiện trạng

Mỗi bàn giữ **một QR cố định**. Mỗi lần quét, backend mở hoặc tái sử dụng đúng phiên `Open` của bàn, cấp capability token mới cho thiết bị và trả về trạng thái tiếp tục. Khách không cần giữ tab cũ hay đăng nhập.

Repo hiện đã có phần nền cần thiết:

- QR bàn đã dùng `RestaurantTable.QrToken` ổn định và backend đã tái sử dụng phiên `Open` thay vì tạo phiên mới.
- Lỗi hành vi hiện tại nằm ở `TableScanPage`: quét thành công luôn điều hướng về `/menu`.
- `Served` đã tồn tại trong `OrderStatus`, `OrderItemStatus`, backend transition và màn Staff; màn Kitchen mới chỉ có ba cột mới/đang nấu/sẵn sàng.

Thành công khi cùng một QR đi hết hành trình:

`Menu → Giỏ đang dở → Theo dõi món → Hóa đơn → Chờ thanh toán → Đã thanh toán`

## 2. Luồng sản phẩm đã chốt

### Bộ trạng thái tiếp tục

Backend bổ sung trường additive `resumeState` vào `OpenTableSessionResponse` và shared type tương ứng:

| `resumeState` | Điều kiện, theo thứ tự ưu tiên | Trang sau khi quét |
|---|---|---|
| `Paid` | Hóa đơn `Paid` hoặc `Confirmed` | `/orders?focus=invoice` |
| `PaymentPending` | Hóa đơn `Pending` | `/orders?focus=invoice` |
| `ReadyForPayment` | Có món không hủy và mọi đơn đều `Served`/`Completed`; thanh toán chưa xong | `/orders?focus=invoice` |
| `OrderInProgress` | Còn đơn `Placed`/`Confirmed`/`Preparing`/`Ready` | `/orders` |
| `CartPending` | Chưa có đơn nhưng giỏ server còn món | `/cart` |
| `New` | Không có giỏ, đơn hoặc hóa đơn cần tiếp tục | `/menu` |

Quy tắc biên:

- Đơn `Cancelled` không tham gia quyết định; phiên chỉ có đơn hủy được xem là `New`.
- Thanh toán `Failed`, `Cancelled` hoặc `Refunded` quay về `ReadyForPayment` nếu món đã phục vụ.
- Nếu vừa có đơn đang xử lý vừa có đơn đã phục vụ, ưu tiên `OrderInProgress`.
- Phiên `Paid` vẫn hiển thị biên lai/cảm ơn cho tới khi Staff đóng bàn. Sau khi đóng hoặc hết hạn, lần quét kế tiếp tạo phiên mới và vào menu.
- Giữ thời hạn phiên hiện tại là 4 giờ; không gia hạn hoặc đổi lifecycle trong đợt này.

### Hub “Bàn của bạn”

Nâng `SessionOrdersPage` thành hub trạng thái thay vì tạo một app/trang thanh toán riêng. Trang vẫn dùng route `/table-session/:sessionId/orders`, nhưng phần đầu thay đổi theo trạng thái:

```text
┌ CMC                 VI   Bàn T01 ┐
│ BÀN CỦA BẠN · ĐANG CHẾ BIẾN      │
│ 2/4 món đã sẵn sàng               │
│ [Xem tiến độ]   [Gọi thêm món]    │
│ Gọi món ━ Đang nấu ─ Phục vụ ─ Trả│
├───────────────────────────────────┤
│ Các lần gọi món / hóa đơn phiên   │
└───────────────────────────────────┘
```

- `OrderInProgress`: nhấn mạnh tiến độ món và trạng thái bếp; “Gọi thêm món” là hành động phụ.
- `ReadyForPayment`: đưa tổng hóa đơn và “Yêu cầu thanh toán” thành hành động chính.
- `PaymentPending`: giữ VietQR hoặc hướng dẫn tiền mặt hiện tại, không cho gọi thêm món.
- `Paid`: hiển thị biên lai và lời cảm ơn; không tạo phiên mới cho tới khi bàn được đóng.
- Dùng một “table journey strip” gồm Gọi món → Chế biến → Phục vụ → Thanh toán làm dấu ấn giao diện; giữ nguyên hệ màu/font thương hiệu hiện tại, chỉ dùng brass cho bước đang chạy và green cho bước hoàn tất.
- Hub subscribe SignalR order/payment; khi mất realtime thì poll 5 giây. Mỗi event reload đồng thời orders và invoice để nhiều điện thoại thấy cùng trạng thái.

## 3. Thay đổi triển khai

### Backend và contract

1. Tách hàm thuần `ResolveTableSessionResumeState` nhận cart, các order không hủy và invoice status; unit-test toàn bộ bảng trạng thái trên.
2. Trong `POST /api/table-sessions`, sau khi tìm/tạo phiên, truy vấn tối thiểu cart count, order statuses và invoice status rồi trả thêm `resumeState`. Đây là thay đổi additive, không cần migration và client cũ vẫn chạy.
3. Giữ unique filtered index hiện tại để nhiều thiết bị quét đồng thời vẫn chỉ có một phiên `Open` cho bàn.
4. Thêm structured log gồm `tableCode`, `sessionId`, `reusedSession`, `resumeState`; tuyệt đối không log QR token hoặc capability token.

### Frontend QR và session hub

1. `TableScanPage` tiếp tục resolve QR, mở/tái sử dụng session và lưu capability vào `sessionStorage`, nhưng dùng một hàm thuần `getResumeDestination(resumeState)` thay cho redirect cứng về menu.
2. Khi session ID thay đổi, xóa cart cache cũ như hiện tại; khi cùng session, giữ nguyên dữ liệu để thiết bị/tab quét lại tiếp tục đúng phiên.
3. `SessionOrdersPage` tính progress từ orders/items, hiển thị journey strip, tự focus/scroll tới invoice khi query `focus=invoice`, và cập nhật realtime.
4. Giữ các route hiện có để không phá QR/link đã phát hành; QR admin tiếp tục sinh `/table/{tableCode}?qr={token}`.

### Trạng thái “Đã phục vụ” ở Kitchen

1. Mở rộng pipeline Kitchen thành bốn cột: `Mới`, `Đang nấu`, `Sẵn sàng`, `Đã phục vụ`; cột cuối chỉ đọc và ghi rõ “Chờ thanh toán/hoàn tất”.
2. Ở card/detail của đơn `Ready`, thêm hành động “Đã phục vụ”. Cả role `Kitchen` và `Staff` được phép thực hiện đúng transition `Ready → Served`; Kitchen không được dùng order endpoint để Confirm/Cancel/Complete.
3. Transition `Ready → Served` cập nhật atomically mọi item không hủy từ `Ready` sang `Served`, order sang `Served`, status history và realtime event. Staff tiếp tục dùng cùng command để hai màn hình không lệch dữ liệu.
4. Sau realtime reload, đơn rời cột Sẵn sàng sang Đã phục vụ; QR scan kế tiếp chỉ chuyển sang `ReadyForPayment` khi mọi order không hủy của phiên đã `Served`/`Completed`.

## 4. Kiểm thử và nghiệm thu

### Backend

- Quét cùng QR nhiều lần/trên hai thiết bị trả cùng `sessionId`; quét đồng thời không tạo hai phiên.
- Ma trận `New`, `CartPending`, `OrderInProgress`, `ReadyForPayment`, `PaymentPending`, `Paid` đúng precedence nêu trên.
- QR sai, bàn inactive, session hết hạn và session đã đóng giữ error/lifecycle hiện tại.
- Kitchen chỉ được `Ready → Served`; Staff/Admin giữ transition hiện có; bulk serve cập nhật order/items/history nhất quán.
- Order/payment realtime được phát sau commit, không phát event giả khi conflict.

### Frontend

- Unit test ánh xạ mỗi `resumeState` sang route; không còn redirect cứng `/menu`.
- Hub hiển thị đúng primary action, khóa gọi thêm khi payment pending/paid, và reload khi có order/payment event.
- Kitchen hiển thị bốn cột, nút Served chỉ ở đơn Ready và chuyển cột sau thành công.
- 320px không tràn ngang; nút chính ≥44px; VI/EN và accessibility labels giữ nguyên.

### E2E bắt buộc

1. Quét QR mới → menu; thêm giỏ rồi đóng tab → quét lại → cart.
2. Gửi đơn rồi đóng trình duyệt → quét lại trên cùng hoặc điện thoại khác → hub hiển thị tiến độ hiện tại.
3. Kitchen chuyển Ready → Served → quét lại → invoice được focus và có nút yêu cầu thanh toán.
4. Yêu cầu COD/VietQR → quét lại → trạng thái pending; xác nhận thanh toán → quét lại → biên lai Paid.
5. Staff đóng bàn → quét lại cùng QR → session ID mới và menu sạch.

## 5. Rollout và giả định

- Deploy backend trước, frontend sau vì contract chỉ thêm trường.
- Không đổi database schema và không đổi URL/giá trị QR trong đợt này; QR đã in tiếp tục dùng được.
- Token seed hiện có thể đoán được, nên rotation sang token ngẫu nhiên 128-bit là một hạng mục hardening riêng trước production; rotation phải đi kèm in lại QR và không được làm âm thầm.
- Mặc định chọn hub theo trạng thái, invoice sau khi toàn bộ món đã phục vụ, và cả Kitchen/Staff được xác nhận Served. Nếu nghiệp vụ thực tế phân vai khác, chỉ đổi policy/action Served; state machine QR không đổi.
