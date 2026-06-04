# Quy Trình Làm Việc Nhóm

## 1. Phân Công Trách Nhiệm

- `Anpham120`: Lead, Docs, DevOps, Testing, Integration, AI.
- `buidaoducanh1210`: Backend.
- `quanghieu1605`: Backend.
- `Tanh2k8-123`: Frontend.
- `totototototoads`: Frontend.

Mỗi tuần mỗi thành viên có một issue chính. Mỗi issue phải có một branch, một Pull Request và một báo cáo kết quả.

## 2. Quy Tắc Dùng AI Agent

Mỗi thành viên có thể dùng AI agent riêng, nhưng agent phải đọc:

- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/GIT_WORKFLOW.md`
- `docs/TEAM_WORKFLOW.md`
- `docs/API_CONTRACT.md`
- Issue được giao

AI agent được phép:

- Làm đúng mục tiêu issue.
- Sửa đúng vùng `Allowed Files / Areas`.
- Tạo test và tài liệu trong phạm vi issue.
- Báo cáo nếu cần đổi contract hoặc scope.

AI agent không được phép:

- Push trực tiếp vào `main` hoặc `develop`.
- Sửa ngoài `Allowed Files / Areas`.
- Sửa vùng `Do Not Touch`.
- Đổi API contract, status name, route, entity chung mà không hỏi Lead.
- Xóa hoặc refactor code của thành viên khác.
- Tự ý thêm feature mới ngoài issue.

## 3. Chuẩn Issue

Mỗi issue phải có:

- Assignee.
- Milestone.
- Required branch.
- Goal.
- Context.
- Scope of work.
- Step-by-step tasks.
- Allowed files/areas.
- Do not touch.
- Acceptance criteria.
- Required test/verification.
- Evidence required.
- AI reviewer notes.

Thầy hoặc AI reviewer có thể dùng các mục trên để so sánh issue, commit và Pull Request.

## 4. Chuẩn Pull Request

Mỗi Pull Request phải:

- Target vào `develop`.
- Link issue bằng `Closes #<issue_number>`.
- Có commit message rõ ràng.
- Có bằng chứng test/build.
- Không sửa ngoài scope.
- Có comment báo cáo kết quả trong issue trước khi review.

Lead review trước khi merge. Nếu PR vượt scope, Lead có quyền yêu cầu tách PR hoặc rollback phần vượt scope.

## 5. Chuẩn Báo Cáo

Khi hoàn thành issue, thành viên comment vào issue:

```text
## Báo cáo kết quả
- Issue:
- Branch:
- PR:
- Commit chính:
- Đã làm:
- File/chức năng đã thay đổi:
- Cách test:
- Bằng chứng:
- Phần chưa làm / giới hạn:
- Có sửa ngoài scope không:
```

Cuối mỗi tuần Lead tổng hợp vào `docs/reports/week-N-report.md`.

## 6. Quy Tắc Đổi Contract

Nếu cần đổi một trong các mục sau, phải comment hỏi Lead:

- API endpoint.
- Request/response DTO.
- Enum/status name.
- Route frontend.
- Shared type.
- Database field dùng chung.
- SignalR event payload.

Không được tự ý đổi contract chỉ để làm UI hoặc backend nhanh hơn.
