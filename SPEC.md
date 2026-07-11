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
- V4: ∀ DineIn order → valid open unexpired TableSession.
- V5: ∀ TableSession.Status=Closed → linked chat capability reject.

## §T

id|status|task|cites
T1|x|remove unreachable frontend modules + empty utils workspace|V2
T2|x|align customer card price + add controls|I.ui
T3|x|payment refund terminal guard + HTTP regression test|V1,I.api
T4|.|table-session open/close/expiry one lifecycle|V4,I.api
T9|x|manual table close deletes linked chat session|V5,I.api
T5|.|chat live menu read; delete stale in-memory menu store|I.api
T6|.|add backend/AI/frontend regression test surfaces|V1,V2,V3,V4
T7|.|classify/remove tracked duplicate agent skill trees + stale docs|C
T8|.|full repository audit; build/deploy proof|C

## §B

id|date|cause|fix
B1|2026-07-11|`PaymentEndpoints` omit `Refunded` confirm/fail guard|V1
B2|2026-07-11|manual table close omit `DeleteSessionsByTableSession`|V5
