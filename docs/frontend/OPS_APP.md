# Ứng dụng vận hành — workspace và quầy

> **⚠️ Kiểm lần cuối: 2026-07-20. Mã sửa gần nhất: 2026-08-02.**
>
> Tài liệu này KHÔNG trỏ vào tệp hay endpoint nào đã biến mất — đã kiểm bằng máy. Nhưng phép
> kiểm đó chỉ bắt được *đường dẫn chết*, **không** bắt được *hành vi đã đổi*: một endpoint còn
> nguyên tên mà đổi dạng phản hồi thì vẫn 'sạch'. Đối chiếu với mã trước khi tin phần chi tiết.

> **Một tài liệu cho toàn bộ mảng này.** Gộp từ 2 tệp: `OPERATIONS_WORKSPACES.md`, `COUNTER_POS_RUNBOOK.md`.
>
> Hai tệp cùng nói về ứng dụng vận hành mà nhân viên dùng.


---

## Workspace theo vai trò

*(gộp từ `docs/OPERATIONS_WORKSPACES.md`)*

One Vite app (`frontend/apps/ops-web`, package `@cmc/ops-web`) serves all back-of-house roles after login.

### Role landing

| Role | Landing route | Workspace |
|------|---------------|-----------|
| Admin | `/` | Full admin + ops nav |
| CounterStaff | `/counter` | Counter POS + invoices |
| Staff (legacy) | `/counter` | Same as counter |
| Kitchen | `/kitchen/board` | Kitchen board |

### Workspaces

- **Operations overview** — dashboard, orders, sessions, invoices
- **Counter** — shift open/close, COD/VietQR confirmation, table invoice queue
- **Kitchen** — drag/drop pipeline board, menu 86 toggle
- **Catalog** — menu, categories (Admin)
- **Guests** — promotions, loyalty (Admin)
- **System** — tables/QR, users, access, reports (Admin)

### Deploy hosts

`admin.*`, `staff.*`, and `kitchen.*` domains all serve the same ops build. Role determines the post-login workspace.

Legacy paths `/staff/*` redirect to `/counter` or `/orders`.

### Out of scope

No mobile floor-staff UI. Service staff coordinate via radio; counter staff use the POS workspace only.

---

## Runbook quầy POS

*(gộp từ `docs/COUNTER_POS_RUNBOOK.md`)*

### Before service

1. Log in as **CounterStaff** (or Admin) on the ops app.
2. Open **Quầy thu ngân** (`/counter`).
3. **Mở ca** with opening cash float.

### During service

- Monitor **Hóa đơn chờ thu** queue (table invoices in `Pending`).
- Confirm **COD** or **VietQR** after verifying amount; COD posts to the open shift ledger.
- Cancel pending invoice only with a note; ordering reopens after cancel per domain rules.

### End of shift

1. Count physical cash.
2. **Chốt ca** with actual total; system records variance vs expected.
3. Review confirmed invoices in admin reports if needed.

### APIs

- `GET /api/counter/shifts/current`
- `POST /api/counter/shifts/open`
- `POST /api/counter/shifts/{id}/close`
- `POST /api/counter/shifts/{id}/adjustments`

Invoice settlement: `/api/table-invoices`, confirm/cancel on table session invoice routes.
