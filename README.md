# Restaurant QR AI Ordering

He thong dat do an va quan ly nha hang hybrid, ho tro khach quet QR tai ban, dat mon online, kitchen board realtime va chatbot AI tu van mon an.

## Project Goals

- Xay dung he thong dat mon hybrid: QR dine-in, pickup va delivery mock.
- Cho khach theo doi trang thai tung mon theo realtime.
- Cho nha hang cap nhat trang thai don/mon qua Staff va Kitchen board.
- Tich hop chatbot AI dung LLM API + RAG tren menu/FAQ.
- Trien khai production-like bang Docker/VPS, khong chi demo localhost.
- Quan ly tien do bang GitHub milestones, issues, PR va bao cao tung thanh vien.

## Tech Stack Du Kien

- Frontend: React + TypeScript
- Backend: ASP.NET Core Web API, mo duoc bang Visual Studio 2026
- Database: PostgreSQL + pgvector
- Realtime: ASP.NET Core SignalR
- AI: external LLM API + RAG dua tren menu/FAQ
- Deployment: Docker + VPS + Nginx + HTTPS

## Important Documents

- [Project Context](docs/PROJECT_CONTEXT.md)
- [Git Workflow](docs/GIT_WORKFLOW.md)
- [Team Workflow](docs/TEAM_WORKFLOW.md)
- [API Contract](docs/API_CONTRACT.md)
- [Weekly Report Template](docs/WEEKLY_REPORT_TEMPLATE.md)

Moi thanh vien va AI agent phai doc cac tai lieu tren truoc khi code.

## Branch Model

Du an dung 3 tang nhanh:

- `main`: ban on dinh de demo, nop bai va deploy production.
- `develop`: nhanh tich hop code cua ca nhom.
- `issue-<number>/<github-username>-<short-task>`: nhanh ca nhan cho tung issue.

Thanh vien khong push truc tiep vao `main` hoac `develop`. Moi thay doi phai di qua Pull Request vao `develop`.

## How To Contribute

1. Mo issue duoc giao va doc ky `Goal`, `Allowed files/areas`, `Do not touch`, `Acceptance criteria`.
2. Cap nhat code moi nhat tu `develop`.
3. Tao nhanh theo dung format: `issue-<number>/<github-username>-<short-task>`.
4. Lam dung pham vi issue, khong sua file/vung cua thanh vien khac neu chua duoc Lead dong y.
5. Commit theo Conventional Commits, vi du: `feat: add order placement api`.
6. Push nhanh ca nhan va tao Pull Request vao `develop`.
7. PR phai link issue bang `Closes #<issue_number>`.
8. Comment bao cao ket qua trong issue truoc khi yeu cau review.

## Team

- Pham Duy An / `Anpham120`: Lead, Docs, DevOps, Testing, Integration, AI
- Bui Dao Duc Anh / `buidaoducanh1210`: Backend
- Nguyen Quang Hieu / `quanghieu1605`: Backend
- Do Tuan Anh / `Tanh2k8-123`: Frontend
- Le Anh / `totototototoads`: Frontend
