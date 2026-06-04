# Hợp Đồng API

Tài liệu này là hợp đồng giữa Backend, Frontend, AI và Realtime. Nếu muốn đổi endpoint, field, enum hoặc event payload, thành viên phải báo Lead và cập nhật tài liệu này trước khi sửa code.

## 1. Quy Tắc Chung

- API base path: `/api`.
- Response JSON dùng camelCase.
- Frontend không gọi `fetch` rải rác trong component; phải đi qua service layer.
- Backend không trả trực tiếp entity database nếu response cần ổn định; nên dùng DTO.
- Mock data frontend phải dùng cùng shape với contract này.
- Status name, route name và shared type không được tự ý đổi theo sở thích UI/backend.

## 1.1. Backend Setup Tuần 1

- Solution backend: `backend/RestaurantQrAiOrdering.sln`.
- API project: `backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj`.
- Test project: `backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj`.
- Visual Studio 2026 nên mở trực tiếp file solution và chạy startup project `RestaurantQrAiOrdering.Api`.
- Launch profile dùng cho local HTTPS: `https`.
- Health check hiện tại: `GET /api/health`.

Response health check dự kiến:

```json
{
  "status": "Healthy",
  "service": "RestaurantQrAiOrdering.Api",
  "environment": "Development",
  "checkedAtUtc": "2026-06-04T00:00:00Z"
}
```

Endpoint này chỉ dùng để xác nhận API chạy được trong Visual Studio, .NET CLI và test integration. Không thêm logic Auth, Menu, Orders, Chat, AI hoặc Realtime trong issue scaffold backend.

## 2. Auth

### POST `/api/auth/register`

Mục đích: tạo tài khoản customer.

Request dự kiến:

```json
{
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "password": "Password123!"
}
```

Response dự kiến:

```json
{
  "userId": "usr_001",
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "role": "Customer"
}
```

### POST `/api/auth/login`

Mục đích: đăng nhập và nhận access token.

Response dự kiến:

```json
{
  "accessToken": "jwt-token",
  "expiresAt": "2026-06-04T12:00:00Z",
  "user": {
    "userId": "usr_001",
    "fullName": "Nguyen Van A",
    "role": "Customer"
  }
}
```

Vai trò:

- `Customer`
- `Staff`
- `Kitchen`
- `Admin`

## 3. Tables / QR

### GET `/api/tables/{tableCode}`

Mục đích: lấy thông tin bàn khi khách vào từ QR route `/table/:tableCode`.

Response dự kiến:

```json
{
  "tableCode": "T05",
  "displayName": "Ban 05",
  "isActive": true
}
```

Quy tắc:

- `tableCode` phải tồn tại.
- Bàn phải đang active.
- QR v1 có thể dùng `/table/:tableCode`; nếu cần bảo mật hơn có thể bổ sung `qrToken` ở phiên bản sau.

## 4. Menu

### GET `/api/menu`

Mục đích: lấy menu cho customer, admin và chatbot.

Response dự kiến:

```json
{
  "categories": [
    {
      "categoryId": "cat_main",
      "name": "Mon chinh"
    }
  ],
  "items": [
    {
      "id": "m_001",
      "name": "Com ga xoi mo",
      "description": "Ga chien gion, com thom, dua chua.",
      "price": 45000,
      "categoryName": "Mon chinh",
      "imageUrl": "https://example.com/com-ga.jpg",
      "isAvailable": true,
      "tags": ["pho bien"]
    }
  ]
}
```

Menu item fields phải giữ thống nhất với frontend mocks và dữ liệu RAG của chatbot.

## 5. Orders

### POST `/api/orders`

Mục đích: tạo đơn từ QR dine-in, pickup hoặc delivery mock.

Request dự kiến:

```json
{
  "orderType": "DineIn",
  "tableCode": "T05",
  "paymentMethod": "COD",
  "deliveryInfo": null,
  "items": [
    {
      "menuItemId": "m_001",
      "quantity": 2
    }
  ]
}
```

Response dự kiến:

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Placed",
  "paymentStatus": "Unpaid",
  "items": [
    {
      "orderItemId": "oi_001",
      "menuItemId": "m_001",
      "name": "Com ga xoi mo",
      "quantity": 2,
      "status": "Pending"
    }
  ]
}
```

Quy tắc nghiệp vụ:

- Backend phải từ chối món không còn hàng.
- Customer chỉ được hủy trước khi đơn/món chuyển sang `Preparing`.
- `DineIn` yêu cầu `tableCode` hợp lệ và đang active.
- `DeliveryMock` yêu cầu thông tin người nhận và địa chỉ.

### GET `/api/orders/{orderCode}`

Mục đích: customer tracking screen.

Response nên khớp với create order response, đồng thời bổ sung timestamps và trạng thái hiện tại của từng món.

## 6. Chat

### POST `/api/chat/sessions`

Mục đích: tạo phiên chat.

Response dự kiến:

```json
{
  "chatSessionId": "chat_001",
  "createdAt": "2026-06-04T08:00:00Z"
}
```

### POST `/api/chat/sessions/{chatSessionId}/messages`

Mục đích: gửi tin nhắn của khách và nhận phản hồi từ chatbot.

Request dự kiến:

```json
{
  "content": "Goi y mon cho 2 nguoi",
  "tableCode": "T05"
}
```

Response dự kiến:

```json
{
  "message": {
    "id": "msg_002",
    "role": "assistant",
    "content": "Ban co the chon Com ga xoi mo va Tra dao cam sa.",
    "createdAt": "2026-06-04T08:01:00Z"
  },
  "suggestedCartActions": [
    {
      "menuItemId": "m_001",
      "name": "Com ga xoi mo",
      "price": 45000,
      "quantity": 1,
      "reason": "Mon pho bien, phu hop bua chinh."
    }
  ]
}
```

Quy tắc:

- Chatbot được đề xuất cart actions.
- Customer phải xác nhận trước khi món được thêm vào giỏ.
- Chatbot không được đặt đơn hoặc thanh toán.
- Chatbot không được bịa món, giá hoặc món đã hết hàng.

## 7. SignalR Events

Hub dự kiến: `/hubs/orders`

### `order.created`

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Placed",
  "createdAt": "2026-06-04T08:05:00Z"
}
```

### `order.statusChanged`

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "status": "Preparing",
  "updatedAt": "2026-06-04T08:10:00Z"
}
```

### `order.itemStatusChanged`

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderItemId": "oi_001",
  "menuItemName": "Com ga xoi mo",
  "status": "Ready",
  "updatedAt": "2026-06-04T08:18:00Z"
}
```

## 8. Cấu Trúc Lỗi

Dự kiến:

```json
{
  "error": {
    "code": "MENU_ITEM_UNAVAILABLE",
    "message": "Menu item is unavailable.",
    "details": {}
  }
}
```

Frontend phải hiển thị thông báo thân thiện cho người dùng và không được phụ thuộc vào nội dung database exception.

## 9. Data Model Draft

Enums:

- `OrderType`: `DineIn`, `Pickup`, `DeliveryMock`
- `OrderStatus`: `Draft`, `Placed`, `Confirmed`, `Preparing`, `Ready`, `Served`, `Delivering`, `Delivered`, `Completed`, `Cancelled`
- `OrderItemStatus`: `Pending`, `Preparing`, `Ready`, `Served`, `Cancelled`
- `PaymentMethod`: `COD`, `MockOnline`
- `PaymentStatus`: `Unpaid`, `Paid`, `Failed`, `Cancelled`

Entities:

- `RestaurantTable`: `id`, `tableCode`, `displayName`, `isActive`, optional `qrToken`.
- `Category`: `id`, `name`, `displayOrder`, `isActive`.
- `MenuItem`: `id`, `categoryId`, `name`, `description`, `price`, `imageUrl`, `isAvailable`, `tags`.
- `Order`: `id`, `orderCode`, `orderType`, `status`, dine-in `tableCode`/`restaurantTableId`, pickup customer fields, delivery mock recipient/address fields, `subtotalAmount`, `totalAmount`.
- `OrderItem`: `id`, `orderId`, `menuItemId`, snapshot `menuItemName`, `unitPrice`, `quantity`, item-level `status`.
- `Payment`: `id`, `orderId`, `method`, `status`, `amount`, optional provider transaction id, payment timestamps.
- `ChatSession`: `id`, optional `tableCode`, optional `orderId`, `isClosed`, timestamps, messages.
- `ChatMessage`: `id`, `chatSessionId`, `role`, `content`, optional suggested cart actions payload, `createdAt`.
- `KnowledgeEntry`: `id`, `title`, `content`, `sourceType`, optional `menuItemId`, `tags`, optional embedding, `isActive`.
