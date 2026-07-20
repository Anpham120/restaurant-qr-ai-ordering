# QR and table session state machine

## Stable table QR

- Table QR token is stable for the life of an open visit.
- Repeated scans on multiple devices attach to the **same open session** (`TABLE_QR_SINGLE_USE` disabled).
- Each scan returns a fresh capability token and deterministic `resumeState`.

## Resume states

| State | Customer destination |
|-------|---------------------|
| `New` | `/table-session/:id/menu` |
| `CartPending` | `/table-session/:id/cart` |
| `OrderInProgress` | `/table-session/:id/orders` |
| `ReadyForPayment` | `/table-session/:id/orders?focus=invoice` |
| `PaymentPending` | `/table-session/:id/orders?focus=invoice` |
| `Paid` | `/table-session/:id/orders?focus=invoice` |

Resolver: `TableSessionResumeStateResolver` (backend) and `getSessionResumeDestination` (frontend).

## Order round atomicity

Creating an order round clears the shared server cart in the **same serializable transaction** as order persistence. Idempotency keys prevent duplicate rounds across devices.

## Kitchen path

Orders must pass `Ready → Served` before session settlement. `Ready → Completed` skip is rejected at the domain layer.

## Settlement

Dine-in settlement uses **table invoice** only. Per-order payment endpoints remain for compatibility but are not the dine-in source of truth.
