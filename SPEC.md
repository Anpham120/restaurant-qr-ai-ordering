# CMC Restaurant QR Ordering

## §G

Refactor repo: cấu trúc rõ, code live, logic state đúng, build/test/deploy proof.

## §C

- Public portal + API contract giữ nếu chưa deprecate.
- Production secret ∉ git.
- Delete source ! caller proof + build/test proof.
- DB enum/string data ! migration + data audit trước breaking change.
- Refactor slice nhỏ, commit riêng, verification cùng commit.

## §I

- ui: customer, admin, staff, kitchen Vite portals.
- api: ASP.NET Core `/api/*`.
- db: EF Core + PostgreSQL; Development InMemory.
- ai: FastAPI RAG `/chat` adapter.
- deploy: Docker Compose + GitHub Actions.

## §V

- V1: ∀ payment.Status=Refunded → confirm/fail reject; status, transaction, loyalty unchanged.
- V2: ∀ runtime frontend module ∈ app import graph.
- V3: ∀ Completed order → payment ∈ {Confirmed,Paid}.
- V4: ∀ DineIn order → valid open unexpired TableSession; reopen expires stale first; ≤1 live session/table.
- V5: ∀ linked chat → parent TableSession active (Open, !closed, !expired); otherwise capability reject.
- V6: ∀ chat menu lookup → current database availability + price.
- V7: ∀ terminal order (Completed/Cancelled) → item status immutable.
- V8: ∀ persisted float[] embedding → structural equality + snapshot comparison.
- V9: ∀ Order/Payment concurrent write → PostgreSQL xmin rowversion participates without schema DDL.
- V10: ∀ deploy → PostgreSQL migration succeeds before API start; normal API boot does not migrate schema.
- V11: ∀ active TableSession → repeated chat-session create reuses one persisted chat session.
- V12: ∀ frontend Dockerfile package-manifest COPY → source exists in build context.
- V13: ∀ integration factory + parameterized DineIn lifecycle case → isolated in-memory DB + table/session fixture; no cross-test active-session contention.
- V14: ∀ TableSession → many Order Rounds aggregate into one Table Invoice; promotion, loyalty identity, and payment never belong to an Order Round.
- V15: ∀ integration fixture → production-valid domain values; setup HTTP failure reports response body before lifecycle assertions.
- V16: ∀ TableSession → Order Round creation and settlement start serialize on the shared session; at most one side commits from the same version.
- V17: ∀ TableInvoice.Status=Pending → no order/item cancellation may change payable lines; kitchen progress remains allowed.
- V18: ∀ cancelled settlement → promotion, loyalty phone, method, and discount cleared before ordering resumes.
- V19: ∀ paid TableSession → reports count one paid Table Invoice, while item sales aggregate all non-cancelled Order Rounds.
- V20: ∀ concurrent loyalty accrual → member rowversion or unique conflict prevents lost increments; caller receives conflict, never silent overwrite.
- V21: ∀ PR→main → required `frontend-build`, `backend-test`, and `docker-compose-config` checks instantiate and pass before merge.
- V22: frontend host routing = 6 production + 6 staging canonical domains; retired `customer` alias absent.
- V23: ∀ deploy workflow → every `deploy-vps.sh` required variable supplied before remote mutation.
- V24: ∀ PostgreSQL Order Round creation with retry enabled → serializable transaction executes inside `Database.CreateExecutionStrategy()` and commits exactly once.
- V25: ∀ persisted chat session lookup → EF query translates on PostgreSQL and a refreshed client restores every committed message.
- V26: ∀ chat message shown as committed history → send API succeeded or a subsequent server history read returned it; pending/failed text is never presented as persisted.
- V27: ∀ unhandled API exception → structured `INTERNAL_ERROR` HTTP 500 retains allowed-origin CORS headers; browser never degrades it to opaque `Failed to fetch`.
- V28: ∀ session capability → signature depends only on immutable persisted identity; PostgreSQL timestamp precision changes cannot invalidate a freshly issued token.

## §T

id|status|task|cites
T1|x|remove unreachable frontend modules + empty utils workspace|V2
T2|x|align customer card price + add controls|I.ui
T3|x|payment refund terminal guard + HTTP regression test|V1,I.api
T4|x|table-session open/close/expiry one lifecycle|V4,I.api
T9|x|manual table close deletes linked chat session|V5,I.api
T5|x|chat live menu read; delete stale in-memory menu store|V6,I.api
T10|x|remove unregistered in-memory chat adapter; name live contract|I.api
T11|x|reject item mutation on terminal parent order|V7
T12|x|add structural EF comparer for knowledge embeddings|V8
T13|x|run backend regression suite in CI and document it|C
T14|x|remove unregistered in-memory user adapter; name live contract|I.api
T15|x|add dependency-free AI guardrail regressions and CI step|I.ai
T16|x|test menu image fallback resolver and run it in CI|I.ui
T17|x|replace deprecated xmin helper and isolate deploy migration|V9,V10
T18|x|retain the restored chat-session contract through repository cleanup|V11
T6|x|add backend/AI/frontend regression test surfaces|V1,V2,V3,V4
T7|x|remove tracked duplicate agent skill trees + stale docs|C
T8|x|full repository audit; build/deploy proof|C
T19|x|introduce aggregate Table Invoice and session settlement flow|V14,I.api,I.ui

## §B

id|date|cause|fix
B1|2026-07-11|`PaymentEndpoints` omit `Refunded` confirm/fail guard|V1
B2|2026-07-11|manual table close omit `DeleteSessionsByTableSession`|V5
B3|2026-07-11|chat read startup `RestaurantDataStore` snapshot|V6
B4|2026-07-11|chat capability checks HMAC but not parent session expiry|V5
B5|2026-07-11|reopen ignores expired Open session and leaves linked chat|V4,V5
B6|2026-07-11|order item transition omits terminal parent order guard|V7
B7|2026-07-11|table open query/insert has no DB uniqueness guard|V4
B8|2026-07-11|EF embedding converter has reference-only collection comparison|V8
B9|2026-07-11|retired UserStore co-locates public result contracts|C
B10|2026-07-11|API startup owned production schema migration|V10
B11|2026-07-11|rebase conflict briefly mixed the table expiry query into its foreach body|compile preflight
B12|2026-07-11|retired chat contract omitted the live CreateOrGetSession API|V11
B13|2026-07-11|DbChatStore test omitted its required active parent TableSession|V5
B14|2026-07-11|frontend Dockerfile copied retired packages/utils manifest|V12
B15|2026-07-12|integration factories reused named EF in-memory DB and lifecycle rows reused table/session during parallel CI|V13
B16|2026-07-12|new Table Invoice endpoint omitted the namespace containing shared API results|compile preflight
B17|2026-07-12|Table Invoice integration test assumed a seeded table index instead of owning its fixture|V13
B18|2026-07-12|cart checkout and payment model attached promotion, loyalty, and settlement to one Order instead of the Table Session|V14
B19|2026-07-12|Table Invoice payment test generated a table code rejected by the production validator|V15
B20|2026-07-12|Table Invoice staff endpoints omitted `Api.Users` namespace for `UserRole`|compile preflight
B21|2026-07-13|integration factory omitted required VietQR bank options for the payment lifecycle|V15
B22|2026-07-13|EF InMemory bound array `Contains` to .NET 10 `ReadOnlySpan` overload in invoice list query|V15
B23|2026-07-13|session-touch patch landed in status update instead of order creation and omitted realtime namespace|compile preflight
B24|2026-07-13|settlement subtotal and new Order Round could commit from the same TableSession version|V16
B25|2026-07-13|pending settlement allowed order/item cancellation to change payable lines|V17
B26|2026-07-13|cancelled settlement retained stale promotion, loyalty phone, method, and discount|V18
B27|2026-07-13|report paid count used Order Rounds while daily revenue used Table Invoices|V19
B28|2026-07-13|loyalty accrual used unguarded read-modify-write|V20
B29|2026-07-13|settlement migration rollback made `order_id` non-null before removing invoice-targeted payments|migration down cleanup
B30|2026-07-13|settlement completion bypassed order history and realtime notification|OrderStore staged completion
B31|2026-07-13|completion audit test referenced `Status` instead of `OrderStatusHistory.ToStatus`|compile preflight
B32|2026-07-13|CI deployment env entries were over-indented, invalidating workflow before required jobs instantiated|V21
B33|2026-07-13|app-separation regression test still required the deliberately retired `customer` redirect|V22
B34|2026-07-13|staging workflow omitted required VietQR deployment variables and exited before SSH|V23
B35|2026-07-13|OrderStore opened a user transaction outside Npgsql retry execution strategy|V24
B36|2026-07-13|DbChatStore used an untranslatable `StringComparison` overload in an EF query|V25
B37|2026-07-13|chat UI appended optimistic text to committed history before backend persistence|V26
B38|2026-07-13|exception middleware sat outside CORS and handled only malformed request bodies|V27
B39|2026-07-13|table/chat capability signatures included timestamps that PostgreSQL can round between issue and verify|V28
