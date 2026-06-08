# Manual API Smoke Test Evidence

Run date: 2026-06-08 12:18:43 +07:00

Command used:

```powershell
dotnet run --project backend/src/RestaurantQrAiOrdering.Api
```

Base URL: `http://localhost:5084` / `http://127.0.0.1:5084`

## Results

| Step | Endpoint | Status | Result | Response summary |
| --- | --- | ---: | --- | --- |
| Health | `GET /api/health` | 200 | PASS | `status=Healthy`, `service=RestaurantQrAiOrdering.Api`, environment `Development`. |
| Menu seed data | `GET /api/menu` | 200 | PASS | Returned 6 categories and 12 menu items. |
| Active table | `GET /api/tables/T05` | 200 | PASS | Returned `tableCode=T05`, `displayName=Ban 05`, `isActive=true`. |
| Invalid table | `GET /api/tables/T00` | 400 | PASS | Returned error code `TABLE_CODE_INVALID`. |
| Create order | `POST /api/orders` | 201 | PASS | Created `orderCode=ORD-1002`, `orderType=DineIn`, `tableCode=T05`, `status=Placed`, one item `m_001`. |
| Get order | `GET /api/orders/ORD-1002` | 200 | PASS | Returned persisted `orderCode=ORD-1002`, `tableCode=T05`, `status=Placed`, one order item. |

## Conclusion

Manual API smoke test passed. Health, menu seed data, table validation, order creation, and order persistence all matched the issue #18 API contract expectations in the same API process.
