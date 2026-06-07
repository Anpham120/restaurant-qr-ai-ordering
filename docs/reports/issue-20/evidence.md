# Issue 20 Evidence

## Scope

- Polish admin dashboard, menu, order, table QR, staff order board, and kitchen board UI.
- Keep operation-side routes demo-ready for final report screenshots.
- QR links use `/table/:tableCode` and are ready for real QR library integration.

## Verification

- `npm run build` in `frontend`: passed.
- Lint script is not configured in `frontend/package.json`.
- Manual walkthrough with Playwright:
  - `/admin`
  - `/admin/menu`
  - `/admin/orders`
  - `/admin/tables`
  - `/staff/orders`
  - `/kitchen`

## Screenshots

- Desktop admin dashboard: `docs/reports/issue-20/admin-dashboard.png`
- Desktop admin menu: `docs/reports/issue-20/admin-menu.png`
- Desktop admin orders: `docs/reports/issue-20/admin-orders.png`
- Desktop admin table QR: `docs/reports/issue-20/admin-tables-qr.png`
- Desktop staff orders: `docs/reports/issue-20/staff-orders.png`
- Desktop kitchen board: `docs/reports/issue-20/kitchen-board.png`
- Mobile table QR: `docs/reports/issue-20/mobile-admin-tables-qr.png`
- Mobile staff orders: `docs/reports/issue-20/mobile-staff-orders.png`
- Mobile kitchen board: `docs/reports/issue-20/mobile-kitchen-board.png`

## Notes

- Staff payment and admin status actions are UI placeholders until backend endpoints are ready.
- Kitchen realtime remains the existing mock event adapter and does not change backend contracts.
