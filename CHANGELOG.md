# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Rebuilt the chatbot as an evidence-driven live-menu RAG service with deterministic fast paths, persisted table-session memory and customer-confirmed cart suggestions.
- Replaced the legacy knowledge-base/evaluation artifacts with a reproducible 91-item research dataset, five-method retrieval comparison, raw per-query evidence, statistical tests and an executed notebook.
- Selected TF-IDF for production from the locked test protocol and changed the optional prose model to Gemini Flash through 9Router with retrieval-only fallback.

### Security
- Menu IDs, prices and availability are now canonicalized by the backend; AI output cannot directly mutate carts, submit orders or claim a completed transaction.

## [0.1.0] - 2026-06-19

First public milestone (MVP / demo) of the CMC Restaurant QR AI Ordering platform:
a QR-based dine-in ordering system with an AI assistant, real-time kitchen
updates, and a backend-first modular-monolith architecture. Delivered across five
weekly milestones (Tuần 1–5) covering 42 closed issues.

### Added
- **QR dine-in ordering flow** — customer scans a table QR, browses the menu,
  builds a cart, and checks out without an app install (#27, #32, #49).
- **Role-based web portals** — separate customer, admin, kitchen, and staff
  front-ends built on React 19 + Vite + TypeScript (#25, #31, #50, #107).
- **Menu, category, table & availability API** with QR/session lookup (#29, #88, #89).
- **Authentication & authorization** — JWT with PBKDF2/HMAC password hashing and
  role-based access for Customer, Staff, Kitchen, and Admin (#33, #85).
- **Order lifecycle** persisted end to end in the database (#90).
- **Payments** — Cash-on-Delivery and VietQR QR-code payment flow (#91).
- **AI ordering assistant** — LLM chat API with menu/FAQ retrieval (RAG) and
  safety guardrails, plus a streaming chatbot UI with add-to-cart suggestions
  (#40, #42, #43, #102).
- **Python RAG service** — standalone FastAPI lexical-retrieval service with a
  knowledge base and evaluation harness (#55), backed by an AI/ML recommendation
  notebook for data exploration (#53).
- **Real-time updates** — SignalR-driven order/item status, live kitchen board,
  and customer order tracking (#41, #44).
- **Backend-first modular monolith** architecture on ASP.NET Core (net10) with
  PostgreSQL + EF Core / Npgsql persistence (#83, #84).
- **CI/CD & deployment** — GitHub Actions pipeline (CI, staging deploy, promote,
  production deploy, rollback), Docker Compose stack, and health checks. Deployed
  live behind Nginx + HTTPS with two front-end domains: `cmcrestaurant.app`
  (customer) and `admin.cmcrestaurant.app` (operations: admin/kitchen/staff),
  plus the `api.cmcrestaurant.app` backend (#45).

### Changed
- Replaced the legacy single-app UI with dedicated role-based portals (#107, #108).
- Migrated persistence from in-memory stores to PostgreSQL across auth, menu,
  tables, and orders (#85, #88, #89, #90).
- Removed the legacy single-app build toolchain in favor of the npm-workspaces
  monorepo (#121).
- Frontend CI now runs both build and unit tests on every pull request (#122).

### Security
- Removed a credential backdoor and stopped shipping secrets in committed config.
  Demo accounts are now opt-in only via the `SEED_DEMO_USERS` flag, and the
  bootstrap admin is configured through `BOOTSTRAP_ADMIN_EMAIL` /
  `BOOTSTRAP_ADMIN_PASSWORD` (#120).

### Fixed
- CORS rejection for the chat API on the customer domain (#47).
- Frontend workspace install inside Docker (#111).
- Operations login layout and demo-password handling (#113).
- Menu placeholder images (#115) and admin login production UI (#117).
- Unstable production health check during promotion (#105).

### Known Issues
- This is an MVP milestone: feature scope is core-only and sample data is used for
  demonstration. The system is deployed live, but secrets must still be kept
  current (see below).
- AI retrieval is lexical (token-overlap scoring), not vector embeddings; semantic
  search is on the roadmap.
- Before any real deployment, operators must set `BOOTSTRAP_ADMIN_EMAIL` /
  `BOOTSTRAP_ADMIN_PASSWORD` and rotate `JWT_SIGNING_KEY` and the PostgreSQL
  password. Demo seed users are intended for local/dev only (`SEED_DEMO_USERS=true`).

[0.1.0]: https://github.com/Anpham120/restaurant-qr-ai-ordering/releases/tag/v0.1.0
