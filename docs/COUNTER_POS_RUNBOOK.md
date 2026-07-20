# Counter POS runbook

## Before service

1. Log in as **CounterStaff** (or Admin) on the ops app.
2. Open **Quầy thu ngân** (`/counter`).
3. **Mở ca** with opening cash float.

## During service

- Monitor **Hóa đơn chờ thu** queue (table invoices in `Pending`).
- Confirm **COD** or **VietQR** after verifying amount; COD posts to the open shift ledger.
- Cancel pending invoice only with a note; ordering reopens after cancel per domain rules.

## End of shift

1. Count physical cash.
2. **Chốt ca** with actual total; system records variance vs expected.
3. Review confirmed invoices in admin reports if needed.

## APIs

- `GET /api/counter/shifts/current`
- `POST /api/counter/shifts/open`
- `POST /api/counter/shifts/{id}/close`
- `POST /api/counter/shifts/{id}/adjustments`

Invoice settlement: `/api/table-invoices`, confirm/cancel on table session invoice routes.
