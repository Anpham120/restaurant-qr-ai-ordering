# Operations workspaces

One Vite app (`frontend/apps/ops-web`, package `@cmc/ops-web`) serves all back-of-house roles after login.

## Role landing

| Role | Landing route | Workspace |
|------|---------------|-----------|
| Admin | `/` | Full admin + ops nav |
| CounterStaff | `/counter` | Counter POS + invoices |
| Staff (legacy) | `/counter` | Same as counter |
| Kitchen | `/kitchen/board` | Kitchen board |

## Workspaces

- **Operations overview** — dashboard, orders, sessions, invoices
- **Counter** — shift open/close, COD/VietQR confirmation, table invoice queue
- **Kitchen** — drag/drop pipeline board, menu 86 toggle
- **Catalog** — menu, categories (Admin)
- **Guests** — promotions, loyalty (Admin)
- **System** — tables/QR, users, access, reports (Admin)

## Deploy hosts

`admin.*`, `staff.*`, and `kitchen.*` domains all serve the same ops build. Role determines the post-login workspace.

Legacy paths `/staff/*` redirect to `/counter` or `/orders`.

## Out of scope

No mobile floor-staff UI. Service staff coordinate via radio; counter staff use the POS workspace only.
