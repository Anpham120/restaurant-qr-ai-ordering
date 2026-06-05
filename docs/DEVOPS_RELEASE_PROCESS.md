# Quy Trình DevOps Và Release

Tài liệu này mô tả cách dự án **Restaurant QR AI Ordering** tách vai trò Developer, Reviewer/Lead và DevOps/Release Owner. Mục tiêu là tránh mô hình "developer tự deploy từ máy cá nhân" và chuyển sang quy trình CI/CD có kiểm soát.

## Mục Tiêu

Dự án áp dụng mức **DevOps Level 2.5** phù hợp phạm vi học thuật:

- Có CI bắt buộc cho frontend và backend.
- Có branch protection cho `develop` và `main`.
- Có auto-merge sau khi CI đạt và có approval cần thiết.
- Có staging deployment tự động từ `develop`.
- Có production build-test-deploy tự động từ `main`.
- Có health check, smoke check, monitoring cơ bản và rollback.
- Có báo cáo triển khai để phục vụ demo và đánh giá.

## Phân Tách Vai Trò

### Developer

- Làm feature trên branch issue riêng.
- Chạy build/test phù hợp trước khi mở PR.
- Mở PR vào `develop`.
- Cung cấp bằng chứng kiểm thử trong issue hoặc PR.
- Không deploy production thủ công.
- Không giữ production secrets.
- Không tắt CI để merge code.

### Reviewer / Lead

- Review scope, code và bằng chứng kiểm thử.
- Duyệt PR trước khi auto-merge được phép chạy.
- Duyệt release PR từ `develop` sang `main` trước khi code đi vào `main`.
- Không deploy production từ máy cá nhân.
- Không duyệt deploy thủ công sau khi `main` đã nhận code.

### DevOps / Release Owner

- Sở hữu workflow CI/CD.
- Sở hữu branch protection, GitHub Environments và secrets.
- Cấu hình staging deployment từ `develop`.
- Cấu hình production build-test-deploy từ `main`.
- Thiết lập health check, smoke check và rollback.
- Ghi báo cáo triển khai/release.

## Luồng A - Tích Hợp Feature Vào `develop`

1. Developer tạo branch từ `develop`.
2. Developer làm issue được giao.
3. Developer chạy kiểm thử cục bộ phù hợp.
4. Developer mở PR từ branch issue vào `develop`.
5. GitHub Actions CI tự chạy trên PR.
6. CI kiểm tra frontend build và backend restore/build/test.
7. Reviewer/Lead review scope và bằng chứng.
8. Auto-merge chỉ được chạy khi CI đạt, PR đúng scope và có approval.
9. Sau khi merge/push vào `develop`, staging deployment tự chạy.
10. Staging health check và smoke check tự chạy.

## Luồng B - Release Từ `develop` Sang `main`

1. Lead/Release Owner xác nhận `develop` đã sẵn sàng release.
2. Tạo PR từ `develop` sang `main`.
3. GitHub Actions CI chạy lại trên release PR.
4. Release PR chỉ được merge khi CI đạt, checklist demo sẵn sàng và có approval.
5. Sau khi merge/push vào `main`, production workflow tự chạy.
6. Không có bước duyệt deploy thủ công sau khi `main` nhận code.

## Luồng C - Production Tự Động Từ `main`

Khi có push/merge vào `main`, workflow production phải chạy theo thứ tự:

1. Checkout đúng trạng thái repository trên `main`.
2. Chạy CI/build/test lại cho release.
3. Nếu CI/build/test thất bại, không được deploy.
4. Nếu kiểm tra đạt, deploy production tự động.
5. Đọc cấu hình từ GitHub Secrets, GitHub Environments hoặc `.env` trên VPS.
6. Khởi động hoặc cập nhật frontend, backend, database, Redis và Nginx nếu có.
7. Chạy backend health check và frontend smoke check.
8. Nếu health/smoke check đạt, ghi nhận triển khai thành công.
9. Nếu health/smoke check lỗi, workflow phải fail và chạy rollback hoặc in checklist rollback rõ ràng.

## Workflow CI/CD Cần Có

### `.github/workflows/ci.yml`

Trigger:

```yaml
on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop]
  workflow_dispatch:
```

Kiểm tra bắt buộc:

```bash
cd frontend
npm ci
npm run build

dotnet restore backend/RestaurantQrAiOrdering.sln
dotnet build backend/RestaurantQrAiOrdering.sln --configuration Release --no-restore
dotnet test backend/RestaurantQrAiOrdering.sln --configuration Release --no-build
```

### `.github/workflows/deploy-staging.yml`

- Trigger tự động khi push vào `develop`.
- Dùng secrets và biến môi trường staging.
- Deploy stack staging hoặc bản demo tương đương.
- Chạy health/smoke check.
- Fail workflow nếu check lỗi.

### `.github/workflows/deploy-production.yml`

- Trigger tự động khi push vào `main`.
- Chạy lại build/test trước deploy.
- Không có manual approval sau khi `main` nhận code.
- Deploy production bằng Docker Compose hoặc artifact đã document.
- Chạy health/smoke check.
- Fail workflow và rollback nếu deployment lỗi.

## Branch Protection

### `develop`

- Require pull request before merge.
- Require CI pass.
- Require ít nhất một approval.
- Cho phép auto-merge sau khi đủ điều kiện.
- Không cho force push.
- Không cho delete branch.
- Merge/push vào `develop` sẽ kích hoạt staging deployment.

### `main`

- Require pull request before merge.
- Require CI pass.
- Require Lead/DevOps approval.
- Chỉ chấp nhận release PR từ `develop` sang `main`.
- Cho phép auto-merge sau khi đủ điều kiện.
- Không cho force push.
- Không cho delete branch.
- Merge/push vào `main` sẽ kích hoạt production build-test-deploy tự động.

Branch protection là cổng kiểm soát code trước khi vào `main`, không phải là bước duyệt deploy thủ công sau khi code đã vào `main`.

## Health Check Và Smoke Check

Sau mỗi lần deploy, workflow cần kiểm tra tối thiểu:

```bash
curl -fsS https://<domain>/api/health
curl -I https://<domain>/
curl -I https://<domain>/menu
curl -I https://<domain>/cart
```

Kết quả kỳ vọng:

- Backend trả HTTP 200.
- Frontend route trả HTTP 200 hoặc SPA fallback hợp lệ.
- Không có lỗi 500, 502 hoặc 503.
- Báo cáo triển khai ghi lại thời gian, commit và kết quả.

## Rollback

Khi deploy thất bại:

1. Dừng hoặc đánh dấu deployment là failed.
2. Quay lại commit, tag hoặc image gần nhất đã chạy ổn.
3. Restart service.
4. Chạy lại backend health check.
5. Chạy lại frontend smoke check.
6. Ghi kết quả rollback vào báo cáo triển khai.

Không được đánh dấu deployment thành công nếu rollback chưa được thực hiện hoặc chưa có bằng chứng.

## Bằng Chứng Cần Lưu

- Link PR.
- Link CI run hoặc log build/test.
- Link staging deployment run.
- Link production deployment run.
- Bằng chứng health/smoke check.
- Bằng chứng không commit secrets thật.
- Ghi chú branch protection đã áp dụng trực tiếp hay mới document.
- Báo cáo rollback nếu có lỗi.
