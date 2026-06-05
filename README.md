# Restaurant QR AI Ordering

**Restaurant QR AI Ordering** là hệ thống đặt món và quản lý nhà hàng theo mô hình QR, tích hợp chatbot AI để tư vấn món ăn và hỗ trợ trải nghiệm khách hàng. Dự án hướng tới một quy trình vận hành gần thực tế: khách quét mã QR tại bàn, chọn món, theo dõi trạng thái đơn theo thời gian thực; nhân viên và bếp xử lý đơn qua màn hình vận hành; quản trị viên quản lý menu, bàn và đơn hàng.

## Tổng Quan

Trong nhiều nhà hàng, việc gọi món, ghi nhận đơn, chuyển thông tin xuống bếp và cập nhật trạng thái cho khách vẫn dễ bị chậm hoặc sai lệch. Dự án này giải quyết bài toán đó bằng một nền tảng thống nhất cho ba nhóm người dùng chính:

- Khách hàng đặt món trực tiếp trên điện thoại qua QR hoặc trang menu.
- Nhân viên và bếp tiếp nhận, chuẩn bị, cập nhật trạng thái món.
- Quản trị viên quản lý menu, bàn, đơn hàng và dữ liệu vận hành.

Chatbot AI được dùng như một lớp hỗ trợ tư vấn món ăn, gợi ý lựa chọn theo nhu cầu của khách và khai thác dữ liệu menu/FAQ của nhà hàng.

## Trải Nghiệm Chính

### Khách Hàng

- Quét QR tại bàn để mở menu theo đúng mã bàn.
- Xem danh sách món ăn, đồ uống, giá và trạng thái còn hàng.
- Thêm món vào giỏ hàng và xác nhận đặt món.
- Theo dõi trạng thái đơn và từng món theo thời gian thực.
- Hỏi chatbot AI để được tư vấn món theo khẩu vị, ngân sách hoặc số người.

### Nhân Viên Và Bếp

- Nhận đơn mới từ khách.
- Cập nhật trạng thái chuẩn bị món.
- Theo dõi các đơn đang chờ, đang làm, đã sẵn sàng hoặc đã phục vụ.
- Giảm sai sót khi chuyển thông tin giữa khu vực phục vụ và bếp.

### Quản Trị Viên

- Quản lý danh mục và món ăn.
- Bật/tắt trạng thái còn hàng của món.
- Quản lý bàn và mã QR.
- Theo dõi đơn hàng và tình trạng vận hành.

## Chức Năng Nổi Bật

- Đặt món tại bàn bằng QR.
- Menu điện tử cho món ăn và đồ uống.
- Giỏ hàng và xác nhận đơn.
- Theo dõi trạng thái đơn theo thời gian thực.
- Màn hình vận hành cho nhân viên, bếp và quản trị.
- Chatbot AI tư vấn món dựa trên menu/FAQ.
- Hướng triển khai production-like bằng Docker, VPS, Nginx và HTTPS.
- Quy trình DevOps có CI/CD, health check, rollback và báo cáo triển khai.

## Kiến Trúc Và Công Nghệ

| Lớp | Công nghệ |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| Backend | ASP.NET Core Web API |
| Realtime | ASP.NET Core SignalR |
| Database | PostgreSQL, pgvector nếu dùng RAG |
| AI | External LLM API kết hợp dữ liệu menu/FAQ |
| Deployment | Docker, Docker Compose, VPS, Nginx, HTTPS |
| CI/CD | GitHub Actions theo luồng `develop` và `main` |

## Luồng DevOps Dự Kiến

Dự án sử dụng định hướng DevOps Level 2.5 phù hợp phạm vi học thuật nhưng vẫn mô phỏng cách làm ngoài thực tế:

- Pull request vào `develop` phải chạy CI cho frontend và backend.
- Khi code được merge/push vào `develop`, hệ thống tự triển khai staging nếu kiểm tra đạt.
- Khi code được merge/push vào `main`, hệ thống tự chạy build, test và triển khai production nếu mọi kiểm tra đạt.
- Sau khi `main` nhận code, không có bước bấm deploy hoặc duyệt deploy thủ công.
- Health check, smoke check, monitoring cơ bản và rollback được ghi rõ trong tài liệu triển khai.

Chi tiết nằm tại:

- [Quy trình DevOps và release](docs/DEVOPS_RELEASE_PROCESS.md)
- [Tài liệu triển khai](docs/DEPLOYMENT.md)

## Cấu Trúc Dự Án

```text
.
├── backend/          # ASP.NET Core API, solution và test backend
├── frontend/         # React + TypeScript customer/admin/staff UI
├── docs/             # Tài liệu nghiệp vụ, API, DevOps và báo cáo
├── tools/            # Script kiểm tra hoặc hỗ trợ dự án
└── site-demo/        # Tài nguyên demo nếu có
```

## Tài Liệu

- [Ngữ cảnh dự án](docs/PROJECT_CONTEXT.md)
- [Hợp đồng API](docs/API_CONTRACT.md)
- [Quy trình DevOps và release](docs/DEVOPS_RELEASE_PROCESS.md)
- [Tài liệu triển khai](docs/DEPLOYMENT.md)
- [Quy trình Git](docs/GIT_WORKFLOW.md)
- [Quy trình làm việc nhóm](docs/TEAM_WORKFLOW.md)
- [Mẫu báo cáo tuần](docs/WEEKLY_REPORT_TEMPLATE.md)

## Trạng Thái Dự Án

Dự án đang được phát triển theo từng issue và milestone. Mục tiêu cuối là có một bản demo nhà hàng CMC Restaurant đủ rõ để trình bày luồng QR ordering, quản lý menu/đơn hàng, vận hành bếp/nhân viên, chatbot AI và quy trình triển khai tự động.
