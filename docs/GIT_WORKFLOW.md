# Quy Trình Git

Tài liệu này quy định luồng Git chuẩn cho dự án **Restaurant QR AI Ordering**. Mục tiêu là giúp thầy, Lead, thành viên và AI agent của từng thành viên nhìn rõ: ai đang làm issue nào, code nằm ở nhánh nào, Pull Request nào, kết quả đã báo cáo chưa.

## 1. Mô Hình Nhánh

Dự án dùng ba tầng nhánh:

- `main`: nhánh ổn định để demo, nộp bài và deploy production.
- `develop`: nhánh tích hợp code của cả nhóm.
- `issue-<number>/<github-username>-<short-task>`: nhánh cá nhân cho từng issue.

Không push trực tiếp vào `main` hoặc `develop`. Mọi thay đổi phải đi qua Pull Request.

## 2. Vai Trò Của Từng Nhánh

### `main`

- Chỉ chứa code đã ổn định.
- Dùng cho demo chính thức, deploy VPS và nộp báo cáo.
- Chỉ nhận code từ PR `develop` -> `main`.
- Lead `Anpham120` là người review và merge cuối cùng.

### `develop`

- Là nhánh tích hợp tiến độ hằng ngày của nhóm.
- Tất cả issue branches merge vào `develop`.
- Dùng để test tích hợp frontend, backend, AI và realtime.

### Issue Branch

- Tạo từ `develop`, không tạo từ `main`.
- Mỗi issue có một branch riêng.
- Format bắt buộc:

```bash
issue-<number>/<github-username>-<short-task>
```

Ví dụ:

```bash
issue-3/quanghieu1605-efcore-menu-order
issue-7/tanh2k8-customer-cart
issue-11/anpham120-rag-menu-faq
```

## 3. Luồng Làm Việc Chuẩn Cho Thành Viên

Bắt đầu issue:

```bash
git checkout develop
git pull origin develop
git checkout -b issue-<number>/<github-username>-<short-task>
```

Trong khi làm:

- Chỉ sửa file/vùng được ghi trong `Allowed files / areas`.
- Không sửa file/vùng ghi trong `Do not touch`.
- Nếu cần sửa API contract, shared model, config chung hoặc file của người khác, phải comment hỏi Lead trong issue trước.

Hoàn thành issue:

```bash
git status
git add <changed-files>
git commit -m "feat: short description"
git push origin issue-<number>/<github-username>-<short-task>
```

Sau đó tạo Pull Request:

- Base branch: `develop`
- Compare branch: branch issue của mình
- PR description phải có `Closes #<issue_number>`
- Điền đầy đủ checklist trong PR template
- Comment báo cáo kết quả vào issue

## 4. Luồng Merge

### Issue Branch -> `develop`

Dùng cho mọi task hằng ngày.

Điều kiện merge:

- PR đúng base branch `develop`.
- PR link issue bằng `Closes #<issue_number>`.
- Không sửa ngoài phạm vi issue.
- Đã chạy test/build phù hợp.
- Đã comment báo cáo kết quả trong issue.
- Lead hoặc người được Lead chỉ định đã review.

### `develop` -> `main`

Chỉ thực hiện cuối tuần hoặc khi cần demo.

Điều kiện merge:

- Các issue trong milestone tuần đã được tổng hợp.
- Không còn lỗi nghiêm trọng.
- Đã chạy test/build/integration.
- Đã có báo cáo tuần.
- Lead `Anpham120` merge cuối cùng.

## 5. Conventional Commits

Dùng commit message rõ nghĩa:

```bash
feat: add customer order placement api
fix: correct unavailable menu item validation
docs: add week 1 report template
test: add order service integration tests
refactor: simplify menu query service
chore: update docker compose config
```

Không dùng commit mơ hồ:

```bash
update
fix bug
done
new code
```

## 6. Quy Tắc Xử Lý Conflict

- Không tự ý resolve conflict ở file ngoài phạm vi issue.
- Nếu conflict liên quan file của người khác, comment vào issue/PR và tag Lead.
- Trước khi mở PR, nên cập nhật branch từ `develop`:

```bash
git checkout develop
git pull origin develop
git checkout issue-<number>/<github-username>-<short-task>
git merge develop
```

Nếu merge conflict quá lớn, dừng lại và báo Lead, không sửa đoạn code không hiểu.

## 7. Quy Tắc Cho AI Agent

Khi mỗi thành viên dùng AI agent riêng, phải đưa agent đọc các tài liệu sau trước khi code:

- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/GIT_WORKFLOW.md`
- issue được giao
- PR/issue liên quan nếu có

AI agent chỉ được:

- Làm đúng mục tiêu issue.
- Sửa đúng vùng `Allowed files / areas`.
- Báo cáo nếu cần sửa file ngoài phạm vi.

AI agent không được:

- Push trực tiếp vào `main` hoặc `develop`.
- Tự ý sửa API contract/shared model.
- Tự ý xóa hoặc refactor code của thành viên khác.
- Tự ý thay đổi scope issue.

## 8. Báo Cáo Kết Quả Trong Issue

Trước khi yêu cầu review PR, thành viên comment vào issue theo mẫu:

```text
## Báo cáo kết quả
- Đã làm:
- File/chức năng đã thay đổi:
- Cách test:
- Ảnh/video demo nếu có:
- Vấn đề còn tồn tại:
- PR liên quan:
```

## 9. Checklist Nhanh

Trước khi mở PR:

- [ ] Branch tạo từ `develop`.
- [ ] Branch đúng format `issue-<number>/<github-username>-<short-task>`.
- [ ] PR merge vào `develop`, không merge vào `main`.
- [ ] PR có `Closes #<issue_number>`.
- [ ] Không sửa file ngoài phạm vi issue.
- [ ] Đã chạy test/build phù hợp.
- [ ] Đã comment báo cáo kết quả trong issue.
