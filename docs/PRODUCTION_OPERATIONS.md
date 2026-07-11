# Production Operations Runbook

Tài liệu này mô tả cách vận hành staging/production cho CMC Restaurant theo issue #78. Mục tiêu là triển khai có kiểm soát, không hard-code secret, có PostgreSQL thật, có backup/restore và có bằng chứng smoke test sau deploy.

## Kiến Trúc Triển Khai

- GitHub Actions là điểm điều phối CI/CD.
- VPS chạy Docker Compose cho `frontend`, `api`, `ai-service` và `postgres`.
- Nginx trên VPS reverse proxy domain về các port nội bộ.
- PostgreSQL chỉ bind trên `127.0.0.1:<POSTGRES_PORT>`, không mở public internet.
- 9router chạy local trên VPS tại `http://127.0.0.1:20128/v1`.
- Secrets nằm trong GitHub Actions Secrets hoặc file `.env` trên VPS, không commit vào repo.

## Domain Và Port

| Môi trường | Frontend | API | Frontend port | API port | PostgreSQL port |
| --- | --- | --- | --- | --- | --- |
| Staging | `staging.cmcrestaurant.app` | `api-staging.cmcrestaurant.app` | `8081` | `5001` | `5433` |
| Production | `cmcrestaurant.app`, `customer.cmcrestaurant.app`, `admin.cmcrestaurant.app` | `api.cmcrestaurant.app` | `8080` | `5000` | `5432` |

## GitHub Secrets Cần Có

Repository hoặc Environment `staging`:

```text
STAGING_HOST
STAGING_SSH_USER
STAGING_SSH_KEY
STAGING_POSTGRES_PASSWORD
JWT_SIGNING_KEY
AI_API_KEY
CERTBOT_EMAIL
```

Repository hoặc Environment `production`:

```text
PRODUCTION_HOST
PRODUCTION_SSH_USER
PRODUCTION_SSH_KEY
PRODUCTION_POSTGRES_PASSWORD
JWT_SIGNING_KEY
AI_API_KEY
CERTBOT_EMAIL
```

GitHub Variables khuyến nghị:

```text
AI_MODEL=gh/gemini-3.1-pro-preview
```

## Luồng Deploy

1. PR vào `main` phải qua CI.
2. Khi merge/push vào `main`, workflow production chạy lại CI trước deploy.
3. Workflow tạo release bundle, SSH vào VPS, ghi `.env` từ GitHub Secrets.
4. Docker Compose build và start `postgres`, sau đó chạy container `migrate` one-shot.
5. Chỉ khi migration thành công, Docker Compose start `ai-service`, `api`, `frontend`; API không tự đổi schema lúc boot.
6. Script tạo backup PostgreSQL trước health check.
7. Script ghi Nginx config, cấp hoặc gia hạn TLS bằng Certbot.
8. Health check kiểm tra frontend và `/api/health`.
9. Kết quả deploy được ghi tại `/opt/cmc-restaurant/<env>/reports/last-deployment.md`.

### Preflight migration phiên bàn

Migration `EnforceSingleActiveTableSession` tự đánh dấu những phiên `Open` đã quá `expires_at` là `Expired`, sau đó áp dụng ràng buộc mỗi bàn chỉ có một phiên live. Trước deploy, chạy truy vấn sau trên PostgreSQL; kết quả phải rỗng:

```sql
SELECT restaurant_table_id, array_agg(id ORDER BY opened_at DESC) AS session_ids
FROM table_sessions
WHERE status = 'Open'
  AND closed_at IS NULL
  AND expires_at > NOW()
GROUP BY restaurant_table_id
HAVING COUNT(*) > 1;
```

Nếu còn kết quả, không tự đóng phiên live: xác nhận với vận hành/bộ phận nhà hàng phiên nào còn hợp lệ rồi đóng phiên còn lại trước khi deploy.

## Backup PostgreSQL

Backup thủ công trên VPS:

```bash
cd /opt/cmc-restaurant/production
set -a && . ./.env && set +a
bash repo/deploy/scripts/backup-postgres.sh manual
```

Kết quả:

- File dump nằm trong `/opt/cmc-restaurant/production/backups`.
- Mỗi file có checksum `.sha256`.
- Script tự xóa backup cũ hơn 14 ngày.

Backup staging tương tự, đổi `production` thành `staging`.

## Restore PostgreSQL

Restore chỉ thực hiện khi đã xác nhận cần khôi phục dữ liệu:

```bash
cd /opt/cmc-restaurant/production
set -a && . ./.env && set +a
bash repo/deploy/scripts/restore-postgres.sh /opt/cmc-restaurant/production/backups/<file>.dump
```

Script sẽ:

- Kiểm tra file backup tồn tại.
- Kiểm tra checksum nếu có.
- Drop và tạo lại database.
- Restore bằng `pg_restore`.
- Chạy health check sau restore.

## Rollback

Rollback workflow dùng GitHub Actions `Rollback` với input `staging` hoặc `production`.

Trên VPS, script:

1. Chuyển `repo` hiện tại thành `repo.failed.<timestamp>`.
2. Đưa `repo.previous` quay lại làm bản chạy chính.
3. Chạy lại Docker Compose.
4. Tạo backup sau rollback.
5. Ghi lại Nginx config và chạy health check.

Rollback chỉ được xem là thành công khi health check pass và có report mới trong `reports/last-deployment.md`.

## Smoke Test Sau Deploy

Các lệnh kiểm tra tối thiểu:

```bash
curl -fsS https://cmcrestaurant.app/ >/dev/null
curl -fsS https://api.cmcrestaurant.app/api/health
curl -fsS https://staging.cmcrestaurant.app/ >/dev/null
curl -fsS https://api-staging.cmcrestaurant.app/api/health
```

Kiểm tra container trên VPS:

```bash
cd /opt/cmc-restaurant/production
set -a && . ./.env && set +a
docker compose --env-file .env -f repo/deploy/docker-compose.yml -p "$COMPOSE_PROJECT_NAME" ps
```

## Definition Of Done Cho Issue #78

- `docker compose -f deploy/docker-compose.yml config` pass với env CI.
- Backend có connection string PostgreSQL thật trong deploy compose.
- PostgreSQL có volume persistent và health check.
- Có script backup và restore PostgreSQL.
- Có tài liệu secrets, deploy, smoke test và rollback.
- Không có secret thật trong repo.
- PR có link `Closes #78` và comment evidence gồm PR, CI, smoke/config log, backup command/log.
