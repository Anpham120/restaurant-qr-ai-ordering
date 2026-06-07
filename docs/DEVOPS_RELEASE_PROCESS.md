# Quy Trình DevOps Và Release

Tài liệu này mô tả cách dự án **Restaurant QR AI Ordering** tách vai trò Developer, Lead và DevOps/Release Owner. Mục tiêu là tránh mô hình "developer tự deploy từ máy cá nhân" và chuyển sang quy trình CI/CD có kiểm soát.

Trạng thái hiện tại: đây là **kế hoạch DevOps đã chốt cho issue #16**, chưa phải pipeline đã triển khai. Khi chưa có `.github/workflows/**`, Docker/deploy config và branch ruleset thật trên GitHub, dự án chưa được xem là có CI/CD tự động hoàn chỉnh.

## Mục Tiêu

Dự án áp dụng mức **DevOps Level 3 cho phạm vi học thuật/MVP**:

- Có CI bắt buộc cho frontend và backend.
- Có branch protection cho `develop` và `main`.
- Có required status checks, ruleset, auto-merge và merge queue.
- Không yêu cầu review/approval thủ công trong luồng bình thường.
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

### Lead

- Thiết lập tiêu chuẩn chất lượng, required checks và ruleset.
- Theo dõi issue/PR ở mức quản trị, không làm bước review thủ công bắt buộc trong luồng bình thường.
- Can thiệp khi pipeline fail, PR sai phạm vi, hoặc có rủi ro lớn.
- Không deploy production từ máy cá nhân.
- Không duyệt deploy thủ công sau khi `main` đã nhận code.

### DevOps / Release Owner

- Sở hữu workflow CI/CD.
- Sở hữu branch protection, GitHub Environments và secrets.
- Cấu hình auto-merge, merge queue và required status checks.
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
7. Bot/workflow kiểm tra scope cơ bản, required checks và điều kiện ruleset.
8. Nếu mọi điều kiện đạt, auto-merge đưa PR vào merge queue.
9. Merge queue chạy lại required checks trên trạng thái mới nhất của `develop`.
10. Nếu merge queue pass, GitHub tự hợp nhất vào `develop`.
11. Sau khi merge/push vào `develop`, staging deployment tự chạy.
12. Staging health check và smoke check tự chạy.

## Luồng B - Promote Từ `develop` Sang `main`

1. Staging deployment từ `develop` hoàn tất.
2. Staging health check và smoke check đạt.
3. Workflow `promote-production` tự tạo hoặc cập nhật PR từ `develop` sang `main`.
4. GitHub Actions CI chạy lại trên release PR.
5. Release PR đi qua required checks và merge queue, không cần review thủ công trong luồng bình thường.
6. Nếu queue pass, GitHub tự merge PR vào `main`.
7. Sau khi merge/push vào `main`, production workflow tự chạy.
8. Không có bước duyệt deploy thủ công sau khi `main` nhận code.

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
- Nếu check đạt, kích hoạt hoặc cho phép workflow promote production.

### `.github/workflows/auto-merge.yml`

- Trigger khi PR vào `develop` hoặc `main` được mở/cập nhật.
- Kiểm tra PR đúng nhánh nguồn, đúng target và không có file ngoài phạm vi issue nếu có rule.
- Bật auto-merge cho PR khi required checks đủ điều kiện.
- Không thay thế CI; chỉ điều phối merge sau khi CI/ruleset đạt.

### `.github/workflows/promote-production.yml`

- Trigger sau khi staging deploy và smoke check từ `develop` đạt.
- Tạo hoặc cập nhật PR `develop` -> `main`.
- Gắn auto-merge cho release PR.
- Không yêu cầu người bấm review/approve trong luồng bình thường.

### `.github/workflows/deploy-production.yml`

- Trigger tự động khi push vào `main`.
- Chạy lại build/test trước deploy.
- Không có manual approval sau khi `main` nhận code.
- Deploy production bằng Docker Compose hoặc artifact đã document.
- Chạy health/smoke check.
- Fail workflow và rollback nếu deployment lỗi.

### `.github/workflows/rollback.yml`

- Trigger khi deploy production fail hoặc chạy thủ công trong tình huống khẩn cấp.
- Rollback về image/artifact gần nhất đã pass health check.
- Ghi rõ commit/image rollback, nguyên nhân và kết quả kiểm tra sau rollback.

## Branch Protection

### `develop`

- Require pull request before merge.
- Require status checks: frontend build, backend build/test, secret/security checks nếu có.
- Require merge queue.
- Cho phép auto-merge sau khi required checks và merge queue đạt.
- Không require human review trong luồng bình thường.
- Không cho force push.
- Không cho delete branch.
- Merge/push vào `develop` sẽ kích hoạt staging deployment.

### `main`

- Require pull request before merge.
- Require status checks: CI release, Docker/artifact build, smoke plan nếu có.
- Require merge queue.
- Chỉ chấp nhận release PR từ `develop` sang `main` do workflow promote tạo/cập nhật.
- Cho phép auto-merge sau khi required checks và merge queue đạt.
- Không require human review trong luồng bình thường.
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

## Issue #16 DevOps Implementation Update

Quy trinh DevOps da duoc chuyen tu ke hoach sang cau hinh co the chay:

- PR vao `develop`/`main` kich hoat `CI`.
- `Auto Merge` co gang bat auto-merge cho PR khong phai draft.
- Push vao `develop` kich hoat `Deploy Staging`.
- Staging pass kich hoat `Promote Production`, tao/cap nhat PR tu `develop`
  sang `main` va co gang bat auto-merge.
- Push vao `main` kich hoat `Deploy Production`.
- `Rollback` cho phep quay lai ban deploy truoc do theo environment.

Lead/DevOps van phai bat repository settings tuong ung: allow auto-merge,
required checks va merge queue/ruleset cho `develop` va `main`. GitHub Secrets
bat buoc gom SSH deploy secrets, `JWT_SIGNING_KEY`, `AI_BASE_URL`, `AI_MODEL`
va `AI_API_KEY`. Khong dong issue #16 neu chua co Actions run/deploy evidence.
