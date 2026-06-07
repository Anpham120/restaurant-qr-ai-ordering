# Tài Liệu Triển Khai

Tài liệu này mô tả hướng triển khai production-like cho **Restaurant QR AI Ordering** bằng VPS, Docker Compose, Nginx, HTTPS và GitHub Actions.

Trạng thái hiện tại: đây là **kế hoạch triển khai đã chốt cho issue #16**, chưa phải hệ thống deploy đang chạy. Chỉ xem là đã triển khai khi có workflow GitHub Actions, Docker/deploy config, secrets/environments và bằng chứng health check thật.

## Mục Tiêu Triển Khai

- Không deploy chính thức từ máy cá nhân của developer.
- Dùng GitHub Actions làm điểm điều phối CI/CD.
- Tự động hóa merge bằng required checks, merge queue và auto-merge.
- Tách staging từ `develop` và production từ `main`.
- Production tự build-test-deploy khi có push/merge vào `main`.
- Có health check, smoke check, monitoring cơ bản và rollback.

## Kiến Trúc Production-Like

Mô hình v1 khuyến nghị:

- Một VPS hoặc production-like host.
- Docker Compose để chạy các service.
- Nginx làm reverse proxy.
- HTTPS bằng Let's Encrypt hoặc cấu hình tương đương.
- Frontend React build static.
- Backend ASP.NET Core Web API.
- PostgreSQL nếu cần lưu dữ liệu.
- pgvector nếu dùng RAG.
- Redis nếu cần cache hoặc queue.
- External LLM API cho chatbot AI, không yêu cầu GPU.

## Biến Môi Trường Và Secrets

Không commit secrets thật vào repository. Các giá trị nhạy cảm phải nằm trong GitHub Secrets, GitHub Environments hoặc `.env` trên VPS.

Nhóm biến cần document:

```text
ASPNETCORE_ENVIRONMENT=Production
DATABASE_URL=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
REDIS_URL=
JWT_SECRET=
LLM_API_KEY=
LLM_API_BASE_URL=
FRONTEND_PUBLIC_API_URL=
FRONTEND_PUBLIC_SIGNALR_URL=
DEPLOY_HOST=
DEPLOY_USER=
DEPLOY_SSH_KEY=
PRODUCTION_DOMAIN=
STAGING_DOMAIN=
```

## CI/CD Tự Động

### CI

CI chạy trên:

- PR vào `develop`.
- PR vào `main`.
- Push vào `develop`.
- Manual rerun qua `workflow_dispatch` nếu cần.

CI phải kiểm tra:

- Frontend install và build.
- Backend restore, build và test.
- Docker Compose syntax nếu đã có compose file.

### Staging Từ `develop`

Khi merge/push vào `develop`:

1. GitHub Actions chạy workflow staging.
2. Workflow dùng staging secrets.
3. Workflow deploy staging hoặc demo environment.
4. Workflow chạy health/smoke check.
5. Nếu check lỗi, workflow fail và ghi log.
6. Nếu check đạt, workflow promote tạo hoặc cập nhật PR `develop` -> `main` và bật auto-merge.

### Production Từ `main`

Khi merge/push vào `main`:

1. GitHub Actions chạy production workflow tự động.
2. Workflow chạy lại build/test trước deploy.
3. Nếu build/test fail, deploy không được bắt đầu.
4. Nếu build/test pass, deploy production tự động.
5. Không có bước bấm deploy, SSH thủ công, review thủ công hoặc duyệt deploy sau khi `main` nhận code.
6. Workflow chạy health/smoke check sau deploy.
7. Nếu check fail, workflow fail và rollback hoặc in checklist rollback.

## Docker Compose Plan

Nếu triển khai bằng Docker Compose, cấu trúc service nên gồm:

```yaml
services:
  frontend:
    # React static build served by Nginx or container web server

  backend:
    # ASP.NET Core API

  postgres:
    # PostgreSQL database

  redis:
    # Optional cache/queue service

  nginx:
    # Reverse proxy and HTTPS entrypoint
```

Yêu cầu tối thiểu:

- Service backend đọc env từ secrets hoặc `.env`.
- Database data dùng volume.
- Nginx route frontend và `/api`.
- Không hard-code secrets vào image hoặc compose file.
- `docker compose config` chạy được trước khi deploy.

## Health Check

Sau mỗi deployment:

```bash
curl -fsS https://<domain>/api/health
curl -I https://<domain>/
curl -I https://<domain>/menu
curl -I https://<domain>/cart
```

Kết quả kỳ vọng:

- `/api/health` trả HTTP 200.
- Frontend route trả HTTP 200 hoặc SPA fallback hợp lệ.
- Không có lỗi 500, 502, 503.

Nếu chưa có domain thật, dùng IP/VPS hoặc môi trường local tương đương và ghi rõ trong báo cáo.

## Monitoring Cơ Bản

Khuyến nghị dùng UptimeRobot, Better Stack hoặc dịch vụ tương đương.

Monitor tối thiểu:

- `https://<domain>/`
- `https://<domain>/api/health`

Cấu hình khuyến nghị:

- Interval: 5 phút nếu gói miễn phí cho phép.
- Failure condition: HTTP 5xx, timeout hoặc endpoint health không trả 200.
- Người nhận cảnh báo: DevOps/Release Owner.
- Phản ứng đầu tiên: kiểm tra GitHub Actions deployment run, log Nginx, log backend và trạng thái container.

## Rollback

Rollback cần rõ ràng trước khi production được xem là ổn định.

Checklist:

1. Xác nhận deployment hiện tại failed.
2. Xác định commit, tag hoặc image gần nhất chạy ổn.
3. Redeploy phiên bản gần nhất chạy ổn.
4. Restart service bằng Docker Compose.
5. Chạy lại backend health check.
6. Chạy lại frontend smoke check.
7. Ghi rollback result vào báo cáo.

Ví dụ lệnh khi dùng Docker Compose:

```bash
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 backend
```

## Báo Cáo Triển Khai

Mỗi lần staging hoặc production deploy cần ghi:

```text
Môi trường:
Branch:
Commit:
Workflow run:
Người chịu trách nhiệm:
Thời gian deploy:
Kết quả build/test:
Kết quả health check:
Kết quả smoke check:
Rollback có cần không:
Ghi chú secrets/no-secrets:
Kết luận:
```

## Khi Chưa Có VPS Thật

Nếu dự án chưa có VPS hoặc domain thật, PR DevOps vẫn phải cung cấp:

- Workflow YAML dự kiến hoặc bản document chính xác.
- Danh sách GitHub Secrets cần có.
- Lệnh deploy dự kiến.
- Lệnh health/smoke check.
- Rollback checklist.
- Ghi chú rõ rằng production auto-deploy đã được thiết kế nhưng chưa chạy thật do thiếu deployment target.

## Issue #16 Deployment Implementation Update

Repo da co cau hinh trien khai production-like bang GitHub Actions, Docker
Compose, Nginx va Certbot:

- CI: `.github/workflows/ci.yml`
- Auto-merge attempt: `.github/workflows/auto-merge.yml`
- Staging deploy tu `develop`: `.github/workflows/deploy-staging.yml`
- Promote `develop` sang `main`: `.github/workflows/promote-production.yml`
- Production deploy tu `main`: `.github/workflows/deploy-production.yml`
- Rollback thu cong co kiem soat: `.github/workflows/rollback.yml`
- Docker/deploy config: `backend/Dockerfile`, `frontend/Dockerfile`,
  `deploy/docker-compose.yml`, `deploy/scripts/**`
- Branch ruleset can bat theo: `docs/BRANCH_RULESET.md`
- Required secrets: `STAGING_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY`,
  `PRODUCTION_HOST`, `PRODUCTION_SSH_USER`, `PRODUCTION_SSH_KEY`,
  `JWT_SIGNING_KEY`, `AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY`
- 9router tren VPS giu private tai `127.0.0.1:20128`; backend container dung
  host network de goi `AI_BASE_URL=http://127.0.0.1:20128/v1`.

Issue #16 chi duoc dong khi co bang chung workflow chay that: CI pass,
staging/production deploy pass, health/smoke check pass va branch/ruleset duoc
bat tren GitHub.
