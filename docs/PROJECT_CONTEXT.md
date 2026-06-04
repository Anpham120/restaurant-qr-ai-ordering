# Project Context

## 1. De Tai

Ten du an: Restaurant QR AI Ordering.

Muc tieu: xay dung he thong dat do an va quan ly nha hang tich hop chatbot AI. He thong phai the hien duoc nghiep vu nha hang that: khach dat mon, nha hang tiep nhan, bep cap nhat tung mon, khach theo doi realtime, admin quan ly menu/ban/don hang.

## 2. Actors

### Customer / Guest

- Xem menu.
- Quet QR tai ban de dat mon dine-in.
- Dat mon online pickup hoac delivery mock.
- Hoi chatbot AI de duoc tu van mon.
- Theo doi trang thai don va tung mon realtime.
- Huy don khi don chua vao trang thai `Preparing`.

### Staff

- Xac nhan don moi.
- Phuc vu mon tai ban.
- Xu ly pickup hoac delivery mock.
- Xac nhan thanh toan COD/mock online.
- Hoan tat don.

### Kitchen

- Xem kitchen board.
- Cap nhat trang thai tung mon: `Pending`, `Preparing`, `Ready`, `Served`, `Cancelled`.
- Bao cho Staff khi mon da san sang.

### Admin

- Quan ly danh muc va mon an.
- Bat/tat trang thai con mon.
- Quan ly ban va link/QR cua ban.
- Xem don hang.
- Xem bao cao co ban: doanh thu ngay, mon ban chay.

### AI Chatbot

- Dung external LLM API.
- Dung RAG tren menu/FAQ de tra loi.
- Tu van mon theo khau vi, ngan sach, so nguoi, tinh trang con hang.
- De xuat them mon vao gio, nhung khach phai xac nhan.
- Khong tu dat don, khong tu thanh toan, khong bia mon/gia.

## 3. Core Business Flows

### QR Dine-in Flow

1. Admin tao hoac quan ly ban, vi du `T05`.
2. He thong sinh link QR cho ban: `/table/T05`.
3. Khach quet QR bang dien thoai.
4. Frontend mo menu voi context `tableCode = T05`.
5. Khach xem menu, hoi chatbot, them mon vao gio.
6. Khach xac nhan dat mon.
7. Backend tao don `OrderType = DineIn`, `tableCode = T05`.
8. Staff xac nhan don.
9. Kitchen nhan don tren kitchen board.
10. Kitchen cap nhat tung mon.
11. Customer tracking screen nhan realtime event va cap nhat trang thai.
12. Staff phuc vu, thu tien, hoan tat don.

### Online Pickup / Delivery Mock Flow

1. Khach vao `/menu`.
2. Khach chon mon va vao checkout.
3. Khach chon `Pickup` hoac `DeliveryMock`.
4. Neu delivery mock, khach nhap ten, so dien thoai, dia chi.
5. Staff xac nhan don.
6. Kitchen chuan bi mon.
7. Pickup: khach nhan tai quan.
8. DeliveryMock: Staff danh dau `Delivering`, sau do `Delivered`.
9. Staff/Admin xac nhan thanh toan va hoan tat don.

### Restaurant Management Flow

1. Admin dang nhap.
2. Admin quan ly category va menu item.
3. Admin bat/tat `isAvailable` cua mon.
4. Admin quan ly ban va QR link.
5. Staff theo doi don moi va xac nhan don.
6. Kitchen cap nhat tung mon.
7. Staff phuc vu/giao mon va xac nhan thanh toan.
8. Admin xem doanh thu ngay va mon ban chay.

### AI Chatbot Flow

1. Khach mo chatbot trong menu hoac trang chat.
2. Khach hoi ve mon an, gia, khau vi, mon chay, mon cay, goi y cho nhom.
3. Backend lay menu/FAQ lien quan bang RAG.
4. LLM tra loi dua tren du lieu da truy xuat.
5. Neu co goi y them vao gio, chatbot tra ve `SuggestedCartAction`.
6. Frontend hien thi nut Confirm/Dismiss.
7. Chi khi khach bam Confirm thi mon moi vao gio.

## 4. Important Status Names

Order status:

- `Draft`
- `Placed`
- `Confirmed`
- `Preparing`
- `Ready`
- `Served`
- `Delivering`
- `Delivered`
- `Completed`
- `Cancelled`

Order item status:

- `Pending`
- `Preparing`
- `Ready`
- `Served`
- `Cancelled`

Order type:

- `DineIn`
- `Pickup`
- `DeliveryMock`

Payment method:

- `COD`
- `MockOnline`

Payment status:

- `Unpaid`
- `Paid`
- `Failed`
- `Cancelled`

## 5. Scope For Version 1

In scope:

- QR table ordering.
- Customer menu/cart/checkout.
- Customer realtime order tracking.
- Admin menu/order/table management.
- Staff order handling.
- Kitchen board.
- Chatbot AI via LLM API + RAG.
- Docker/VPS deployment guide.

Out of scope for v1:

- Real payment gateway.
- Real delivery/shipper integration.
- Reservation/booking table before arrival.
- Inventory/ingredient stock deduction.
- Training a custom AI model.
- Multi-restaurant marketplace.

