# Hop Dong API - CMC Restaurant

Tai lieu nay la contract chinh thuc giua Backend, Frontend, AI service va DevOps cho giai doan Week 5. Neu thay doi endpoint, field, enum, error code hoac event payload sau tai lieu nay, nguoi thuc hien phai tao breaking-change note trong issue/PR lien quan.

## 1. Nguyen Tac Chung

- Base API path: `/api`.
- JSON response dung `camelCase`.
- Thoi gian dung ISO 8601 UTC, vi du `2026-06-14T04:00:00Z`.
- Tien te la VND; `price`, `amount`, `subtotalAmount`, `totalAmount` la number/decimal khong am.
- Frontend production khong duoc tu suy luan contract tu mock data. Component phai di qua service layer.
- UI production khong hien raw API payload, debug JSON, secret, token hoac provider key.
- Endpoint protected phai gui header `Authorization: Bearer <accessToken>`.
- OpenAPI duoc expose o moi truong Development qua `app.MapOpenApi()`; tai lieu nay la ban freeze de review/lam viec nhom.

## 2. Response Va Error Format

Thanh cong tra ve DTO cu the cua endpoint. Loi business/validation dung shape:

```json
{
  "error": {
    "code": "MENU_ITEM_UNAVAILABLE",
    "message": "Menu item is unavailable.",
    "details": {}
  }
}
```

Quy tac:

- `error.code` dung UPPER_SNAKE_CASE va on dinh de frontend map thong bao than thien.
- `error.message` la message ky thuat/van hanh; frontend khong duoc phu thuoc logic vao message.
- Body invalid hoac JSON sai tra `400 REQUEST_INVALID`.

## 3. Shared Enum

| Nhom | Gia tri hop le | Ghi chu |
| --- | --- | --- |
| `UserRole` | `Customer`, `Staff`, `Kitchen`, `Admin` | `Customer` cho khach; cac role van hanh dung auth seed/admin. |
| `OrderType` | `DineIn`, `Pickup`, `DeliveryMock` | `DineIn` can `tableCode`; `DeliveryMock` can `deliveryInfo`. UI co the hien la "Giao tan noi". |
| `PaymentMethod` | `COD`, `VietQR` | VietQR tao payload/QR de doi soat thu cong. |
| `PaymentStatus` | `Unpaid`, `Pending`, `Paid`, `Confirmed`, `Failed`, `Cancelled` | Staff/Admin xac nhan hoac fail payment. |
| `OrderStatus` | `Draft`, `Placed`, `Confirmed`, `Preparing`, `Ready`, `Served`, `Delivering`, `Delivered`, `Completed`, `Cancelled` | Tracking UI phai xu ly du cac status nay. |
| `OrderItemStatus` | `Pending`, `Preparing`, `Ready`, `Served`, `Cancelled` | Kitchen/Staff cap nhat tung mon. |
| `ChatRole` | `user`, `assistant` | Theo chuan message role cua chat. |
| `TableCode` | `T01` den `T99` hoac seed hien hanh cua DB | QR/token phai map ve table active. |

## 4. Auth Contract

### POST `/api/auth/register`

Auth: public.

Request:

```json
{
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "password": "12345678"
}
```

Response `200 OK`:

```json
{
  "userId": "usr_001",
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "role": "Customer"
}
```

Loi chinh: `FULL_NAME_REQUIRED`, `EMAIL_REQUIRED`, `EMAIL_INVALID`, `PASSWORD_REQUIRED`, `PASSWORD_TOO_SHORT`, `EMAIL_ALREADY_REGISTERED`.

### POST `/api/auth/login`

Auth: public.

Request:

```json
{
  "email": "admin@cmc.test",
  "password": "Admin@123"
}
```

Response `200 OK`:

```json
{
  "accessToken": "<jwt>",
  "expiresAt": "2026-06-14T12:00:00Z",
  "user": {
    "userId": "usr_admin",
    "fullName": "Admin CMC",
    "email": "admin@cmc.test",
    "role": "Admin"
  }
}
```

Loi chinh: `EMAIL_REQUIRED`, `PASSWORD_REQUIRED`, `INVALID_CREDENTIALS`.

### GET `/api/auth/me`

Auth: any authenticated user.

Response `200 OK`:

```json
{
  "userId": "usr_admin",
  "fullName": "Admin CMC",
  "email": "admin@cmc.test",
  "role": "Admin"
}
```

### GET `/api/auth/admin-check`

Auth: role `Admin`.

Response:

```json
{ "status": "ok", "requiredRole": "Admin" }
```

## 5. Menu Va Category Contract

### GET `/api/menu`

Auth: public. Chi tra category active va item con ban.

Response:

```json
{
  "categories": [
    { "categoryId": "cat_main", "name": "Mon chinh" }
  ],
  "items": [
    {
      "id": "m_001",
      "name": "Pho bo dac biet",
      "description": "Pho bo truyen thong",
      "price": 65000,
      "categoryId": "cat_main",
      "categoryName": "Mon chinh",
      "imageUrl": "https://...",
      "isAvailable": true,
      "tags": ["noodle", "beef"]
    }
  ]
}
```

### Admin Category Endpoints

Auth: role `Staff` hoac `Admin`.

| Method | Path | Muc dich |
| --- | --- | --- |
| GET | `/api/admin/categories` | Lay danh sach category. |
| GET | `/api/admin/categories/{categoryId}` | Lay chi tiet category. |
| POST | `/api/admin/categories` | Tao category. |
| PUT | `/api/admin/categories/{categoryId}` | Cap nhat category. |
| DELETE | `/api/admin/categories/{categoryId}` | Xoa category neu chua co item. |

Category request:

```json
{
  "name": "Hai san",
  "displayOrder": 40,
  "isActive": true
}
```

Category response:

```json
{
  "categoryId": "cat_hai_san",
  "name": "Hai san",
  "displayOrder": 40,
  "isActive": true,
  "createdAt": "2026-06-14T04:00:00Z",
  "updatedAt": "2026-06-14T04:00:00Z"
}
```

Loi chinh: `CATEGORY_NAME_REQUIRED`, `CATEGORY_NOT_FOUND`, `CATEGORY_HAS_MENU_ITEMS`.

### Admin Menu Item Endpoints

Auth: role `Staff` hoac `Admin`.

| Method | Path | Muc dich |
| --- | --- | --- |
| GET | `/api/admin/menu-items?includeInactiveCategories=true` | Lay menu item cho admin. |
| GET | `/api/admin/menu-items/{menuItemId}` | Lay chi tiet item. |
| POST | `/api/admin/menu-items` | Tao item. |
| PUT | `/api/admin/menu-items/{menuItemId}` | Cap nhat item. |
| PATCH | `/api/admin/menu-items/{menuItemId}/availability` | Bat/tat trang thai con mon. |
| DELETE | `/api/admin/menu-items/{menuItemId}` | Xoa item. |

Menu item request:

```json
{
  "categoryId": "cat_main",
  "name": "Pho bo dac biet",
  "description": "Pho bo truyen thong",
  "price": 65000,
  "imageUrl": "https://...",
  "isAvailable": true,
  "tags": ["noodle", "beef"]
}
```

Toggle availability:

```json
{ "isAvailable": false }
```

Loi chinh: `CATEGORY_REQUIRED`, `CATEGORY_INVALID`, `MENU_ITEM_NAME_REQUIRED`, `MENU_ITEM_PRICE_INVALID`, `MENU_ITEM_NOT_FOUND`.

## 6. Table Va Table Session Contract

### GET `/api/tables/{tableCode}`

Auth: public.

Response:

```json
{
  "tableCode": "T05",
  "displayName": "Ban T05",
  "isActive": true
}
```

### GET `/api/tables/qr/{qrToken}`

Auth: public. Resolve QR token sang table active.

### POST `/api/table-sessions`

Auth: public.

Request:

```json
{
  "tableCode": "T05",
  "orderType": "DineIn"
}
```

Pickup session co the gui:

```json
{ "orderType": "Pickup" }
```

Response:

```json
{
  "sessionId": "ts_abc123",
  "tableCode": "T05",
  "orderType": "DineIn",
  "status": "Open",
  "openedAt": "2026-06-14T04:00:00Z",
  "closedAt": null
}
```

### GET `/api/table-sessions/{sessionId}`

Auth: public. Lay session hien tai.

### POST `/api/table-sessions/{sessionId}/close`

Auth: public trong backend hien tai; UI van nen chi goi khi user ket thuc flow.

Loi chinh: `TABLE_CODE_INVALID`, `TABLE_NOT_FOUND`, `ORDER_TYPE_INVALID`, `TABLE_SESSION_NOT_FOUND`, `TABLE_SESSION_CLOSED`.

## 7. Order Contract

### POST `/api/orders`

Auth: public. Tao don tu customer cart.

Request:

```json
{
  "orderType": "DineIn",
  "tableCode": "T05",
  "paymentMethod": "COD",
  "deliveryInfo": null,
  "items": [
    { "menuItemId": "m_001", "quantity": 2 }
  ]
}
```

Delivery request:

```json
{
  "orderType": "DeliveryMock",
  "tableCode": null,
  "paymentMethod": "VietQR",
  "deliveryInfo": {
    "recipientName": "Nguyen Van A",
    "phoneNumber": "0901234567",
    "address": "1 Nguyen Trai, Ha Noi",
    "note": "It cay"
  },
  "items": [
    { "menuItemId": "m_002", "quantity": 1 }
  ]
}
```

Response `201 Created`:

```json
{
  "orderId": "ord_abc123",
  "orderCode": "ORD-1001",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Placed",
  "paymentStatus": "Unpaid",
  "items": [
    {
      "orderItemId": "oi_001",
      "menuItemId": "m_001",
      "name": "Pho bo dac biet",
      "quantity": 2,
      "status": "Pending"
    }
  ]
}
```

Loi chinh: `ORDER_ITEMS_REQUIRED`, `ORDER_ITEM_QUANTITY_INVALID`, `ORDER_TYPE_INVALID`, `PAYMENT_METHOD_INVALID`, `DINE_IN_TABLE_REQUIRED`, `DELIVERY_INFO_REQUIRED`, `MENU_ITEM_NOT_FOUND`, `MENU_ITEM_UNAVAILABLE`.

### GET `/api/orders/{orderCode}`

Auth: public. Dung cho customer tracking.

Response:

```json
{
  "orderId": "ord_abc123",
  "orderCode": "ORD-1001",
  "orderType": "DineIn",
  "tableCode": "T05",
  "status": "Preparing",
  "paymentStatus": "Unpaid",
  "paymentMethod": "COD",
  "deliveryInfo": null,
  "subtotalAmount": 130000,
  "totalAmount": 130000,
  "createdAt": "2026-06-14T04:00:00Z",
  "updatedAt": "2026-06-14T04:05:00Z",
  "items": [
    {
      "orderItemId": "oi_001",
      "menuItemId": "m_001",
      "name": "Pho bo dac biet",
      "unitPrice": 65000,
      "quantity": 2,
      "status": "Preparing",
      "lineTotal": 130000,
      "updatedAt": "2026-06-14T04:05:00Z"
    }
  ],
  "events": [
    { "status": "Placed", "createdAt": "2026-06-14T04:00:00Z" }
  ]
}
```

### GET `/api/orders`

Auth: role `Staff`, `Kitchen` hoac `Admin`.

Query optional: `status`, `orderType`, `tableCode`, `fromUtc`, `toUtc`, `page`, `pageSize`.

Response:

```json
{
  "orders": [],
  "total": 0
}
```

### PATCH `/api/orders/{orderCode}/status`

Auth: role `Staff` hoac `Admin`.

Request:

```json
{ "status": "Confirmed" }
```

### PATCH `/api/orders/{orderCode}/items/{orderItemId}/status`

Auth: role `Kitchen`, `Staff` hoac `Admin`.

Request:

```json
{ "status": "Ready" }
```

Loi chinh: `ORDER_NOT_FOUND`, `ORDER_STATUS_INVALID`, `ORDER_ITEM_NOT_FOUND`, `ORDER_ITEM_STATUS_INVALID`, `ORDER_CANCEL_NOT_ALLOWED`.

## 8. Payment Contract

### GET `/api/orders/{orderCode}/payment`

Auth: public.

Response:

```json
{
  "paymentId": "pay_001",
  "orderCode": "ORD-1001",
  "method": "VietQR",
  "status": "Pending",
  "amount": 130000,
  "providerTransactionId": "CMC-ORD-1001",
  "createdAt": "2026-06-14T04:00:00Z",
  "paidAt": null,
  "updatedAt": "2026-06-14T04:05:00Z",
  "transactions": []
}
```

### POST `/api/orders/{orderCode}/payment/vietqr`

Auth: public. Chi dung khi order payment method la `VietQR`.

Response:

```json
{
  "orderCode": "ORD-1001",
  "amount": 130000,
  "transferContent": "CMC ORD-1001",
  "bankId": "970436",
  "accountNumber": "123456789",
  "accountName": "CMC Restaurant",
  "quickLink": "https://img.vietqr.io/...",
  "qrPayload": "000201...",
  "qrImageDataUri": "data:image/png;base64,...",
  "paymentStatus": "Pending"
}
```

### POST `/api/orders/{orderCode}/payment/confirm`

Auth: role `Staff` hoac `Admin`.

Request:

```json
{
  "providerTransactionId": "BANK-TX-001",
  "note": "Da doi soat"
}
```

### POST `/api/orders/{orderCode}/payment/fail`

Auth: role `Staff` hoac `Admin`.

Request:

```json
{ "note": "Khach huy thanh toan" }
```

Loi chinh: `PAYMENT_NOT_FOUND`, `PAYMENT_METHOD_INVALID`, `PAYMENT_ALREADY_CONFIRMED`, `PAYMENT_ALREADY_FAILED`, `VIETQR_CONFIG_MISSING`.

## 9. Kitchen, Staff Va Realtime Contract

Kitchen/Staff khong co endpoint rieng ngoai order endpoints:

- Staff board doc `GET /api/orders`.
- Staff confirm order doc `PATCH /api/orders/{orderCode}/status`.
- Kitchen board doc `GET /api/orders` va `PATCH /api/orders/{orderCode}/items/{orderItemId}/status`.
- Payment counter doc `POST /api/orders/{orderCode}/payment/confirm`.

SignalR:

- Hub path: `/hubs/orders`.
- Event tu backend den client:

```json
{
  "event": "order.itemStatusChanged",
  "payload": {
    "orderId": "ord_abc123",
    "orderCode": "ORD-1001",
    "orderItemId": "oi_001",
    "menuItemName": "Pho bo dac biet",
    "status": "Ready",
    "updatedAt": "2026-06-14T04:10:00Z"
  }
}
```

Event names:

- `order.created`
- `order.statusChanged`
- `order.itemStatusChanged`

## 10. AI Chat Contract

### POST `/api/chat/sessions`

Auth: public.

Response `201 Created`:

```json
{
  "chatSessionId": "chat_abc123",
  "createdAt": "2026-06-14T04:00:00Z"
}
```

### POST `/api/chat/sessions/{chatSessionId}/messages`

Auth: public. Backend goi AI provider qua service rieng; frontend khong goi 9router/provider truc tiep.

Request:

```json
{
  "content": "Goi y mon cho 2 nguoi an trua",
  "tableCode": "T05"
}
```

Response:

```json
{
  "message": {
    "id": "msg_002",
    "role": "assistant",
    "content": "Minh goi y pho bo va tra dao...",
    "createdAt": "2026-06-14T04:01:00Z"
  },
  "suggestedCartActions": [
    {
      "menuItemId": "m_001",
      "name": "Pho bo dac biet",
      "price": 65000,
      "quantity": 1,
      "reason": "Phu hop bua trua",
      "requiresCustomerConfirmation": true
    }
  ],
  "guardrailFlags": ["CUSTOMER_CONFIRMATION_REQUIRED"]
}
```

### GET `/api/chat/sessions/{chatSessionId}/messages`

Auth: public. Lay lich su session.

Guardrail bat buoc:

- AI chi de xuat, khong tu tao order.
- AI khong tu them item vao cart neu khach chua bam xac nhan.
- Neu menu item khong ton tai hoac unavailable, backend/frontend khong duoc bia mon/gia.
- Frontend khong hien raw prompt, raw provider response, API key hoac debug payload.

Loi chinh: `REQUEST_INVALID`, `CHAT_MESSAGE_EMPTY`, `CHAT_SESSION_NOT_FOUND`.

## 11. Health, CORS Va Deployment Contract

| Method | Path | Auth | Ghi chu |
| --- | --- | --- | --- |
| GET | `/api/health` | Public | Health JSON cua app. |
| GET | `/health/live` | Public | Liveness probe. |
| GET | `/health/ready` | Public | Readiness probe, co PostgreSQL neu config connection string. |

CORS origins mac dinh:

- `https://cmcrestaurant.app`
- `https://customer.cmcrestaurant.app`
- `https://admin.cmcrestaurant.app`
- `https://staging.cmcrestaurant.app`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

Production co the override bang `CORS_ALLOWED_ORIGINS`, ngan cach bang dau `;`.

## 12. Ma Loi Chinh

| HTTP | Code | Module |
| --- | --- | --- |
| 400 | `REQUEST_INVALID` | Shared |
| 400 | `EMAIL_REQUIRED`, `EMAIL_INVALID`, `PASSWORD_REQUIRED`, `PASSWORD_TOO_SHORT` | Auth |
| 401 | `INVALID_CREDENTIALS` | Auth |
| 409 | `EMAIL_ALREADY_REGISTERED` | Auth |
| 400 | `TABLE_CODE_INVALID`, `ORDER_TYPE_INVALID` | Table |
| 404 | `TABLE_NOT_FOUND`, `TABLE_SESSION_NOT_FOUND` | Table |
| 400 | `CATEGORY_NAME_REQUIRED`, `CATEGORY_REQUIRED`, `CATEGORY_INVALID` | Menu |
| 404 | `CATEGORY_NOT_FOUND`, `MENU_ITEM_NOT_FOUND` | Menu |
| 409 | `CATEGORY_HAS_MENU_ITEMS` | Menu |
| 400 | `MENU_ITEM_NAME_REQUIRED`, `MENU_ITEM_PRICE_INVALID`, `MENU_ITEM_UNAVAILABLE` | Menu/Order |
| 400 | `ORDER_ITEMS_REQUIRED`, `ORDER_ITEM_QUANTITY_INVALID`, `DINE_IN_TABLE_REQUIRED`, `DELIVERY_INFO_REQUIRED` | Order |
| 404 | `ORDER_NOT_FOUND`, `ORDER_ITEM_NOT_FOUND` | Order |
| 400 | `ORDER_STATUS_INVALID`, `ORDER_ITEM_STATUS_INVALID`, `ORDER_CANCEL_NOT_ALLOWED` | Order |
| 404 | `PAYMENT_NOT_FOUND` | Payment |
| 400 | `PAYMENT_METHOD_INVALID`, `PAYMENT_ALREADY_CONFIRMED`, `PAYMENT_ALREADY_FAILED`, `VIETQR_CONFIG_MISSING` | Payment |
| 400 | `CHAT_MESSAGE_EMPTY` | Chat |
| 404 | `CHAT_SESSION_NOT_FOUND` | Chat |

## 13. Checklist Cho Frontend

- Dung service layer cho moi endpoint, khong fetch truc tiep trong component.
- Loading/error/empty state phai hien thong bao than thien.
- LocalStorage chi duoc luu token/session/cart tam thoi tren client, khong lam source of truth cho order/menu/payment.
- Menu, order, payment, admin data production phai lay tu API.
- Khi them field moi vao DTO, cap nhat TypeScript type va tai lieu nay trong cung PR hoac PR lien quan.
- Neu response thay doi breaking, PR phai ghi ro migration impact cho frontend/admin/kitchen/AI.
