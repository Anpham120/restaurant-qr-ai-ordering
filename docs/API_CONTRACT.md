# API Contract

Tai lieu nay la hop dong giua Backend, Frontend, AI va Realtime. Neu muon doi endpoint, field, enum hoac event payload, phai bao Lead va cap nhat tai lieu nay.

## 1. Common Rules

- API base path: `/api`.
- Response JSON dung camelCase.
- Frontend khong goi `fetch` rai rac trong component; phai di qua service layer.
- Backend khong tra truc tiep entity database neu response can on dinh; dung DTO.
- Mock data frontend phai dung cung shape voi contract nay.

## 2. Auth

### POST `/api/auth/register`

Purpose: tao tai khoan customer.

Request draft:

```json
{
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "password": "Password123!"
}
```

Response draft:

```json
{
  "userId": "usr_001",
  "fullName": "Nguyen Van A",
  "email": "customer@example.com",
  "role": "Customer"
}
```

### POST `/api/auth/login`

Response draft:

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

Roles:

- `Customer`
- `Staff`
- `Kitchen`
- `Admin`

## 3. Tables / QR

### GET `/api/tables/{tableCode}`

Purpose: lay thong tin ban khi khach vao tu QR route `/table/:tableCode`.

Response draft:

```json
{
  "tableCode": "T05",
  "displayName": "Ban 05",
  "isActive": true
}
```

## 4. Menu

### GET `/api/menu`

Purpose: lay menu cho customer, admin va chatbot.

Response draft:

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

Menu item fields must stay aligned with frontend mocks and chatbot RAG data.

## 5. Orders

### POST `/api/orders`

Purpose: tao don tu QR dine-in, pickup hoac delivery mock.

Request draft:

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

Response draft:

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

Business rules:

- Backend must reject unavailable menu items.
- Customer can cancel only before order/item moves to `Preparing`.
- `DineIn` requires valid active `tableCode`.
- `DeliveryMock` requires delivery contact/address fields.

### GET `/api/orders/{orderCode}`

Purpose: customer tracking screen.

Response shape should match create order response plus timestamps and current item statuses.

## 6. Chat

### POST `/api/chat/sessions`

Response draft:

```json
{
  "chatSessionId": "chat_001",
  "createdAt": "2026-06-04T08:00:00Z"
}
```

### POST `/api/chat/sessions/{chatSessionId}/messages`

Request draft:

```json
{
  "content": "Goi y mon cho 2 nguoi",
  "tableCode": "T05"
}
```

Response draft:

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

Rules:

- Chatbot can suggest cart actions.
- Customer must confirm before item is added.
- Chatbot cannot place order or pay.
- Chatbot must not invent dishes, prices, or unavailable items.

## 7. SignalR Events

Hub draft: `/hubs/orders`

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

## 8. Error Shape

Draft:

```json
{
  "error": {
    "code": "MENU_ITEM_UNAVAILABLE",
    "message": "Menu item is unavailable.",
    "details": {}
  }
}
```

Frontend must show user-friendly error messages and must not depend on database exception text.

