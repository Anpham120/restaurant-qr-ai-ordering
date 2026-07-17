# CMC Restaurant Documentation

Đây là điểm vào thống nhất cho tài liệu sản phẩm, kiến trúc, AI/RAG, kiểm thử và vận hành của CMC Restaurant — QR AI Ordering.

> Bắt đầu nhanh: đọc [Project Context](PROJECT_CONTEXT.md), [System Analysis & Design](SYSTEM_ANALYSIS_DESIGN.md), [API Contract](API_CONTRACT.md) và [Deployment](DEPLOYMENT.md).

## Start Here

- [Project Context](PROJECT_CONTEXT.md) — mục tiêu, phạm vi và bối cảnh hiện tại của dự án.
- [System Analysis & Design](SYSTEM_ANALYSIS_DESIGN.md) — phân tích tác nhân, use case và thiết kế hệ thống tổng thể.
- [API Contract](API_CONTRACT.md) — hợp đồng endpoint giữa frontend và backend.
- [Test Plan](TEST_PLAN.md) — chiến lược và phạm vi kiểm thử chính.
- [Deployment](DEPLOYMENT.md) — cách cấu hình và triển khai hệ thống.

## Product & System Design

- [BA/SA System Design](BA_SA_SYSTEM_DESIGN.md) — góc nhìn business/system analysis và kiến trúc nghiệp vụ.
- [Smart Table QR Plan](SMART_TABLE_QR_PLAN.md) — thiết kế table session và hành trình gọi món bằng QR.
- [Restaurant UI Feature Benchmark](RESTAURANT_UI_FEATURE_BENCHMARK.md) — đối chiếu tính năng và trải nghiệm UI nhà hàng.
- [Admin UI Redesign Blueprint](ADMIN_UI_REDESIGN_BLUEPRINT.md) — định hướng giao diện quản trị.

## API & Architecture

- [Backend Modular Monolith Architecture](BACKEND_MODULAR_MONOLITH_ARCHITECTURE.md) — ranh giới module và nguyên tắc kiến trúc backend.
- [Backend Database Setup](BACKEND_DATABASE_SETUP.md) — PostgreSQL, connection string và migration.
- [API Contract](API_CONTRACT.md) — endpoint, payload và quy ước tích hợp.
- [Smart Table QR Plan](SMART_TABLE_QR_PLAN.md) — vòng đời token/session liên quan đến API table ordering.

## AI & RAG

- [AI Chatbot](AI_CHATBOT.md) — vai trò, luồng request và cách chạy AI service.
- [AI/RAG Architecture](AI_RAG_ARCHITECTURE.md) — retriever, grounding, guardrails và luồng gọi LLM.
- [AI Knowledge Base Guide](AI_KNOWLEDGE_BASE_GUIDE.md) — cách tổ chức và bảo trì knowledge base.
- [AI/RAG Quality Protocol](AI_RAG_QUALITY_PROTOCOL.md) — quy tắc đánh giá chất lượng và chống hallucination.
- [AI Evaluation Plan](AI_EVALUATION_PLAN.md) — mục tiêu, dataset và phương pháp evaluation.
- [AI Evaluation Runbook](AI_EVALUATION_RUNBOOK.md) — lệnh và quy trình chạy evaluation tái lập.
- [AI/RAG Research Design](AI_RAG_RESEARCH_DESIGN.md) — thiết kế nghiên cứu retrieval và thí nghiệm.
- [AI Retrieval Development Results](AI_RETRIEVAL_DEV_RESULTS.md) — kết quả benchmark trong quá trình phát triển.
- [Retriever Selection ADR](ai/ADR_RETRIEVER_SELECTION.md) — quyết định lựa chọn chiến lược retriever.
- [AI Production Operations](ai/AI_PRODUCTION_OPERATIONS.md) — vận hành AI service trong production.

## Testing & Quality

- [Test Plan](TEST_PLAN.md) — test pyramid, các luồng quan trọng và điều kiện hoàn thành.
- [E2E Multi-device Checklist](E2E_MULTI_DEVICE_CHECKLIST.md) — kiểm tra customer/staff/kitchen/admin trên nhiều thiết bị.
- [Smoke Test Evidence](SMOKE_TEST_EVIDENCE.md) — bằng chứng smoke test được ghi nhận.
- [Issue #20 Evidence](reports/issue-20/evidence.md) — ảnh và bằng chứng giao diện cho các workspace vận hành.
- [Repository Hygiene](REPO_HYGIENE.md) — nguyên tắc giữ repository sạch và dễ kiểm chứng.

## DevOps & Operations

- [CI/CD Pipeline](CICD_PIPELINE.md) — cấu trúc workflow CI, staging và production.
- [Deployment](DEPLOYMENT.md) — quy trình triển khai và cấu hình môi trường.
- [DevOps Release Process](DEVOPS_RELEASE_PROCESS.md) — promotion, release và rollback.
- [Production Operations](PRODUCTION_OPERATIONS.md) — health checks, vận hành và xử lý sự cố.
- [Branch Ruleset](BRANCH_RULESET.md) — quy tắc bảo vệ nhánh và merge.
- [Git Workflow](GIT_WORKFLOW.md) — branch, commit và pull request flow.

## Team Process

- [Team Workflow](TEAM_WORKFLOW.md) — phân công và nhịp làm việc của nhóm.
- [Weekly Report Template](WEEKLY_REPORT_TEMPLATE.md) — mẫu báo cáo tiến độ tuần.
- [Contributing Guide](../CONTRIBUTING.md) — hướng dẫn đóng góp vào repository.
- [Security Policy](../SECURITY.md) — báo cáo lỗ hổng và nguyên tắc bảo mật.

## Reports & Presentation

- [Presentation Script](presentation/kich-ban-thuyet-trinh.md) — kịch bản thuyết trình dự án.
- [CMC RAG Chatbot Defense Deck](presentation/CMC_RAG_Chatbot_Defense.pptx) — slide bảo vệ phần AI/RAG.
- [Issue #20 UI Evidence](reports/issue-20/evidence.md) — báo cáo và gallery giao diện đã kiểm chứng.

## Historical Plans and Implementation Notes

Các tệp dưới đây ghi lại ý định hoặc quá trình triển khai tại một thời điểm. Chúng hữu ích để hiểu quyết định, nhưng không mặc định mô tả trạng thái hiện tại.

- [AI LLM/RAG Refactor Plan](AI_LLM_RAG_REFACTOR_PLAN.md) — kế hoạch cải tổ AI/RAG.
- [Ordering Session & Invoice Refactor Plan](ORDERING_SESSION_INVOICE_REFACTOR_PLAN.md) — kế hoạch thay đổi session/invoice.
- [Table Ordering App Refactor Plan](TABLE_ORDERING_APP_REFACTOR_PLAN.md) — kế hoạch tái cấu trúc ordering app.
- [Repository Refactor Plan](REFACTOR_PLAN.md) — kế hoạch refactor tổng quát.
- [Remediation Plan](REMEDIATION_PLAN.md) — các hạng mục khắc phục được xác định.
- [Table QR Order Flow Design](superpowers/specs/2026-07-10-table-qr-order-flow-design.md) — design spec cho luồng QR ordering.
- [GitHub README Redesign](superpowers/specs/2026-07-17-github-readme-redesign.md) — design spec cho trang trình bày GitHub.
- [Professional GitHub README Plan](superpowers/plans/2026-07-17-github-readme-redesign.md) — kế hoạch triển khai README hiện tại.

## Quy ước bảo trì tài liệu

- `README.md` mô tả hành vi và trạng thái hiện tại.
- ADR ghi lại quyết định kiến trúc cùng bối cảnh và đánh đổi.
- Plan/spec mô tả thay đổi dự kiến; sau khi triển khai có thể trở thành tài liệu lịch sử.
- Evidence report phải ghi rõ issue, phạm vi hoặc thời điểm kiểm chứng.
- Không đưa secret, mật khẩu, token hoặc dữ liệu khách hàng vào tài liệu.
- Tài liệu mới cần được liên kết từ tệp này để người đọc có thể tìm thấy.
