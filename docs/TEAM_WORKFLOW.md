# Quy Trình Làm Việc Nhóm

Tài liệu này mô tả cách nhóm phối hợp khi phát triển **Restaurant QR AI Ordering**. README dùng để giới thiệu dự án; tài liệu này dùng cho phân công, policy CI/CD, báo cáo và phối hợp với AI agent.

Trạng thái hiện tại: pipeline DevOps tự động đã được triển khai trong `.github/workflows/**`; phần còn lại để hoàn tất là bật branch ruleset, required checks/merge queue và cấu hình GitHub Secrets trên repo.

## 1. Vai Trò Chính

### Lead

- Điều phối milestone, issue và phạm vi công việc.
- Thiết lập tiêu chuẩn chất lượng, scope issue và rule cần kiểm tra tự động.
- Theo dõi ngoại lệ khi pipeline fail hoặc PR có rủi ro lớn.
- Đảm bảo tài liệu, demo và báo cáo cuối cùng nhất quán.

### Developer

- Làm issue được giao trên branch riêng.
- Giữ thay đổi trong đúng phạm vi issue.
- Chạy build/test phù hợp trước khi mở PR.
- Không deploy production thủ công.
- Không giữ production secrets.

### Reviewer / Quality Gate

- Trong luồng bình thường, quality gate là CI, required checks, ruleset và merge queue.
- Review thủ công chỉ dùng khi pipeline fail, PR vượt phạm vi, hoặc Lead/DevOps đánh dấu rủi ro cao.
- Không merge nếu required checks fail hoặc branch protection bị tắt để đi nhanh.

### DevOps / Release Owner

- Sở hữu CI/CD, branch protection, secrets và release workflow.
- Cấu hình auto-merge, merge queue và required status checks.
- Cấu hình staging deployment từ `develop`.
- Cấu hình production build-test-deploy từ `main`.
- Theo dõi health check, smoke check, monitoring và rollback.
- Ghi deployment/release report.

DevOps không đồng nghĩa với "developer tự deploy từ máy cá nhân". Developer tập trung viết và kiểm thử code; DevOps/Release Owner sở hữu hệ thống triển khai.

## 2. Phân Công Theo Khu Vực

- `Anpham120`: Lead, Docs, DevOps, Testing, Integration, AI.
- `buidaoducanh1210`: Backend.
- `quanghieu1605`: Backend.
- `Tanh2k8-123`: Frontend.
- `totototototoads`: Frontend.

Nếu issue thay đổi người phụ trách hoặc phạm vi, ưu tiên thông tin mới nhất trong GitHub issue.

## 3. Vòng Đời Issue

1. Lead tạo hoặc cập nhật issue.
2. Issue ghi rõ mục tiêu, phạm vi file, điều không được chạm và tiêu chí hoàn thành.
3. Người phụ trách tạo branch issue từ `develop`.
4. Người phụ trách làm đúng scope.
5. Người phụ trách chạy build/test phù hợp.
6. Người phụ trách mở PR vào `develop`.
7. CI, required checks và ruleset tự kiểm tra PR.
8. Khi required checks đạt, PR vào merge queue.
9. Nếu merge queue pass, auto-merge hợp nhất vào `develop`.
10. Sau khi merge vào `develop`, staging deployment tự chạy nếu workflow đã cấu hình.
11. Issue chỉ được đóng khi có bằng chứng hoàn thành.

## 4. Release Và Production

Release production không đi thẳng từ issue branch.

Luồng đúng:

1. Các issue merge vào `develop`.
2. `develop` được kiểm tra trên staging.
3. Nếu staging health/smoke check đạt, workflow promote tạo hoặc cập nhật PR từ `develop` sang `main`.
4. Release PR phải pass required checks và merge queue.
5. Nếu queue pass, auto-merge hợp nhất vào `main`.
6. Sau khi code vào `main`, production build-test-deploy tự chạy.
7. Không có review/approval/deploy thủ công sau khi `main` nhận code.
8. DevOps kiểm tra health/smoke check và ghi báo cáo.

## 5. Báo Cáo Kết Quả Issue

Mỗi issue nên có báo cáo ngắn:

```text
## Báo cáo kết quả
- Issue:
- Branch:
- PR:
- Commit chính:
- Đã làm:
- File/chức năng đã thay đổi:
- Cách test:
- Bằng chứng build/test:
- Bằng chứng CI/CD nếu có:
- Có sửa ngoài scope không:
- Phần chưa làm / giới hạn:
```

## 6. Quy Tắc Khi Dùng AI Agent

AI agent chỉ là công cụ hỗ trợ người phụ trách issue. Người phụ trách vẫn chịu trách nhiệm cuối cùng về scope, test và báo cáo.

AI agent phải:

- Đọc issue và tài liệu liên quan trước khi sửa.
- Làm đúng phạm vi issue.
- Không tự ý sửa file ngoài scope.
- Không tự ý đổi API contract, enum, database schema hoặc shared type.
- Không commit secrets thật.
- Báo rõ test đã chạy và test chưa chạy.

AI agent không được:

- Tự nhận đã hoàn thành khi chưa có bằng chứng.
- Merge hoặc đóng issue khi chưa được yêu cầu.
- Revert thay đổi của người khác nếu chưa được phép.
- Tạo tài liệu mơ hồ chỉ để đủ hình thức.

## 7. Checklist Quality Gate

- [ ] PR đúng issue và đúng branch.
- [ ] Diff không vượt scope.
- [ ] Không có secrets thật.
- [ ] Frontend build pass nếu có sửa frontend.
- [ ] Backend restore/build/test pass nếu có sửa backend.
- [ ] CI pass hoặc có lý do rõ nếu CI chưa kích hoạt.
- [ ] Required checks và merge queue được cấu hình cho branch liên quan.
- [ ] Auto-merge không bỏ qua branch protection.
- [ ] DevOps evidence đầy đủ nếu PR liên quan deployment.
- [ ] Báo cáo issue/PR đủ thông tin.
- [ ] README không bị biến thành tài liệu nội bộ của team/agent.
