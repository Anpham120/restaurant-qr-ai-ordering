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
- api: `POST /api/table-sessions` → active session + capability + `resumeState ∈ {New,CartPending,OrderInProgress,ReadyForPayment,PaymentPending,Paid}`.
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
- V29: ∀ configured AI provider failure → fallback response carries `AI_PROVIDER_UNAVAILABLE` and server logs provider, model, and exception type without credentials or user prompt.
- V30: ∀ production LLM call → direct Google Gemini API OpenAI-compatible endpoint; credential comes from `GEMINI_API_KEY`; no local gateway dependency.
- V31: ∀ default production Gemini model → successful live `/chat/completions` smoke with the configured repository key before release.
- V32: ∀ Gemini structured completion → request JSON response mode; retry 429/5xx at most `AI_MAX_RETRY` times before bounded fallback.
- V33: ∀ Gemini restaurant chat completion → strict JSON schema requires `content`, `suggested_cart_actions`, and `guardrail_flags` before parser execution.
- V34: ∀ menu-category/tag request → every AI-listed or AI-actionable item belongs to the matched live category/tag candidate set; response contains no duplicate semantic line and uses bounded prompt context.
- V35: ∀ explicit live category/tag catalog request → backend returns a deterministic catalog built only from matched live candidates; LLM free text cannot introduce menu items.
- V36: ∀ request to recommend additional dishes in one chat session → response excludes every live menu item previously suggested by that session and honours a requested count from 1 to 8 (default 3).
- V37: ∀ persisted assistant recommendation → every returned/history message retains its actionable menu cards; an unambiguous `xem chi tiết` follow-up resolves to the latest suggested live items instead of unrelated retrieval.
- V38: ∀ research benchmark case → expected document IDs ∩ forbidden document IDs = ∅; family source and materialized JSONL remain identical; dev/test artifacts are physically separate and frozen test canonical text bytes are hash-gated before label parsing; query-family split leakage = 0; official menu corpus = exactly 91 canonical items including drinks, with production-seed parity for name/price/description.
- V39: ∀ Python-RAG menu recommendation → live available menu is ranked by configured BM25/dense/hybrid stack; category/tag constraints apply before ranking; previously suggested or explicitly rejected IDs cannot become cards; explicit count 1..8 is filled without duplicate cards when enough candidates exist.
- V40: ∀ production hybrid startup → exact multilingual-E5 revision is packaged in the AI image and reused across KB/live-menu indexes; unavailable dense runtime degrades to observable BM25 fallback instead of failing the AI service.
- V41: ∀ production AI image build → PyTorch is installed from the official CPU-only index before RAG dependencies and CUDA/NVIDIA wheels are absent; deployment health checks retry transient TLS failures during Nginx certificate reload.
- V42: ∀ `/api/users` mutation → `AdminOnly`; create/update/delete persists; duplicate email + missing user deterministic; current admin cannot delete self or remove own Admin role.
- V43: landing + ordering → one warm Vietnamese brand token set; display/body/utility fonts + VND formatting identical; money uses tabular utility numerals.
- V44: landing + ordering locale ∈ {`vi`,`en`} persists across hosts; switch updates static UI, navigation, accessibility copy, dates, money, category, item name + description.
- V45: landing + ordering @ viewport ≥320px → no horizontal overflow; primary controls touch target ≥44px; header/nav/modal respect safe-area; content hierarchy remains readable without zoom.
- V46: ∀ declared `@cmc/*` workspace dependency → matching workspace package + lock entry exist; fresh install then frontend typecheck resolves every package.
- V47: ∀ order-detail invoice action → canonical `/table-session/:sessionId/orders`; never session root/menu.
- V48: kitchen active pipeline = `Placed|Confirmed|Preparing|Ready`; `order.created` reloads board; `Placed` visible in new-order column.
- V49: ∀ relational table-invoice payment request → serializable transaction executes inside EF execution strategy; COD/VietQR capability + idempotency preserved; missing session → structured 404, never 500.
- V50: ordering header has no dashed divider; locale control = one ≥44px current-locale `VI|EN` button; click flips locale.
- V51: ∀ valid table QR scan while session `Open` & unexpired → same `sessionId`; concurrent/multi-device scans create ≤1 active session; response `resumeState` deterministic, token values never logged.
- V52: scan destination solely maps `resumeState`: `New→menu`, `CartPending→cart`, `OrderInProgress→orders`, payment states→`orders?focus=invoice`; ⊥ hardcoded post-scan menu redirect.
- V53: session orders hub reflects aggregate orders/items/invoice; order/payment realtime reloads hub; disconnected realtime → 5s polling; payment pending/paid forbids new ordering.
- V54: `Ready→Served` atomic order + all non-cancelled items; Kitchen|Staff allowed, Kitchen forbidden any other order transition; Kitchen board contains read-only Served column and realtime movement.
- V55: QR/Kitchen state logic has one live resolver/pipeline each; superseded one-shot routing, duplicate status maps, unused feature files/imports absent; full typecheck + tests pass.
- V56: ∀ application log entry → request-controlled values omitted or CR/LF-sanitized before emission; CodeQL `cs/log-forging` findings = 0.
- V57: ∀ verification command → execute from its authoritative component root or pass an explicit project/config path; parent-workspace invocation forbidden.
- V58: ∀ `Placed|Confirmed` order, first active item `Pending→Preparing` → aggregate order `Preparing` in same mutation; refreshed Kitchen board moves card `confirmed→preparing`.
- V59: Kitchen board @ desktop → exactly 4 equal columns `confirmed|preparing|ready|served` in one row; tablet → 2 columns; mobile → 1 column.

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
T20|x|ground AI menu retrieval by live category/tag; add quality/latency regressions and research protocol|V34,I.ai,I.api
T21|x|return deterministic live catalog for explicit category/tag requests; regression against LLM text leakage|V35,I.ai,I.api
T22|x|exclude previously suggested session dishes from deterministic additional recommendations; honor 1-8 requested count|V36,I.ai,I.api
T23|x|persist recommendation cards per chat message and resolve latest-card detail follow-up|V37,I.ai,I.api,I.ui
T24|x|integrate benchmark-selected hybrid retrieval, structured session exclusions and reusable Gemini client into production AI|V39,V40,I.ai,I.api
T25|x|add admin user create/update/delete API + UI + regressions|V42,I.api,I.ui
T26|x|unify landing + ordering brand tokens, typography + VND formatting|V43,I.ui
T27|x|add persistent VI/EN switch + full landing/ordering/menu localization|V44,V46,I.ui
T28|x|optimize landing + ordering responsive mobile layout + regressions|V45,I.ui
T29|x|run full repo verification; commit + push AI and requested features|C,V42,V43,V44,V45
T30|x|fix order-detail invoice route|V47
T31|x|surface placed orders in kitchen pipeline|V48
T32|x|run table-invoice payment transaction inside retry strategy|V49
T33|x|simplify ordering header + locale toggle|V45,V50
T34|x|add table-session resume-state resolver + additive open response|V51,I.api
T35|x|route repeat scans + upgrade session orders to realtime state hub|V52,V53,I.ui,I.api
T36|x|add atomic Served transition + fourth Kitchen column|V54,I.api,I.ui
T37|x|remove superseded QR/Kitchen logic + full verification|V55,C
T38|x|fix Kitchen card movement + four-column responsive board|V54,V55,V58,V59,I.api,I.ui

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
B40|2026-07-13|production AI model remained in 9Router catalog but upstream chat rejected it, while the service swallowed the exception and exposed only a generic fallback|V29
B41|2026-07-13|CI `AI_MODEL` env entry retained invalid over-indentation, so the workflow failed before creating jobs|V21
B42|2026-07-13|Gemini 2.5 Flash remained in the model catalog but rejected new users with 404 after deployment|V31
B43|2026-07-13|Gemini completion relied on prompt-only JSON and failed immediately on transient 503 or free-form output|V32
B44|2026-07-13|Gemini `json_object` mode returned valid JSON with provider-invented field names that the restaurant parser rejected|V33
B45|2026-07-13|AI prompt omitted live category name and passed arbitrary first menu items, so a seafood request could surface other categories; long unbounded context also increased latency and repetition|V34
B46|2026-07-13|LLM could still violate candidate-only text instruction even though its action IDs were validated, returning `Khai vị` dishes for the live `Hải sản` category|V35
B47|2026-07-13|cross-turn recommendation only deduplicated lines inside one LLM response; older AI suggestions were not a deterministic exclusion set|V36
B48|2026-07-13|deterministic menu replies returned no suggested actions and history omitted persisted actions, so cards vanished and `xem chi tiết` lost its referent|V37
B49|2026-07-13|broad healthy and sweet tag selectors overlapped, so rejection benchmark labels marked the same menu documents as both expected and forbidden|V38
B50|2026-07-13|research corpus used a stale 84-item JSON snapshot and omitted the 7-item Bia & Rượu category present in the production seed|V38
B51|2026-07-13|dev benchmark loaded a combined 360-case artifact before filtering, so frozen test labels were parsed during tuning|V38
B52|2026-07-13|new drink records enriched canonical descriptions with unsupported serving sizes, alcohol percentages and ingredients absent from the production seed|V38
B53|2026-07-13|Python RAG rebuilt a lexical menu index and Gemini client per request while backend history omitted action IDs and long-session memory omitted suggestions/rejections, allowing repeated cards and inconsistent requested counts|V39,V40
B54|2026-07-13|the customer phrase `đồ uống có cồn` did not exactly match category `Bia & Rượu`; both backend deterministic grounding and Python hybrid retrieval admitted unrelated drinks/foods|V39
B55|2026-07-13|frozen text artifacts were hashed from checkout bytes, so Windows CRLF and Linux LF produced different hashes for identical benchmark content and failed CI|V38
B56|2026-07-13|the production AI image resolved default PyTorch CUDA/NVIDIA wheels on a CPU VPS, creating multi-gigabyte layers until Docker export broke the SSH deployment connection|V41
B57|2026-07-13|rollback recreated a healthy stack but its immediate API health check treated a transient TLS certificate mismatch as terminal, so the rollback workflow reported failure despite public 200 responses|V41
B58|2026-07-15|new `@cmc/i18n` workspace package was declared before lock/install refresh, so typecheck could not resolve it|V46
B59|2026-07-15|menu localization generic required category metadata absent from the shared customer `MenuItem` contract|V44
B60|2026-07-15|localized menu filters read a nonexistent `MenuItem.categoryId` instead of joining canonical category name to response category ID|V44
B61|2026-07-15|verification batch ran from the parent workspace, so relative `frontend` prefix missed the repository package|repo-scoped verification command
B62|2026-07-15|menu parity regression expected materialized `m_###` strings while the canonical C# seed declares `Item(index, ...)`|V44
B63|2026-07-15|server-render payment regression mounted a localized component without its required `I18nProvider` runtime contract|V44
B64|2026-07-15|payment regression still expected legacy `220.000đ` after shared money formatting standardized the UI on Intl VND output|V43
B65|2026-07-15|AI verification launched pytest from the repository root even though tests import the `ai` directory as their package root|AI-scoped verification command
B66|2026-07-15|AI retriever ADR used Markdown hard-break spaces that failed the authoritative staged whitespace gate|`git diff --cached --check`
B67|2026-07-15|order-detail invoice link used route-relative parent, resolving to session index then menu redirect|V47
B68|2026-07-15|new orders start `Placed`, but kitchen page and board both admitted only `Confirmed` into new-order column|V48
B69|2026-07-15|payment endpoint opened a serializable transaction outside Npgsql retry execution strategy, causing production 500 before session lookup|V49
B70|2026-07-15|invoice route was referenced inside nested tracking panel without passing session scope, so source assertion passed but ordering typecheck failed|V47,frontend typecheck
B71|2026-07-15|scan page always redirected successful reusable session to `/menu`; open response exposed no semantic resume state|V51,V52
B72|2026-07-15|V53 integration fixture assumed invoice GET persisted a `TableInvoice`; GET only projects a response, so payment-state setup had no row|V53
B73|2026-07-15|concurrent QR opens raced past the pre-insert lookup; non-relational tests exposed multiple returned session ids because uniqueness catch was provider-dependent|V51
B74|2026-07-15|release verification invoked Compose without the authoritative `deploy/docker-compose.yml` path and its required CI environment|V21
B75|2026-07-15|admin user endpoint logged route-controlled `userId`, so CodeQL found two CWE-117 log-forging paths and unresolved review threads blocked merge|V56
B76|2026-07-15|backend verification ran from the parent workspace without an explicit solution path, so MSBuild found no project and produced a false test failure|V57
B77|2026-07-15|`Placed` omitted from item-status aggregation + board `auto-fit minmax(340px,1fr)` wrapped Served lane below|V58,V59
