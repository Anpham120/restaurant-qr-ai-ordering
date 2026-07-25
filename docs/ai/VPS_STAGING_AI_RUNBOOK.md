# VPS staging — AI + chat thật

Runbook cho deploy **staging** qua GitHub Actions (`.github/workflows/deploy-staging.yml`) và kiểm tra chat AI trên domain staging.

## Trước khi deploy

### 1. 9router trên VPS

Service `ai-service` dùng `network_mode: host`. `LLM_BASE_URL` phải trỏ tới gateway **trên cùng máy VPS** (mặc định workflow: `http://127.0.0.1:20128/v1` hoặc `vars.NINE_ROUTER_BASE_URL`).

- Cài và chạy 9router (systemd hoặc container publish port 20128).
- Không commit `LLM_API_KEY`; dùng GitHub secret `NINE_ROUTER_API_KEY`.

### 2. GitHub Environment `staging`

Secrets / vars tối thiểu (xem `deploy/scripts/deploy-vps.sh`):

| Biến | Nguồn |
| --- | --- |
| `STAGING_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY` | Secrets |
| `JWT_SIGNING_KEY`, `AI_INTERNAL_TOKEN`, `STAGING_POSTGRES_PASSWORD` | Secrets |
| `NINE_ROUTER_API_KEY` | Secret |
| `NINE_ROUTER_BASE_URL` | Variable (optional) |
| VietQR `PAYMENTS__VIETQR__*` | Secrets |

Workflow đã set: `CHAT_AI_PROVIDER=python-rag`, `RAG_RETRIEVAL_METHOD=hybrid`, `LLM_MODEL=oc/deepseek-v4-flash-free` (override bằng `vars.LLM_MODEL`), `VITE_USE_MOCK_CHAT=false`.

### 3. DNS

Domain staging (ví dụ `api-staging.cmcrestaurant.app`, `order-staging.cmcrestaurant.app`) trỏ về VPS.

## Deploy

1. Push `develop` hoặc **Actions → Deploy Staging → Run workflow**.
2. Workflow chạy CI quality gate rồi `bash deploy/scripts/deploy-vps.sh`.
3. Trên VPS, script chạy migrate, `docker compose up`, nginx, certbot, **`deploy/scripts/health-check.sh`**.

Health-check gồm:

- Frontend + API health/ready
- `GET http://127.0.0.1:8001/ready`
- `POST /v1/chat` với `Authorization: Bearer $AI_INTERNAL_TOKEN` và body `{"message":"Xin chào"}`

Báo cáo: `/opt/cmc-restaurant/staging/reports/last-deployment.md`

## Kiểm tra sau deploy

1. `curl -fsS https://api-staging.cmcrestaurant.app/api/health`
2. Đăng nhập demo (`SEED_DEMO_USERS=true` trên staging) → **order-staging** → mở chat.
3. Câu KB: *"nhà hàng có wifi không?"* (fast-path / KB).
4. Câu menu: *"gợi ý món"* — có thể **abstain** nếu Claim Verifier chưa LiveContext (đúng thiết kế; xem notebook §16).

Release quality vẫn **NOT READY** — xem [`AI_STAGING_READINESS.md`](AI_STAGING_READINESS.md).

## Local trước khi push

```powershell
cd restaurant-qr-ai-ordering\deploy
# .env từ deploy/env/staging.example.env
docker compose --env-file .env -f docker-compose.yml up -d --build
```

Hoặc chỉ AI: `cd ai` → `uvicorn` + `py scripts/smoke_9router.py`.

## Rollback

Workflow **rollback** hoặc `deploy/scripts/rollback-vps.sh` (xem README deploy).
