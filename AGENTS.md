# Repository Guidelines

## Project Structure & Module Organization

- `frontend/` is a React 19/TypeScript workspace. Deployable Vite apps live in `apps/{customer,admin,kitchen,staff}-web`; reusable code lives in `packages/`; shared pages, components, services, types, and styles are under `src/`.
- `backend/` contains the ASP.NET Core solution. API code is in `src/RestaurantQrAiOrdering.Api`; shared entities and enums are at the backend root.
- `ai/` contains the FastAPI/RAG service, knowledge base, evaluation data, and notebooks.
- `deploy/` and `.github/workflows/` hold deployment and CI configuration; architecture and operational guidance belongs in `docs/`.

## Build, Test, and Development Commands

Run commands from the indicated directory:

```bash
cd frontend && npm ci && npm run dev       # customer app locally
npm run dev:admin                          # alternate portal
npm run build                              # type-check and build all Vite apps
dotnet build backend/RestaurantQrAiOrdering.sln --configuration Release
python -m pip install -r ai/requirements.txt
python -m compileall ai/app
```

Run the API with `dotnet run --project backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj`. Run the AI service from `ai/` with `uvicorn app.main:app --reload --port 8001`.

## Coding Style & Naming Conventions

Follow existing formatting: two-space indentation in TypeScript/TSX and four spaces in C#. Use `PascalCase` for React components, C# types, and test classes; `camelCase` for TypeScript functions and variables; and descriptive service filenames such as `orderService.ts`. Keep nullable reference types enabled and avoid suppressing TypeScript errors. No repository-wide formatter is configured, so preserve the style of surrounding code and keep diffs focused.

## Verification Guidelines

The repository does not retain test suites. Verify changes with frontend type-check/build, backend Release build, Python bytecode compilation, Docker Compose validation, and focused manual smoke checks for auth, orders, payments, table sessions, and AI guardrails.

## Commit & Pull Request Guidelines

Use Conventional Commits (`feat:`, `fix:`, `style(scope):`, `docs:`, `test:`, `chore:`), matching recent history. Branch from `develop`; prefer `issue-<number>/<user>-<short-task>`. Target PRs to `develop`, include `Closes #<number>`, summarize scope, list verification commands, and attach screenshots for UI changes. CI must pass before merge.

## Security & Configuration

Copy `.env.example` files and keep real secrets out of Git. Document user-visible behavior changes and never change shared API contracts, routes, enums, or database fields without coordinating dependent frontend, backend, and AI code.
