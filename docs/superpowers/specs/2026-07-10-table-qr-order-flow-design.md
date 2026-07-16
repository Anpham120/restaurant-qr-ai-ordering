# Table QR Ordering Flow Design

## Goal

Make the production Vite/React portals and ASP.NET API support one reliable restaurant flow: a customer scans an active table QR code, receives an open table session, places an order, kitchen/staff see and process that order, and staff/customer complete payment without authorization or API-call errors.

## Contract and Boundaries

`docs/API_CONTRACT.md` remains the source of truth. Production state comes from HTTP API and SignalR, never frontend mocks or `localStorage`. Browser storage may retain only temporary cart/session data, JWT auth data, and the per-order customer access token.

The frontend uses one Vite-compatible API configuration based on `import.meta.env.VITE_API_BASE_URL`. Shared API client methods own URL construction and headers. Public customer requests use table/session data and `X-Order-Token` where required. Admin, staff, and kitchen requests use Bearer JWTs and enforce this role matrix:

- Admin: management, order operations, payment operations.
- Staff: order operations and payment operations.
- Kitchen: order list and item preparation status only.
- Customer: public menu/table/session/order creation and token-protected order/payment reads.

Backend authorization remains least-privilege. Fix contract mismatches rather than weakening protected endpoints.

## End-to-End Data Flow

1. `/table/:tableCode?qr=:token` resolves or opens an active dine-in table session.
2. Menu loads from the API; customer cart stays scoped to that table session.
3. Order creation sends `tableCode`, `qrToken`, `tableSessionId`, items, and payment method.
4. Frontend stores returned `orderCode` plus `customerAccessToken`, then opens tracking.
5. Kitchen/staff load `GET /api/orders`; SignalR refreshes new/status events, with HTTP refresh fallback.
6. Kitchen updates item status; staff updates order status.
7. Customer generates VietQR when selected; staff/admin confirms payment. Tracking reloads authoritative payment/order state.

## Error Handling

- Invalid or expired QR/session: block checkout and instruct customer to rescan.
- `401`: clear invalid operational auth and return to the correct portal login.
- `403`: show unauthorized state without redirecting into another role portal.
- Missing customer order token: do not expose the order; show a recoverable tracking error.
- Network/SignalR failure: retain current UI state, show retry, and retry via HTTP without duplicate orders or payments.

## Verification Seams

- Vitest/Testing Library: QR route to session to checkout to stored order token; portal role routing and API errors.
- Shared API-client tests: Vite base URL, Bearer token, `X-Order-Token`, request paths, and payloads.
- xUnit integration tests: role matrix, session/order validation, kitchen visibility, and payment authorization.
- Multi-device xUnit/Playwright smoke: separate customer, kitchen, and staff clients complete the full flow against shared backend state.

## Non-Goals

No framework migration, mock-backed production pages, new order types, or broad authorization bypasses.
