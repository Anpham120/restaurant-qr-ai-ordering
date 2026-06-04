# Restaurant QR AI Ordering

**Restaurant QR AI Ordering** là hệ thống đặt món và quản lý nhà hàng tích hợp chatbot AI. Dự án hướng tới một quy trình vận hành thực tế: khách quét mã QR tại bàn để đặt món, nhà hàng tiếp nhận và xử lý đơn, bếp cập nhật trạng thái từng món theo thời gian thực, khách theo dõi tiến độ món ăn, và chatbot AI hỗ trợ tư vấn món dựa trên menu/FAQ của nhà hàng.

## Mục Tiêu Dự Án

- Xây dựng hệ thống đặt món hybrid gồm QR tại bàn, pickup và delivery mock.
- Cho phép khách hàng theo dõi trạng thái từng món theo thời gian thực.
- Cho phép nhân viên và bếp cập nhật trạng thái đơn/món qua màn hình vận hành.
- Tích hợp chatbot AI sử dụng API mô hình ngôn ngữ lớn kết hợp RAG trên dữ liệu menu/FAQ.
- Triển khai theo hướng production-like bằng Docker, VPS, Nginx và HTTPS.
- Quản lý tiến độ bằng GitHub milestones, issues, pull requests, commits và báo cáo kết quả từng thành viên.

## Công Nghệ Dự Kiến

- Frontend: React + TypeScript
- Backend: ASP.NET Core Web API, mở và chạy được bằng Visual Studio 2026
- Database: PostgreSQL + pgvector
- Realtime: ASP.NET Core SignalR
- AI: API mô hình ngôn ngữ lớn + RAG dựa trên menu/FAQ
- Deployment: Docker + VPS + Nginx + HTTPS

## Tài Liệu Quan Trọng

- [Ngữ cảnh dự án](docs/PROJECT_CONTEXT.md)
- [Quy trình Git](docs/GIT_WORKFLOW.md)
- [Quy trình làm việc nhóm](docs/TEAM_WORKFLOW.md)
- [Hợp đồng API](docs/API_CONTRACT.md)
- [Mẫu báo cáo tuần](docs/WEEKLY_REPORT_TEMPLATE.md)

Mọi thành viên và AI agent hỗ trợ lập trình phải đọc các tài liệu trên trước khi bắt đầu làm issue.

## Mô Hình Nhánh

Dự án sử dụng ba tầng nhánh:

- `main`: nhánh ổn định dùng để demo, nộp bài và triển khai production.
- `develop`: nhánh tích hợp code của cả nhóm.
- `issue-<number>/<github-username>-<short-task>`: nhánh cá nhân cho từng issue.

Không thành viên nào được push trực tiếp lên `main` hoặc `develop`. Mọi thay đổi phải đi qua Pull Request vào `develop`.

## Cách Đóng Góp

1. Mở issue được giao và đọc kỹ `Goal`, `Allowed files / areas`, `Do not touch`, `Acceptance criteria`.
2. Cập nhật code mới nhất từ `develop`.
3. Tạo nhánh đúng format: `issue-<number>/<github-username>-<short-task>`.
4. Chỉ làm đúng phạm vi issue, không sửa file hoặc vùng của thành viên khác nếu chưa được Lead đồng ý.
5. Commit theo Conventional Commits, ví dụ: `feat: add order placement api`.
6. Push nhánh cá nhân lên GitHub.
7. Tạo Pull Request vào `develop`.
8. PR phải link issue bằng `Closes #<issue_number>`.
9. Comment báo cáo kết quả trong issue trước khi yêu cầu review.

## Thành Viên

- Phạm Duy An / `Anpham120`: Lead, Docs, DevOps, Testing, Integration, AI
- Bùi Đào Đức Anh / `buidaoducanh1210`: Backend
- Nguyễn Quang Hiếu / `quanghieu1605`: Backend
- Đỗ Tuấn Anh / `Tanh2k8-123`: Frontend
- Lê Anh / `totototototoads`: Frontend

## Nguyên Tắc Làm Việc Với AI Agent

- AI agent chỉ được làm đúng phạm vi issue.
- AI agent không được tự ý đổi API contract, route, enum trạng thái, shared type hoặc database field dùng chung.
- Nếu cần sửa ngoài phạm vi issue, thành viên phải comment hỏi Lead trước.
- Mỗi issue phải có branch, commit, PR và báo cáo kết quả rõ ràng để thầy hoặc AI reviewer đánh giá đóng góp.

## Trạng Thái Hiện Tại

Dự án đang ở giai đoạn nền tảng: thiết lập tài liệu quản trị, quy trình Git, hợp đồng API, milestones và issues cho 4 tuần phát triển.
