# Quy Trình Git

Tài liệu này quy định cách dùng branch, pull request và release cho dự án **Restaurant QR AI Ordering**. README chỉ giới thiệu dự án; toàn bộ quy trình làm việc, review và CI/CD được đặt trong tài liệu này và các tài liệu DevOps liên quan.

## 1. Mô Hình Branch

Dự án sử dụng ba nhóm branch chính:

- `main`: nhánh release/production. Khi có push hoặc merge vào `main`, production workflow phải tự chạy build, test và deploy nếu kiểm tra đạt.
- `develop`: nhánh tích hợp. Khi có push hoặc merge vào `develop`, staging workflow phải tự chạy nếu kiểm tra đạt.
- `issue-<number>/<github-username>-<short-task>`: branch riêng cho từng issue.

Không làm việc trực tiếp trên `main`. Với `develop`, chỉ push trực tiếp khi Lead cho phép trong tình huống đặc biệt; mặc định mọi thay đổi đi qua PR.

## 2. Quy Trình Làm Issue

1. Đọc issue được giao.
2. Kiểm tra `Goal`, `Allowed Files / Areas`, `Do Not Touch` và `Acceptance Criteria`.
3. Cập nhật branch nền:

```bash
git checkout develop
git pull origin develop
```

4. Tạo branch đúng format:

```bash
git checkout -b issue-<number>/<github-username>-<short-task>
```

5. Làm đúng phạm vi issue.
6. Chạy build/test phù hợp.
7. Commit bằng Conventional Commits.
8. Push branch lên GitHub.
9. Mở PR vào `develop`.
10. PR phải có `Closes #<issue_number>`.
11. Comment báo cáo kết quả trong issue hoặc PR.

## 3. Pull Request Vào `develop`

PR vào `develop` phải đạt:

- Đúng phạm vi issue.
- Không sửa file ngoài scope nếu chưa được Lead đồng ý.
- Có bằng chứng build/test.
- CI frontend/backend pass.
- Có reviewer approval.
- Có thể bật auto-merge sau khi đủ điều kiện.

Sau khi PR được merge vào `develop`, staging deployment tự chạy. Developer không deploy staging hoặc production từ máy cá nhân.

## 4. Release Từ `develop` Sang `main`

Release production đi qua PR từ `develop` sang `main`.

Điều kiện merge:

- CI chạy lại và pass trên release PR.
- Checklist demo đã sẵn sàng.
- Không còn issue critical mở.
- Lead/DevOps approval đã có.
- Branch protection không bị tắt để merge nhanh.

Sau khi code vào `main`, production workflow tự chạy. Không có bước duyệt deploy thủ công sau khi `main` nhận code.

## 5. CI/CD Theo Branch

### `develop`

- PR vào `develop`: chạy CI.
- Push/merge vào `develop`: chạy CI và staging deploy nếu đạt.
- Nếu staging health/smoke check fail, workflow phải fail và báo lại trong PR/issue.

### `main`

- PR vào `main`: chạy CI.
- Push/merge vào `main`: chạy production build-test-deploy tự động.
- Nếu build/test fail, deployment không được bắt đầu.
- Nếu health/smoke check fail, workflow phải fail và rollback hoặc in checklist rollback.

## 6. Branch Protection

### `develop`

- Require pull request before merge.
- Require CI pass.
- Require ít nhất một approval.
- Allow auto-merge sau khi đủ điều kiện.
- Block force push.
- Block deletion.

### `main`

- Require pull request before merge.
- Require CI pass.
- Require Lead/DevOps approval.
- Chỉ chấp nhận release PR từ `develop`.
- Allow auto-merge sau khi đủ điều kiện.
- Block force push.
- Block deletion.

Branch protection là cổng kiểm soát trước khi code vào branch quan trọng. Nó không phải là bước duyệt deploy sau khi code đã vào `main`.

## 7. Conventional Commits

Nên dùng commit rõ nghĩa:

```bash
feat: add customer order placement api
fix: correct unavailable menu item validation
docs: add devops release process
ci: add frontend and backend build workflow
chore: add docker compose deployment config
test: add order service integration tests
```

Không dùng commit mơ hồ:

```bash
update
fix bug
done
new code
```

## 8. Quy Tắc Cho AI Agent

Khi dùng AI agent hỗ trợ lập trình, agent phải làm đúng issue đang được giao.

AI agent được phép:

- Sửa đúng file trong phạm vi issue.
- Chạy kiểm tra phù hợp.
- Báo cáo rõ thay đổi, test và giới hạn.
- Hỏi lại nếu cần sửa ngoài scope.

AI agent không được phép:

- Tự ý đổi API contract, enum, database field hoặc route dùng chung.
- Tự ý sửa vùng code của issue khác.
- Push trực tiếp vào `main`.
- Commit secrets thật.
- Đóng issue khi chưa có bằng chứng.

## 9. Checklist Trước Khi Yêu Cầu Review

- [ ] Branch đúng format.
- [ ] PR target là `develop`, trừ release PR từ `develop` sang `main`.
- [ ] PR có `Closes #<issue_number>`.
- [ ] Diff đúng phạm vi issue.
- [ ] Frontend build đã chạy nếu có sửa frontend.
- [ ] Backend restore/build/test đã chạy nếu có sửa backend.
- [ ] CI/CD evidence đã được ghi nếu có sửa DevOps.
- [ ] Không commit secrets thật.
- [ ] Đã báo cáo kết quả trong issue hoặc PR.
