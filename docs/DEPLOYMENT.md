# Tài Liệu Triển Khai

Tài liệu này mô tả hướng triển khai production-like cho **CMC Restaurant - Restaurant QR AI Ordering** bằng GitHub Actions, VPS, Docker Compose, PostgreSQL, Nginx, HTTPS và Google Gemini API.

## Mục Tiêu

- Không deploy production trực tiếp từ máy cá nhân của developer.
- GitHub Actions là điểm điều phối build, test, deploy và rollback.
- Tách rõ staging từ `develop` và production từ `main`.
- Production tự build, test và deploy khi có code hợp lệ vào `main`.
- Không lưu secret thật trong repository hoặc log.
- Có health check, smoke test, backup PostgreSQL và rollback có kiểm chứng.

## Kiến Trúc Production-Like

- VPS Ubuntu chạy Docker Compose.
- Nginx reverse proxy domain về frontend và backend API.
- Frontend React build static và phục vụ qua container Nginx.
- Backend ASP.NET Core Web API chạy theo modular monolith.
- PostgreSQL lưu dữ liệu thật, có volume persistent và health check.
- AI service Python RAG gọi trực tiếp Google Gemini API qua HTTPS.
- `GEMINI_API_KEY` chỉ được cấp cho container AI, không truyền xuống frontend hay container backend.

## Luồng CI/CD

### Pull Request

PR vào `main` hoặc `develop` phải qua CI:

- Frontend install và build.
- Backend restore, build và test.
- AI service unit test.
- Docker Compose config validation.

### Staging

Khi push hoặc merge vào `develop`:

1. Workflow `Deploy Staging` chạy với environment `staging`.
2. GitHub Secrets được ghi thành `.env` trên VPS.
3. Docker Compose build/start các service.
4. Nginx và Certbot được cấu hình.
5. Health check kiểm tra frontend và API.
6. Kết quả ghi vào report trên VPS.

### Production

Khi push hoặc merge vào `main`:

1. Workflow `Deploy Production` chạy lại CI thông qua reusable workflow.
2. Nếu CI fail, deploy không bắt đầu.
3. Nếu CI pass, workflow deploy production lên VPS.
4. PostgreSQL migration chạy bằng container one-shot `migrate` trước khi API start; `RUN_DB_MIGRATIONS_ON_STARTUP=false` ở deploy mặc định.
5. Backup PostgreSQL được tạo trước health check.
6. Health check và smoke check xác nhận release.

## Secrets Và Variables

Không commit giá trị thật. Các biến nhạy cảm phải nằm trong GitHub Secrets hoặc `.env` trên VPS.

Staging:

```text
STAGING_HOST
STAGING_SSH_USER
STAGING_SSH_KEY
STAGING_POSTGRES_PASSWORD
JWT_SIGNING_KEY
GEMINI_API_KEY
CERTBOT_EMAIL
```

Production:

```text
PRODUCTION_HOST
PRODUCTION_SSH_USER
PRODUCTION_SSH_KEY
PRODUCTION_POSTGRES_PASSWORD
JWT_SIGNING_KEY
GEMINI_API_KEY
CERTBOT_EMAIL
```

Variables khuyến nghị:

```text
AI_MODEL=gh/gemini-3.1-pro-preview
```

## Docker Compose

File triển khai chính: `deploy/docker-compose.yml`.

Service bắt buộc:

- `postgres`: PostgreSQL 16, persistent volume, health check.
- `api`: ASP.NET Core API, đọc `ConnectionStrings__DefaultConnection`.
- `ai-service`: Python RAG service.
- `frontend`: React static build.

Kiểm tra cấu hình:

```bash
docker compose -f deploy/docker-compose.yml config
```

## Health Check Và Smoke Test

Backend:

```bash
curl -fsS https://api.cmcrestaurant.app/api/health
curl -fsS https://api-staging.cmcrestaurant.app/api/health
```

Frontend:

```bash
curl -fsS https://cmcrestaurant.app/ >/dev/null
curl -fsS https://order.cmcrestaurant.app/ >/dev/null
curl -fsS https://staging.cmcrestaurant.app/ >/dev/null
curl -fsS https://order-staging.cmcrestaurant.app/ >/dev/null
```

Report sau deploy:

```text
/opt/cmc-restaurant/<environment>/reports/last-deployment.md
```

## Backup Và Restore

Runbook chi tiết nằm tại `docs/PRODUCTION_OPERATIONS.md`.

Backup PostgreSQL production:

```bash
cd /opt/cmc-restaurant/production
set -a && . ./.env && set +a
bash repo/deploy/scripts/backup-postgres.sh manual
```

Restore PostgreSQL production:

```bash
cd /opt/cmc-restaurant/production
set -a && . ./.env && set +a
bash repo/deploy/scripts/restore-postgres.sh /opt/cmc-restaurant/production/backups/<file>.dump
```

## Rollback

Rollback dùng workflow `Rollback` với input `staging` hoặc `production`.

Script rollback trên VPS:

```text
deploy/scripts/rollback-vps.sh
```

Rollback thành công khi:

- `repo.previous` được đưa lại làm bản chạy chính.
- Docker Compose start lại thành công.
- Backup sau rollback được tạo.
- Health check pass.
- Report deploy mới được ghi.

## Evidence Khi Đóng Issue DevOps

Mỗi issue DevOps triển khai phải có comment evidence riêng, gồm:

- PR link.
- CI hoặc workflow run link.
- `docker compose config` result.
- Smoke/health check result.
- Backup command hoặc log.
- Danh sách secret/env đã cấu hình, không lộ giá trị thật.

## Trạng Thái Issue #16 Và #78

Issue #16 thiết kế luồng CI/CD tự động:

- CI: `.github/workflows/ci.yml`
- Auto-merge: `.github/workflows/auto-merge.yml`
- Staging deploy: `.github/workflows/deploy-staging.yml`
- Production deploy: `.github/workflows/deploy-production.yml`
- Promote production: `.github/workflows/promote-production.yml`
- Rollback: `.github/workflows/rollback.yml`

Issue #78 gia cố vận hành production:

- PostgreSQL trong Docker Compose deploy.
- Secrets tách khỏi repo.
- Backup/restore PostgreSQL.
- Health report sau deploy.
- Runbook vận hành: `docs/PRODUCTION_OPERATIONS.md`.
