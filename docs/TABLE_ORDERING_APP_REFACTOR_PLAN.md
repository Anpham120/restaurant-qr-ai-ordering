# Kế hoạch refactor ứng dụng gọi món tại bàn độc lập

> Trạng thái: đã triển khai trên nhánh `codex/issue-242-ordering-app`, đang chờ review và phát hành.
> Domain chính: `order.cmcrestaurant.app`.

## Lỗi hiện tại

Màn hình “Phiên gọi món chưa sẵn sàng” xuất hiện khi người dùng mở thẳng URL chứa `sessionId` trong một tab mới nhưng trình duyệt không có capability của phiên. `sessionId` chỉ là mã định danh, không phải thông tin cấp quyền, nên không thể dùng riêng URL này để truy cập phiên.

Ứng dụng cũ còn trộn hai sản phẩm trong cùng một bundle:

- `cmcrestaurant.app`: trang giới thiệu nhà hàng;
- luồng QR, phiên bàn, thực đơn, giỏ hàng, thanh toán và trạng thái món.

Việc dùng chung router, storage, CSS và artifact deploy khiến URL của phiên bàn dễ rơi về trang giới thiệu, lỗi khó phân loại và hai phần không thể phát hành độc lập.

## Kiến trúc đích

### 1. Marketing app — `cmcrestaurant.app`

Chỉ sở hữu:

- giới thiệu nhà hàng;
- thực đơn xem trước, chỉ đọc;
- album, đánh giá và thông tin liên hệ;
- hướng dẫn quét QR để gọi món.

Không sở hữu session, cart, checkout, order tracking hoặc AI.

### 2. Table ordering app — `order.cmcrestaurant.app`

Chỉ sở hữu:

- vào phiên bằng QR;
- xác thực và khôi phục phiên bàn;
- thực đơn giao dịch;
- giỏ hàng;
- checkout/thanh toán theo contract hiện có;
- danh sách món đã gọi và trạng thái đơn.

Không có hero marketing, album, testimonial, nội dung giới thiệu hoặc AI. Giao diện chỉ giữ ngôn ngữ thương hiệu: màu ivory/chestnut/brass, typography, logo và phong cách card.

### 3. Khối dùng chung

Hai app chỉ dùng chung package `brand-ui` và các transport/domain contract ổn định. Không dùng chung router, layout, page hoặc ownership của session/cart.

## Quy tắc phiên bàn

- QR route là cách duy nhất tạo capability trong trình duyệt mới.
- Capability lưu trong `sessionStorage`, giới hạn trong một tab.
- Cart vẫn lưu theo `sessionId`; đổi phiên không được dùng lại cart của phiên khác.
- URL chỉ có `sessionId` nhưng thiếu capability phải hiện đúng trạng thái “cần quét lại QR”.
- Capability sai phiên, hết hạn và backend lỗi phải là các trạng thái khác nhau.
- UI không đọc token trực tiếp; mọi thao tác đi qua session module.
- `customer.cmcrestaurant.app` chỉ là host tương thích tạm thời cho luồng cũ.

## Các giai đoạn triển khai

1. Tách brand token và primitive thành `@cmc/brand-ui`.
2. Tạo workspace/build độc lập `ordering-web`.
3. Tách session capability store và chuyển capability từ local storage sang tab storage.
4. Chuyển QR entry, menu, cart, checkout và order tracking sang ordering app.
5. Loại bỏ route giao dịch và AI khỏi marketing app.
6. Đổi QR do admin tạo sang `order.cmcrestaurant.app/enter/:qrToken`.
7. Thêm artifact, Nginx host mapping, TLS host, CORS và biến môi trường cho domain mới.
8. Giữ redirect tương thích từ URL cũ; không chuyển local storage giữa hai origin.
9. Chạy unit test, full frontend build, backend test, Docker Compose validation và browser smoke test.
10. Review diff, commit, tạo PR; sau khi CI xanh mới merge và deploy.

## Tiêu chí nghiệm thu

- Marketing app build độc lập và không import page/session/cart của ordering app.
- Ordering app build độc lập và không import trang marketing hoặc AI.
- Điều hướng ordering trên mobile chỉ có: Thực đơn, Giỏ hàng, Món đã gọi.
- QR hợp lệ mở/khôi phục đúng phiên và đưa người dùng vào thực đơn.
- Mở trực tiếp session URL trong tab mới không cấp quyền; UI yêu cầu quét QR lại.
- Cart không rò rỉ giữa hai phiên bàn.
- Admin tạo QR bằng ordering domain.
- Nginx phục vụ đúng artifact theo từng host và SPA fallback hoạt động.
- Backend cho phép CORS từ production, staging và localhost của ordering app.
- Build/test/Compose validation đều xanh trước khi phát hành.

## Trình tự phát hành

1. Deploy `order.cmcrestaurant.app` ở chế độ dark launch.
2. Smoke test QR → menu → cart → checkout → orders trên production.
3. Chuyển QR mới do admin tạo sang ordering domain.
4. Theo dõi lỗi bootstrap phiên, tải menu và submit order.
5. Giữ `customer.cmcrestaurant.app` trong thời gian chuyển tiếp.
6. Chỉ xóa host tương thích sau khi không còn QR cũ được sử dụng.

## Ngoài phạm vi

- AI chatbot/RAG trong ứng dụng gọi món tối giản.
- Đổi nghiệp vụ backend, schema database hoặc contract thanh toán.
- Tích hợp PayOS mới.
- Đặt bàn trước/reservation.
- Redesign admin, staff hoặc kitchen.
- Thay toàn bộ nhận diện thương hiệu.
