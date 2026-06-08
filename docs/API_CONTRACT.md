# Hợp Đồng API

Tài liệu này là hợp đồng giữa Backend, Frontend, AI và Realtime. Nếu muốn đổi endpoint, field, enum, error code hoặc event payload, thành viên phải báo Lead và cập nhật tài liệu này trước khi sửa code.

Phạm vi cập nhật tuần 2 của issue #10: khóa contract cho auth, menu, tables, order creation, order detail, error shape, shared enum/status names, seed data plan và checklist tích hợp thủ công. Đây là thay đổi tài liệu, không implement feature code.

## 1. Quy Tắc Chung

- API base path: `/api`.
- Response JSON dùng `camelCase`.
- Thời gian dùng ISO 8601 UTC, ví dụ `2026-06-05T10:30:00Z`.
- Tiền tệ dùng VND, field amount/price là số nguyên hoặc decimal không âm theo DTO backend.
- Frontend không gọi `fetch` rải rác trong component; phải đi qua service layer.
- Backend không trả trực tiếp entity database nếu response cần ổn định; dùng DTO để giữ contract.
- Mock data frontend phải dùng cùng shape, enum và mã lỗi với contract này.
- Status name, route name, shared type và error code không được tự ý đổi theo sở thích UI/backend.
- Những endpoint chưa implement xong vẫn phải bám contract này khi member triển khai.

### 1.1. Backend Setup Tuần 1

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

Endpoint này chỉ dùng để xác nhận API chạy được trong Visual Studio, .NET CLI và test integration. Không gắn thêm logic Auth, Menu, Orders, Chat, AI hoặc Realtime vào health check.

## 2. Shared Enum / Status Names

Các enum dưới đây là tên chuẩn cho backend DTO, frontend TypeScript type, mock data, seed data, SignalR event và báo cáo test.

| Nhóm | Giá trị hợp lệ | Ghi chú |
| --- | --- | --- |
| `UserRole` | `Customer`, `Staff`, `Kitchen`, `Admin` | `Customer` tự đăng ký; các role vận hành do seed/admin tạo. |
| `OrderType` | `DineIn`, `Pickup`, `DeliveryMock` | `DineIn` bắt buộc có `tableCode`; `DeliveryMock` bắt buộc có `deliveryInfo`. |
| `OrderStatus` | `Draft`, `Placed`, `Confirmed`, `Preparing`, `Ready`, `Served`, `Delivering`, `Delivered`, `Completed`, `Cancelled` | UI có thể chỉ dùng subset, nhưng không được đổi tên. |
| `OrderItemStatus` | `Pending`, `Preparing`, `Ready`, `Served`, `Cancelled` | Trạng thái theo từng món trên kitchen/staff/customer tracking. |
| `PaymentMethod` | `COD`, `MockOnline` | Chưa tích hợp cổng thanh toán thật trong v1. |
| `PaymentStatus` | `Unpaid`, `Paid`, `Failed`, `Cancelled` | Không dùng `Pending` cho payment trong contract API. |
| `ChatRole` | `user`, `assistant`, `system` | Dùng cho chatbot message. |
| `TableCode` | `T01` đến `T99` | Tuần 2 seed tối thiểu `T01` đến `T08`; không dùng dạng `T-05`. |

Quy tắc đặt tên:

- Enum value dùng PascalCase, trừ `ChatRole` theo chuẩn message role viết thường.
- Error code dùng UPPER_SNAKE_CASE.
- ID seed menu dùng dạng `m_001`; category dùng dạng `cat_main`; order code dùng dạng `ORD-1001`.

## 3. Error Shape Chuẩn

Tất cả lỗi business/validation nên trả cùng shape:

```json
{
  "error": {
    "code": "MENU_ITEM_UNAVAILABLE",
    "message": "Menu item is unavailable.",
    "details": {}
  }
}
```

Quy tắc:

- `error.code` là khóa ổn định để frontend map sang thông báo thân thiện.
- `error.message` có thể là tiếng Anh kỹ thuật hoặc tiếng Việt, nhưng frontend không được phụ thuộc vào nội dung này để rẽ nhánh logic.
- `error.details` là object; có thể rỗng `{}` hoặc chứa field-level validation như `{ "field": "email" }`.
- Request body thieu/null/malformed tra `400` voi `REQUEST_INVALID` theo cung shape.
- `401 Unauthorized` và `403 Forbidden` có thể trả body rỗng nếu middleware mặc định chưa custom, nhưng khi custom API result thì phải dùng shape trên.

Error code đang dùng hoặc phải dùng:

| HTTP | Code | Khi nào |
| --- | --- | --- |
| `400` | `REQUEST_INVALID` | Request body thieu, null hoac JSON khong hop le. |
| `400` | `FULL_NAME_REQUIRED` | Register thiếu họ tên. |
| `400` | `EMAIL_INVALID` | Email sai format. |
| `400` | `PASSWORD_TOO_SHORT` | Password dưới 8 ký tự. |
| `400` | `PASSWORD_REQUIRED` | Login thiếu password. |
| `401` | `INVALID_CREDENTIALS` | Email/password không đúng. |
| `409` | `EMAIL_ALREADY_REGISTERED` | Email đã tồn tại. |
| `400` | `TABLE_CODE_INVALID` | `tableCode` không đúng format `T01`. |
| `404` | `TABLE_NOT_FOUND` | Không tìm thấy bàn active. |
| `400` | `CATEGORY_NAME_REQUIRED` | Tạo/sửa category thiếu tên. |
| `400` | `CATEGORY_REQUIRED` | Tạo/sửa món thiếu category. |
| `400` | `CATEGORY_INVALID` | Category không tồn tại hoặc inactive. |
| `404` | `CATEGORY_NOT_FOUND` | Không tìm thấy category. |
| `409` | `CATEGORY_HAS_MENU_ITEMS` | Không thể xóa category còn món. |
| `400` | `MENU_ITEM_NAME_REQUIRED` | Tạo/sửa món thiếu tên. |
| `400` | `MENU_ITEM_PRICE_INVALID` | Giá món không lớn hơn 0. |
| `404` | `MENU_ITEM_NOT_FOUND` | Không tìm thấy món. |
| `400` | `ORDER_ITEMS_REQUIRED` | Tạo đơn không có món. |
| `400` | `ORDER_ITEM_QUANTITY_INVALID` | Số lượng món nhỏ hơn 1. |
| `400` | `MENU_ITEM_UNAVAILABLE` | Món đang hết hàng. |
| `400` | `ORDER_TYPE_INVALID` | `orderType` không thuộc `OrderType`. |
| `400` | `PAYMENT_METHOD_INVALID` | `paymentMethod` không thuộc `PaymentMethod`. |
| `400` | `ORDER_STATUS_INVALID` | `status` không thuộc `OrderStatus`. |
| `400` | `ORDER_ITEM_STATUS_INVALID` | `status` không thuộc `OrderItemStatus`. |
| `400` | `ORDER_CANCEL_NOT_ALLOWED` | Khong the huy don sau khi don hoac mot mon da toi `Preparing`. |
| `400` | `DINE_IN_TABLE_REQUIRED` | `DineIn` thiếu `tableCode`. |
| `400` | `DELIVERY_INFO_REQUIRED` | `DeliveryMock` thiếu thông tin giao hàng mock. |
| `404` | `ORDER_NOT_FOUND` | Không tìm thấy đơn theo `orderCode`. |
| `404` | `ORDER_ITEM_NOT_FOUND` | Không tìm thấy món trong đơn theo `orderItemId`. |
| `400` | `CHAT_MESSAGE_EMPTY` | Nội dung chat rỗng. |
| `404` | `CHAT_SESSION_NOT_FOUND` | Không tìm thấy phiên chat. |

## 4. Auth

### POST `/api/auth/register`

Mục đích: tạo tài khoản customer. Register v1 chỉ tạo role `Customer`.

Request:

```json
{
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "password": "Password123!"
}
```

Response `201 Created`:

```json
{
  "userId": "usr_001",
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "role": "Customer"
}
```

Lỗi:

- `400` với `FULL_NAME_REQUIRED`, `EMAIL_INVALID` hoặc `PASSWORD_TOO_SHORT`.
- `409` với `EMAIL_ALREADY_REGISTERED`.

### POST `/api/auth/login`

Mục đích: đăng nhập và nhận JWT access token.

Request:

```json
{
  "email": "customer@example.com",
  "password": "Password123!"
}
```

Response `200 OK`:

```json
{
  "accessToken": "jwt-token",
  "expiresAt": "2026-06-05T12:00:00Z",
  "user": {
    "userId": "usr_001",
    "fullName": "Nguyen Van A",
    "email": "customer@example.com",
    "role": "Customer"
  }
}
```

Lỗi:

- `400` với `EMAIL_INVALID` hoặc `PASSWORD_REQUIRED`.
- `401` với `INVALID_CREDENTIALS`.

Auth header cho endpoint protected:

```http
Authorization: Bearer <accessToken>
```

### GET `/api/auth/me`

Mục đích: endpoint protected mẫu để kiểm tra JWT.

Yêu cầu: `Authorization: Bearer <accessToken>`.

Response `200 OK`:

```json
{
  "userId": "usr_001",
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "role": "Customer"
}
```

Nếu không gửi token hoặc token không hợp lệ, trả `401 Unauthorized`.

### GET `/api/auth/admin-check`

Mục đích: endpoint role-restricted mẫu để kiểm tra policy `AdminOnly`.

Yêu cầu: `Authorization: Bearer <accessToken>` của user role `Admin`.

Response `200 OK`:

```json
{
  "status": "Authorized",
  "requiredRole": "Admin"
}
```

Nếu chưa đăng nhập, trả `401 Unauthorized`. Nếu đăng nhập nhưng sai role, trả `403 Forbidden`.

## 5. Tables / QR

### GET `/api/tables/{tableCode}`

Mục đích: lấy thông tin bàn khi khách vào từ QR route `/table/:tableCode`.

Response `200 OK`:

```json
{
  "tableCode": "T05",
  "displayName": "Bàn 05",
  "isActive": true
}
```

Quy tắc:

- `tableCode` phải đúng format `T01` đến `T99`.
- Seed tuần 2 dùng `T01` đến `T08`.
- Bàn phải đang active.
- QR v1 dùng route frontend `/table/:tableCode`; nếu cần bảo mật hơn có thể bổ sung `qrToken` ở phiên bản sau.
- Format sai trả `400` với `TABLE_CODE_INVALID`.
- Không tìm thấy bàn active trả `404` với `TABLE_NOT_FOUND`.

## 6. Menu

### GET `/api/menu`

Mục đích: lấy menu public cho customer, admin preview và chatbot RAG.

Response `200 OK`:

```json
{
  "categories": [
    {
      "categoryId": "cat_main",
      "name": "Món chính"
    }
  ],
  "items": [
    {
      "id": "m_001",
      "name": "Cơm gà xối mỡ",
      "description": "Gà chiên giòn, cơm thơm, dưa chua.",
      "price": 45000,
      "categoryId": "cat_main",
      "categoryName": "Món chính",
      "imageUrl": "https://example.com/com-ga.jpg",
      "isAvailable": true,
      "tags": ["phổ biến"]
    }
  ]
}
```

Quy tắc:

- Public menu trả cả món available và unavailable để UI/chatbot biết trạng thái; field `isAvailable` phải rõ ràng.
- Public menu chỉ trả category active và item thuộc category active.
- `price` phải lớn hơn `0`.
- `name` và `categoryId` không được rỗng.
- `categoryId` phải tồn tại và đang active khi tạo/cập nhật menu item.
- Menu item fields phải giữ thống nhất với frontend mocks và dữ liệu RAG của chatbot.

### GET `/api/admin/categories`

Response `200 OK`:

```json
[
  {
    "categoryId": "cat_main",
    "name": "Món chính",
    "displayOrder": 20,
    "isActive": true,
    "createdAt": "2026-06-05T00:00:00Z",
    "updatedAt": "2026-06-05T00:00:00Z"
  }
]
```

### GET `/api/admin/categories/{categoryId}`

Response: một category theo shape của `GET /api/admin/categories`.

### POST `/api/admin/categories`

Request:

```json
{
  "name": "Món chính",
  "displayOrder": 20,
  "isActive": true
}
```

Response: `201 Created` và category vừa tạo.

### PUT `/api/admin/categories/{categoryId}`

Request: cùng shape với `POST /api/admin/categories`.

Response: category sau khi cập nhật.

### DELETE `/api/admin/categories/{categoryId}`

Response:

- `204 No Content` nếu xóa thành công.
- `404` với `CATEGORY_NOT_FOUND` nếu không tìm thấy.
- `409` với `CATEGORY_HAS_MENU_ITEMS` nếu category còn menu item.

### GET `/api/admin/menu-items`

Response: danh sách menu item theo shape item của `GET /api/menu`, bao gồm item thuộc category inactive nếu admin cần quản trị.

### GET `/api/admin/menu-items/{menuItemId}`

Response: một menu item theo shape item của `GET /api/menu`.

### POST `/api/admin/menu-items`

Request:

```json
{
  "categoryId": "cat_main",
  "name": "Cơm gà xối mỡ",
  "description": "Gà chiên giòn, cơm thơm, dưa chua.",
  "price": 45000,
  "imageUrl": "https://example.com/com-ga.jpg",
  "isAvailable": true,
  "tags": ["phổ biến"]
}
```

Response: `201 Created` và menu item vừa tạo.

### PUT `/api/admin/menu-items/{menuItemId}`

Request: cùng shape với `POST /api/admin/menu-items`.

Response: menu item sau khi cập nhật.

### PATCH `/api/admin/menu-items/{menuItemId}/availability`

Request:

```json
{
  "isAvailable": false
}
```

Response: menu item sau khi đổi availability.

### DELETE `/api/admin/menu-items/{menuItemId}`

Response:

- `204 No Content` nếu xóa thành công.
- `404` với `MENU_ITEM_NOT_FOUND` nếu không tìm thấy.

## 7. Orders

Order endpoints là contract cho member triển khai Week 2. Nếu backend chưa có code tương ứng, frontend chỉ được mock theo đúng shape dưới đây.

### POST `/api/orders`

Mục đích: tạo đơn từ QR dine-in, pickup hoặc delivery mock.

Request:

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

Request cho `Pickup`:

```json
{
  "orderType": "Pickup",
  "tableCode": null,
  "paymentMethod": "COD",
  "deliveryInfo": null,
  "items": [
    {
      "menuItemId": "m_002",
      "quantity": 1
    }
  ]
}
```

Request cho `DeliveryMock`:

```json
{
  "orderType": "DeliveryMock",
  "tableCode": null,
  "paymentMethod": "COD",
  "deliveryInfo": {
    "recipientName": "Nguyen Van A",
    "phoneNumber": "0900000000",
    "address": "12 Nguyen Trai, Quan 1",
    "note": "Giao trong gio hanh chinh"
  },
  "items": [
    {
      "menuItemId": "m_009",
      "quantity": 2
    }
  ]
}
```

Response `201 Created`:

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Placed",
  "paymentStatus": "Unpaid",
  "subtotalAmount": 90000,
  "totalAmount": 90000,
  "createdAt": "2026-06-05T08:05:00Z",
  "items": [
    {
      "orderItemId": "oi_001",
      "menuItemId": "m_001",
      "name": "Cơm gà xối mỡ",
      "unitPrice": 45000,
      "quantity": 2,
      "status": "Pending",
      "lineTotal": 90000
    }
  ]
}
```

Quy tắc nghiệp vụ:

- `items` phải có ít nhất một dòng.
- `quantity` phải lớn hơn hoặc bằng `1`.
- Backend phải từ chối món không còn hàng bằng `MENU_ITEM_UNAVAILABLE`.
- Customer chỉ được hủy trước khi đơn/món chuyển sang `Preparing`.
- Backend chan status `Cancelled` bang `ORDER_CANCEL_NOT_ALLOWED` neu order hoac bat ky item nao da toi `Preparing`.
- `DineIn` yêu cầu `tableCode` hợp lệ và đang active.
- `Pickup` không cần `tableCode`, không cần `deliveryInfo`.
- `DeliveryMock` yêu cầu `recipientName`, `phoneNumber` và `address`.
- `MockOnline` chỉ mô phỏng; không gọi cổng thanh toán thật trong v1.

### GET `/api/orders/{orderCode}`

Mục đích: customer tracking screen và admin/staff đối chiếu chi tiết đơn.

Response `200 OK`:

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Preparing",
  "paymentStatus": "Unpaid",
  "paymentMethod": "COD",
  "deliveryInfo": null,
  "subtotalAmount": 90000,
  "totalAmount": 90000,
  "createdAt": "2026-06-05T08:05:00Z",
  "updatedAt": "2026-06-05T08:10:00Z",
  "items": [
    {
      "orderItemId": "oi_001",
      "menuItemId": "m_001",
      "name": "Cơm gà xối mỡ",
      "unitPrice": 45000,
      "quantity": 2,
      "status": "Preparing",
      "lineTotal": 90000,
      "updatedAt": "2026-06-05T08:10:00Z"
    }
  ],
  "events": [
    {
      "status": "Placed",
      "createdAt": "2026-06-05T08:05:00Z"
    }
  ]
}
```

Nếu không tìm thấy, trả `404` với `ORDER_NOT_FOUND`.

### PATCH `/api/orders/{orderCode}/status`

Purpose: Staff/Admin update the overall order status and backend emits `order.statusChanged`.

Auth: `Authorization: Bearer <accessToken>` with role `Staff` or `Admin`.

Request:

```json
{
  "status": "Preparing"
}
```

Response `200 OK`: same shape as `GET /api/orders/{orderCode}` after update.

Errors:

- `401 Unauthorized` when no valid token is provided.
- `403 Forbidden` when the token role is not `Staff` or `Admin`.
- `400` with `ORDER_STATUS_INVALID` when `status` is not a valid `OrderStatus`.
- `400` with `ORDER_CANCEL_NOT_ALLOWED` when cancelling after the order or any item reaches `Preparing`.
- `404` with `ORDER_NOT_FOUND` when `orderCode` does not exist.

### PATCH `/api/orders/{orderCode}/items/{orderItemId}/status`

Purpose: Kitchen/Staff/Admin update one dish status and backend emits `order.itemStatusChanged`.

Auth: `Authorization: Bearer <accessToken>` with role `Kitchen`, `Staff`, or `Admin`.

Request:

```json
{
  "status": "Ready"
}
```

Response `200 OK`: same shape as `GET /api/orders/{orderCode}` after update.

Errors:

- `401 Unauthorized` when no valid token is provided.
- `403 Forbidden` when the token role is not `Kitchen`, `Staff`, or `Admin`.
- `400` with `ORDER_ITEM_STATUS_INVALID` when `status` is not a valid `OrderItemStatus`.
- `404` with `ORDER_NOT_FOUND` when `orderCode` does not exist.
- `404` with `ORDER_ITEM_NOT_FOUND` when `orderItemId` does not exist in the order.

## 8. Chat / AI

Chi tiết thiết kế LLM, RAG và guardrails nằm ở `docs/AI_CHATBOT.md`. Contract trong mục này là ràng buộc tối thiểu cho backend, frontend và dữ liệu mock.

### 8.1. Provider Và Môi Trường

- LLM provider dùng `9router`.
- Local hiện tại: backend local gọi 9router local qua `AI_BASE_URL=http://127.0.0.1:<9router_port>`.
- CI/build test dùng mock/stub AI, không cần API key thật và không gọi provider thật.
- Production/VPS: backend và 9router chạy cùng VPS hoặc cùng private network; backend gọi 9router bằng URL nội bộ.
- Frontend không gọi 9router trực tiếp và không lưu API key.
- Backend gọi 9router theo OpenAI-compatible endpoint `{AI_BASE_URL}/chat/completions`; ví dụ local `AI_BASE_URL=http://localhost:20128/v1`.

Biến môi trường backend dự kiến:

```env
AI_PROVIDER=9router
AI_BASE_URL=http://127.0.0.1:<9router_port>
AI_API_KEY=<secret>
AI_MODEL=<model_name>
AI_TIMEOUT_SECONDS=60
AI_MAX_RETRY=1
```

### 8.2. KnowledgeEntry Cho RAG

`KnowledgeEntry` là shape chuẩn cho menu, FAQ, policy và insight được đưa vào retrieval context.

```json
{
  "id": "menu:m_001",
  "source": "menu",
  "title": "Cơm gà xối mỡ",
  "content": "Cơm gà xối mỡ giá 45000 VND, thuộc nhóm Món chính, còn bán.",
  "metadata": {
    "menuItemId": "m_001",
    "categoryId": "cat_main",
    "categoryName": "Món chính",
    "price": 45000,
    "isAvailable": true,
    "tags": ["phổ biến"]
  },
  "updatedAt": "2026-06-05T00:00:00Z"
}
```

Quy tắc RAG:

- `source` hợp lệ: `menu`, `faq`, `policy`, `insight`.
- Giá, tên món và trạng thái còn/hết phải lấy từ menu hiện tại.
- Món `isAvailable=false` không được xuất hiện trong `suggestedCartActions`.
- Nếu context không có thông tin, chatbot phải fallback thay vì tự suy đoán.

### 8.3. POST `/api/chat/sessions`

Mục đích: tạo phiên chat.

Response `201 Created`:

```json
{
  "chatSessionId": "chat_001",
  "createdAt": "2026-06-05T08:00:00Z"
}
```

### 8.4. POST `/api/chat/sessions/{chatSessionId}/messages`

Mục đích: gửi tin nhắn của khách và nhận phản hồi từ chatbot.

Request:

```json
{
  "content": "Gợi ý món cho 2 người",
  "tableCode": "T05"
}
```

Response `200 OK`:

```json
{
  "message": {
    "id": "msg_002",
    "role": "assistant",
    "content": "Bạn có thể chọn Cơm gà xối mỡ và Trà đào cam sả. Mình chỉ đề xuất, bạn cần xác nhận trước khi thêm vào giỏ.",
    "createdAt": "2026-06-05T08:01:00Z"
  },
  "suggestedCartActions": [
    {
      "menuItemId": "m_001",
      "name": "Cơm gà xối mỡ",
      "price": 45000,
      "quantity": 1,
      "reason": "Món phổ biến, phù hợp bữa chính.",
      "requiresCustomerConfirmation": true
    }
  ],
  "guardrailFlags": []
}
```

Fallback khi AI provider lỗi hoặc timeout:

```json
{
  "message": {
    "id": "msg_003",
    "role": "assistant",
    "content": "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống.",
    "createdAt": "2026-06-05T08:02:00Z"
  },
  "suggestedCartActions": [],
  "guardrailFlags": ["AI_PROVIDER_UNAVAILABLE"]
}
```

Quy tắc:

- Chatbot được đề xuất `suggestedCartActions`, nhưng không tự thêm món vào giỏ.
- Customer phải xác nhận trước khi món được thêm vào giỏ.
- Chatbot không được đặt đơn hoặc thanh toán.
- Chatbot không được bịa món, giá, khuyến mãi hoặc món đã hết hàng.
- Backend phải validate lại `menuItemId`, `name`, `price`, `quantity` và `isAvailable` trước khi trả action cho frontend.
- `requiresCustomerConfirmation` luôn là `true`.

### 8.5. GET `/api/chat/sessions/{chatSessionId}/messages`

Mục đích: lấy lịch sử tin nhắn của một phiên chat.

Response `200 OK`:

```json
{
  "chatSessionId": "chat_001",
  "createdAt": "2026-06-05T08:00:00Z",
  "updatedAt": "2026-06-05T08:01:00Z",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "Gợi ý món cho 2 người",
      "createdAt": "2026-06-05T08:01:00Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "Bạn có thể chọn Cơm gà xối mỡ. Mình chỉ đề xuất, bạn cần xác nhận trước khi thêm vào giỏ.",
      "createdAt": "2026-06-05T08:01:01Z"
    }
  ]
}
```

Nếu không tìm thấy phiên chat, trả `404` với `CHAT_SESSION_NOT_FOUND`.

### 8.6. Sample Guardrail Cases

| Case | Input | Expected |
| --- | --- | --- |
| Món có thật và còn bán | "Có cơm gà không?" | Trả lời đúng tên, giá và trạng thái theo menu. |
| Món không tồn tại | "Có pizza hải sản không?" | Không bịa món; nói menu hiện tại chưa có thông tin. |
| Món hết hàng | "Thêm món đang hết hàng vào giỏ" | Không trả `suggestedCartActions` cho món hết hàng. |
| Ngoài phạm vi | "Viết code Python giúp tôi" | Từ chối nhẹ và kéo về hỗ trợ chọn món/FAQ nhà hàng. |

## 9. SignalR Events

Hub: `/hubs/orders`.

Client subscriptions:

- Operations roles (`Kitchen`, `Staff`, `Admin`) are added to the operations group after connecting with a valid JWT.
- Customers/anonymous tracking clients call `WatchOrder(orderCode, tableCode)` to join only that order. For dine-in orders, `tableCode` must match the order table.
- Customers/anonymous table screens call `WatchTable(tableCode)` to join an active table group.
- Events are sent only to order, table, and operations groups; there is no broadcast to all connected clients.

### `order.created`

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Placed",
  "createdAt": "2026-06-05T08:05:00Z"
}
```

### `order.statusChanged`

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "status": "Preparing",
  "updatedAt": "2026-06-05T08:10:00Z"
}
```

### `order.itemStatusChanged`

```json
{
  "orderId": "ord_1024",
  "orderCode": "ORD-1024",
  "orderItemId": "oi_001",
  "menuItemName": "Cơm gà xối mỡ",
  "status": "Ready",
  "updatedAt": "2026-06-05T08:18:00Z"
}
```

Manual SignalR verification sample:

1. Connect to `/hubs/orders`.
2. Call `WatchOrder("ORD-1001", "T05")` or `WatchTable("T05")`.
3. Update `PATCH /api/orders/ORD-1001/items/oi_001/status` with a `Kitchen`, `Staff`, or `Admin` token.
4. Expected client event:

```json
{
  "event": "order.itemStatusChanged",
  "payload": {
    "orderId": "ord_1001",
    "orderCode": "ORD-1001",
    "orderItemId": "oi_001",
    "menuItemName": "Com ga xoi mo",
    "status": "Ready",
    "updatedAt": "2026-06-05T08:18:00Z"
  }
}
```

## 10. Seed Data Plan Tuần 2

Seed data tuần 2 phải hỗ trợ đủ 4 demo: QR customer order, menu/admin management, online pickup/delivery mock và chatbot RAG.

### 10.1. Tables

| Table code | Display name | Active | QR route demo |
| --- | --- | --- | --- |
| `T01` | `Bàn 01` | `true` | `/table/T01` |
| `T02` | `Bàn 02` | `true` | `/table/T02` |
| `T03` | `Bàn 03` | `true` | `/table/T03` |
| `T04` | `Bàn 04` | `true` | `/table/T04` |
| `T05` | `Bàn 05` | `true` | `/table/T05` |
| `T06` | `Bàn 06` | `true` | `/table/T06` |
| `T07` | `Bàn 07` | `true` | `/table/T07` |
| `T08` | `Bàn 08` | `true` | `/table/T08` |

Ghi chú:

- `qrToken` có thể seed dạng `qr-demo-t01` đến `qr-demo-t08`, nhưng frontend v1 vẫn dùng `tableCode`.
- Không seed table inactive trong demo mặc định để tránh làm rối luồng QR.

### 10.2. Categories

| Category ID | Name | Display order | Active | Demo dùng cho |
| --- | --- | --- | --- | --- |
| `cat_appetizer` | `Khai vi` | `10` | `true` | Menu, chatbot goi y mon nhe. |
| `cat_main` | `Mon chinh` | `20` | `true` | QR order, pickup. |
| `cat_noodle` | `Pho va bun` | `30` | `true` | Chatbot hoi mon nong. |
| `cat_seafood` | `Hai san` | `40` | `true` | Delivery mock, nhom khach. |
| `cat_drink` | `Do uong` | `50` | `true` | Combo/goi y kem mon. |
| `cat_dessert` | `Trang mieng` | `60` | `true` | Upsell chatbot. |

### 10.3. Menu Items

| ID | Category | Name | Price | Available | Tags demo |
| --- | --- | --- | ---: | --- | --- |
| `m_001` | `cat_main` | `Com ga xoi mo` | `45000` | `true` | `pho bien`, `mon chinh`, `signature` |
| `m_002` | `cat_main` | `Com suon nuong` | `52000` | `true` | `pho bien`, `nuong` |
| `m_003` | `cat_noodle` | `Pho bo tai` | `55000` | `true` | `nong`, `pho`, `bo` |
| `m_004` | `cat_noodle` | `Bun bo Hue` | `60000` | `false` | `cay`, `het hang`, `unavailable-demo` |
| `m_005` | `cat_appetizer` | `Goi cuon tom thit` | `39000` | `true` | `fresh`, `light` |
| `m_006` | `cat_appetizer` | `Cha gio hai san` | `42000` | `true` | `chien gion`, `seafood` |
| `m_007` | `cat_seafood` | `Tom rang muoi` | `185000` | `true` | `seafood`, `share` |
| `m_008` | `cat_seafood` | `Lau Thai hai san` | `345000` | `true` | `spicy`, `seafood`, `share` |
| `m_009` | `cat_drink` | `Tra dao cam sa` | `55000` | `true` | `drink`, `fresh` |
| `m_010` | `cat_drink` | `Ca phe sua da` | `45000` | `false` | `drink`, `coffee`, `unavailable-demo` |
| `m_011` | `cat_dessert` | `Che khuc bach` | `55000` | `true` | `sweet`, `cool` |
| `m_012` | `cat_dessert` | `Banh flan caramel` | `35000` | `true` | `sweet`, `classic` |

Seed descriptions và image URL có thể khác nhau theo môi trường, nhưng ID, category, price, `isAvailable` và tags demo phải thống nhất để frontend, admin và chatbot test cùng dữ liệu.

## 11. Manual Integration Scenarios

Checklist chi tiết nằm ở [docs/TEST_PLAN.md](TEST_PLAN.md). Tối thiểu phải có 4 scenario trước khi Week 2 merge:

- QR customer order từ `/table/T05`.
- Online pickup từ `/menu`.
- Delivery mock với `deliveryInfo`.
- Admin đổi `isAvailable` và kiểm tra customer/chatbot không đặt món hết hàng.

## 12. Contract Drift Review

Kiểm tra ngày `2026-06-05` bằng `gh pr list --repo Anpham120/restaurant-qr-ai-ordering --state open --json number,title,headRefName,baseRefName,author,url,updatedAt`: kết quả `[]`, tức là không có PR mở tại thời điểm kiểm tra nên không có drift từ PR mở.

Drift/risk đang thấy trong code hiện tại nhưng không sửa trong issue #10 vì đây là docs-only:

- Frontend admin mock đang dùng `tableCode: "T-05"`; contract chuẩn là `T05`.
- Frontend admin mock đang dùng `paymentStatus: "Pending"`; contract chuẩn là `Unpaid`, `Paid`, `Failed`, `Cancelled`.
- Frontend menu type/mock đang dùng ID `mi-001` và thiếu `categoryId`; contract/backend DTO chuẩn dùng `m_001` và có `categoryId`.
- Backend hiện có auth/menu/table foundation; order/chat/realtime endpoints trong tài liệu là contract để member triển khai tiếp, không phải bằng chứng endpoint đã hoàn thành trong issue #10.
- Cac frontend drift items o tren van con ton tai vi frontend/** thuoc Do Not Touch trong issue #18. Can frontend team sua trong issue rieng.

## 13. Issue #18 Integration Review Notes

Ket qua review backend truoc final demo:

- EF Core migration: backend hien tai chua co EF Core `DbContext`, package EF Core hoac thu muc migration. Data demo dang la in-memory store trong API process, nen khong co migration de apply vao local/test DB trong issue nay.
- Migration/schema risk: khong tao destructive migration va khong sua schema persistence vi EF pipeline chua ton tai.
- Seed tables: `T01` den `T08` active, `qrToken` dang seed `qr-demo-t01` den `qr-demo-t08`; API table chi chap nhan `T01` den `T99`.
- Seed menu: 6 category active va 12 menu item demo, co ca item available/unavailable de test order, admin availability va chatbot guardrail.
- Roles: role catalog co `Customer`, `Staff`, `Kitchen`, `Admin`. Demo Admin/Staff/Kitchen login account chua seed trong code vi auth user store nam ngoai allowed files cua issue #18.
- Demo admin/staff/kitchen accounts: UserStore nam trong thu muc Users/ khong thuoc allowed files cua issue #18 (chi cho phep Data/, Orders/, Menu/, Tables/, Chat/), nen khong seed demo accounts trong issue nay. Can tao issue rieng hoac xin Lead approval neu muon bo sung.
- API contract fixes: bo sung error codes backend dang tra (`CATEGORY_NAME_REQUIRED`, enum invalid codes, `ORDER_ITEM_NOT_FOUND`, `CHAT_MESSAGE_EMPTY`, `CHAT_SESSION_NOT_FOUND`) va dong bo seed menu/category voi backend response.
- Status persistence: order status va order item status duoc luu trong `OrderStore` in-memory va GET `/api/orders/{orderCode}` tra lai trang thai moi trong cung API process.
- Limitation: vi data in-memory, restart API se reset orders, chat sessions, admin menu changes va user registers.
