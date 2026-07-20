# Professional GitHub README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the repository landing page into a product-first, evidence-backed GitHub presentation with real screenshots and clear technical onboarding.

**Architecture:** `README.md` remains the product landing page and concise developer entry point. `docs/README.md` becomes the categorized documentation hub, while existing specialist documents remain in place and are linked rather than duplicated.

**Tech Stack:** GitHub Flavored Markdown, Mermaid, GitHub Actions badges, repository-owned PNG assets.

## Global Constraints

- Chỉ công bố tính năng, URL, workflow và trạng thái đã có bằng chứng trong repository.
- Không sử dụng badge trang trí hoặc số liệu không thể kiểm chứng.
- Không đưa secret, tài khoản demo nhạy cảm hoặc chi tiết vận hành riêng tư vào README.
- Nội dung chính viết bằng tiếng Việt, giữ tên công nghệ và lệnh bằng tiếng Anh.
- README là trang giới thiệu và điều hướng; chi tiết dài nằm trong `docs/`.
- Thay đổi chỉ tác động tài liệu và asset trình bày, không thay đổi runtime code.
- Không di chuyển hoặc đổi tên hàng loạt tài liệu hiện có.

---

### Task 1: Rewrite the repository landing page

**Files:**
- Modify: `README.md`
- Reuse: `frontend/src/mocks/images/logo.png`
- Reuse: `docs/reports/issue-20/admin-dashboard.png`
- Reuse: `docs/reports/issue-20/admin-menu.png`
- Reuse: `docs/reports/issue-20/kitchen-board.png`
- Reuse: `docs/reports/issue-20/staff-orders.png`

**Interfaces:**
- Consumes: production URLs, workflow names, package scripts, architecture documents and repository-owned screenshots.
- Produces: a self-contained GitHub landing page linking to `docs/README.md` and specialist documents.

- [ ] **Step 1: Establish the product-first hero**

Replace the existing opening with:

- Centered project logo at a restrained width.
- Product name and the value proposition “Quét QR, gọi món, phối hợp vận hành và tư vấn món ăn bằng AI trên một nền tảng thống nhất.”
- Direct links to the customer demo, operations portal, architecture, API and local setup.
- CI, Security and Production Deployment badges using the existing workflow file names.

- [ ] **Step 2: Present product value and role-based flows**

Add:

- A short problem/solution paragraph.
- A two-column “Khả năng / Giá trị” table covering QR ordering, live operations, role-based workspaces, AI assistance and production delivery.
- A role table for Customer, Ordering, Staff, Kitchen and Admin.
- A Mermaid sequence/flow diagram from table scan to order completion, including the optional AI recommendation branch.

- [ ] **Step 3: Add a real product gallery**

Use an HTML table so GitHub displays four repository-owned screenshots in a two-column grid:

- Admin dashboard.
- Menu management.
- Kitchen board.
- Staff order board.

Every image must have descriptive Vietnamese alt text and a visible caption.

- [ ] **Step 4: Document architecture and engineering strengths**

Add:

- A Mermaid architecture diagram for five React/Vite applications, ASP.NET Core API, SignalR, PostgreSQL and FastAPI/RAG.
- A concise technology table.
- Separate evidence-based bullets for AI/RAG grounding, security/privacy, reliability and automated verification.

- [ ] **Step 5: Add executable onboarding**

Document:

```powershell
cd frontend
npm ci
npm run dev
```

```powershell
dotnet run --project backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj
```

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Also list the exact verification commands from `AGENTS.md` and link detailed environment/deployment instructions instead of copying secrets.

- [ ] **Step 6: Finish navigation and project status**

Add:

- Repository tree for `frontend/`, `backend/`, `ai/`, `deploy/`, `docs/`.
- A short documentation index linking to `docs/README.md`.
- Honest MVP/production-deployed status, focused roadmap, contribution link and MIT license.

- [ ] **Step 7: Verify Task 1**

Run:

```powershell
git diff --check -- README.md
```

Expected: no output.

Confirm every referenced image exists:

```powershell
Test-Path frontend/src/mocks/images/logo.png
Test-Path docs/reports/issue-20/admin-dashboard.png
Test-Path docs/reports/issue-20/admin-menu.png
Test-Path docs/reports/issue-20/kitchen-board.png
Test-Path docs/reports/issue-20/staff-orders.png
```

Expected: five `True` values.

### Task 2: Create the documentation hub

**Files:**
- Create: `docs/README.md`

**Interfaces:**
- Consumes: existing files under `docs/`.
- Produces: stable categorized navigation used by the root README.

- [ ] **Step 1: Create category-based navigation**

Create these sections with one-line descriptions for every linked document:

- Start Here.
- Product & System Design.
- API & Architecture.
- AI & RAG.
- Testing & Quality.
- DevOps & Operations.
- Team Process.
- Reports & Presentation.

Link only files that currently exist. Keep refactor/remediation plans under an explicit “Historical plans and implementation notes” subsection so readers do not confuse plans with the current architecture.

- [ ] **Step 2: Add documentation maintenance rules**

State that:

- README files describe current behavior.
- ADRs record decisions.
- Plans describe intended changes and may become historical.
- Evidence reports must include the issue or verification date.
- New documents must be linked from `docs/README.md`.

- [ ] **Step 3: Verify Task 2**

Run:

```powershell
git diff --check -- docs/README.md
```

Expected: no output.

### Task 3: Validate the complete GitHub presentation

**Files:**
- Verify: `README.md`
- Verify: `docs/README.md`

**Interfaces:**
- Consumes: completed Task 1 and Task 2.
- Produces: evidence that the documentation is renderable, internally consistent and limited to documentation changes.

- [ ] **Step 1: Validate relative Markdown targets**

Extract relative links from `README.md` and `docs/README.md`, resolve them from each file’s directory and confirm every local target exists. Ignore `http://`, `https://`, anchor-only and badge URLs.

Expected: zero missing local targets.

- [ ] **Step 2: Validate encoding and structure**

Confirm both files decode as UTF-8 and contain:

- Correct Vietnamese diacritics.
- One top-level heading each.
- Balanced fenced code blocks.
- Mermaid blocks for user flow and architecture.

- [ ] **Step 3: Review the scoped diff**

Run:

```powershell
git diff -- README.md docs/README.md
git status --short
```

Expected: root README modified and documentation hub added; unrelated user changes remain untouched.

- [ ] **Step 4: Commit documentation**

Stage only:

```powershell
git add README.md docs/README.md docs/superpowers/plans/2026-07-17-github-readme-redesign.md
```

Commit:

```text
docs: professionalize GitHub presentation
```
# Freshness correction

- [x] Remove README references to June issue #20 screenshots.
- [x] Capture current customer, menu, QR entry, and operations views from production.
- [x] Separate maintained documentation entry points from historical plans and reports.
- [x] Verify every promoted screenshot exists, is visually current, and contains no private data before push.
