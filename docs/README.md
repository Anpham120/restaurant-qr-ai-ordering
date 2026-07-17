# Documentation Hub

Điểm vào cho tài liệu **đang được duy trì** của CMC Restaurant QR AI Ordering.

> Thứ tự tin cậy: code và test hiện tại → `SPEC.md` → tài liệu kiến trúc/API → kế hoạch hoặc báo cáo lịch sử.

## Bắt đầu từ đây

| Nhu cầu | Tài liệu |
| --- | --- |
| Hiểu bài toán và thiết kế tổng thể | [BA/SA System Design](BA_SA_SYSTEM_DESIGN.md) |
| Kiểm tra invariant và công việc đã chốt | [Project SPEC](../SPEC.md) |
| Tích hợp với backend | [API Contract](API_CONTRACT.md) |
| Hiểu cấu trúc backend | [Backend Modular Monolith Architecture](BACKEND_MODULAR_MONOLITH_ARCHITECTURE.md) |
| Chạy và triển khai hệ thống | [Deployment](DEPLOYMENT.md) |
| Vận hành production | [Production Operations](PRODUCTION_OPERATIONS.md) |

## AI, RAG và đánh giá

- [AI/RAG Architecture](AI_RAG_ARCHITECTURE.md) — luồng xử lý, grounding và ranh giới giữa backend với AI service.
- [AI Evaluation Runbook](AI_EVALUATION_RUNBOOK.md) — cách chạy và đọc bộ đánh giá.
- [AI RAG Quality Protocol](AI_RAG_QUALITY_PROTOCOL.md) — tiêu chí chất lượng và kiểm soát hồi quy.
- [Knowledge Base Guide](AI_KNOWLEDGE_BASE_GUIDE.md) — quy ước cho nguồn tri thức.
- [Retriever Selection ADR](ai/ADR_RETRIEVER_SELECTION.md) — quyết định kỹ thuật cho retrieval.
- [AI Production Operations](ai/AI_PRODUCTION_OPERATIONS.md) — cấu hình và xử lý sự cố AI trên production.

## Kiểm thử và phát hành

- [E2E Multi-device Checklist](E2E_MULTI_DEVICE_CHECKLIST.md) — xác minh luồng bàn, phiên gọi món và nhiều thiết bị.
- [CI/CD Pipeline](CICD_PIPELINE.md) — pipeline kiểm tra và triển khai.
- [DevOps Release Process](DEVOPS_RELEASE_PROCESS.md) — quy trình phát hành.
- [Backend Database Setup](BACKEND_DATABASE_SETUP.md) — chuẩn bị PostgreSQL cho backend.

## Quy tắc cập nhật

- Ảnh được quảng bá trong `README.md` phải chụp từ production hiện tại, ghi ngày chụp và được kiểm tra trực quan trước khi commit.
- Khi giao diện hoặc luồng chính thay đổi, cập nhật ảnh và phần mô tả liên quan trong cùng thay đổi tài liệu.
- Kế hoạch refactor, báo cáo issue và bằng chứng theo mốc thời gian là tài liệu truy vết; không đưa vào danh sách “hiện hành” nếu chưa đối chiếu lại với code.
- Nếu tài liệu mâu thuẫn với code/test hiện tại, code/test là nguồn đúng và tài liệu phải được sửa.

## Tài liệu lịch sử

Các kế hoạch, báo cáo issue và bằng chứng cũ vẫn được giữ trong `docs/` để truy vết quyết định. Chúng không được liệt kê ở hub này như mô tả của phiên bản hiện tại.
