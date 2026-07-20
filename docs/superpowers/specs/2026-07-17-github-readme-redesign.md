# GitHub README Redesign

## Mục tiêu

Nâng cấp trang GitHub của CMC Restaurant thành một hồ sơ sản phẩm chuyên nghiệp, dễ hiểu trong 60 giây đầu nhưng vẫn đủ chiều sâu cho developer bắt đầu chạy và đánh giá hệ thống.

README sử dụng cách kể chuyện product-first tương tự `k4spi4n/runny-ai`: giới thiệu giá trị trước, chứng minh bằng giao diện thật, sau đó mới trình bày kiến trúc, bảo mật, cách chạy và tài liệu kỹ thuật.

## Đối tượng

- Nhà tuyển dụng, giảng viên và khách hàng cần hiểu nhanh bài toán, giải pháp và mức độ hoàn thiện.
- Developer cần xác định cấu trúc hệ thống, công nghệ, lệnh chạy và tài liệu chuyên sâu.
- Thành viên dự án cần một điểm vào thống nhất thay vì tìm giữa nhiều tệp trong `docs/`.

## Nguyên tắc

- Chỉ công bố tính năng, URL, workflow và trạng thái đã có bằng chứng trong repository.
- Không sử dụng badge trang trí hoặc số liệu không thể kiểm chứng.
- Không đưa secret, tài khoản demo nhạy cảm hoặc chi tiết vận hành riêng tư vào README.
- Nội dung chính viết bằng tiếng Việt, giữ tên công nghệ và lệnh bằng tiếng Anh.
- README là trang giới thiệu và điều hướng; chi tiết dài nằm trong `docs/`.
- Thay đổi này chỉ tác động tài liệu và asset trình bày, không thay đổi runtime code.

## Cấu trúc README

1. **Hero**
   - Logo thật của dự án.
   - Tên “CMC Restaurant — QR AI Ordering”.
   - Một câu mô tả giá trị.
   - Liên kết demo, kiến trúc, API và hướng dẫn chạy.
   - Badge CI/security/deployment chỉ lấy từ GitHub Actions đang tồn tại.
2. **Giá trị sản phẩm**
   - Mô tả ngắn bài toán phục vụ nhà hàng.
   - Bảng “Khả năng → Giá trị nhận được”.
3. **Trải nghiệm theo vai trò**
   - Customer, ordering, staff, kitchen và admin.
   - Nêu luồng xuyên suốt từ quét QR đến hoàn tất đơn.
4. **Giao diện**
   - Gallery dùng ảnh thật trong `docs/reports/issue-20/`.
   - Ưu tiên ảnh desktop rõ nội dung; ảnh mobile dùng khi bổ sung góc nhìn.
5. **Kiến trúc**
   - Mermaid thể hiện React applications, ASP.NET Core API, SignalR, PostgreSQL và FastAPI/RAG.
   - Nêu ranh giới trách nhiệm, không mô tả hệ thống như các microservice chưa tồn tại.
6. **AI, bảo mật và độ tin cậy**
   - Grounded menu/knowledge-base answers, guardrails và evaluation.
   - JWT/roles, QR table session, secrets phía server, health checks và rollback.
7. **Bắt đầu phát triển**
   - Điều kiện tiên quyết.
   - Quick start cho frontend, backend và AI.
   - Lệnh build/test chính xác lấy từ repository.
8. **Cấu trúc repository**
   - Liệt kê `frontend/`, `backend/`, `ai/`, `deploy/`, `docs/`.
9. **Tài liệu**
   - Gom liên kết theo Product & System Design, API & Architecture, AI/RAG, Testing và Operations.
10. **Trạng thái, roadmap và license**
    - Mô tả trung thực giai đoạn hiện tại.
    - Roadmap ngắn, không cam kết ngày.
    - Giấy phép lấy từ `LICENSE`.

## Asset trình bày

- Logo nguồn: asset logo đang được customer web sử dụng; sao chép một bản ổn định vào `docs/assets/` nếu hiện tại chỉ nằm trong thư mục build.
- Gallery nguồn:
  - `docs/reports/issue-20/admin-dashboard.png`
  - `docs/reports/issue-20/admin-menu.png`
  - `docs/reports/issue-20/kitchen-board.png`
  - `docs/reports/issue-20/staff-orders.png`
  - Các ảnh mobile tương ứng khi bố cục không bị quá dài.
- Không tham chiếu asset có tên hash trong `dist/` trực tiếp từ README.
- Không tạo hình AI giả lập giao diện; chỉ dùng ảnh chụp sản phẩm thật.

## Tài liệu bổ sung

- Tạo `docs/README.md` làm mục lục tài liệu có phân nhóm.
- Giữ nguyên tài liệu chuyên sâu hiện có; chỉ sửa tên liên kết hoặc mô tả khi cần để điều hướng chính xác.
- Không di chuyển hoặc đổi tên hàng loạt vì có thể làm hỏng liên kết ngoài và lịch sử issue.

## Kiểm chứng

- Mọi đường dẫn Markdown và đường dẫn ảnh trong README phải tồn tại.
- URL demo phải khớp cấu hình production hiện có.
- Mermaid phải dùng cú pháp GitHub hỗ trợ.
- Lệnh quick start phải khớp `frontend/package.json`, solution backend và `ai/requirements.txt`.
- Badge workflow phải trỏ đúng tên tệp trong `.github/workflows/`.
- Rà soát README ở dạng raw để phát hiện lỗi encoding tiếng Việt.
- Kiểm tra `git diff --check` để phát hiện whitespace hoặc marker lỗi.

## Ngoài phạm vi

- Thay đổi tính năng ứng dụng, API, database hoặc AI/RAG.
- Chụp lại giao diện production bằng tài khoản hoặc dữ liệu nhạy cảm.
- Thiết kế lại thương hiệu đầy đủ.
- Thay đổi workflow CI/CD chỉ để tạo badge đẹp hơn.
# Freshness addendum

- Product screenshots must come from the currently deployed applications, include the capture date in their filename or surrounding copy, and pass visual inspection before commit.
- Issue evidence and historical plans may remain in the repository for traceability, but must not be presented as current product state without revalidation against the live application and current code.
- The documentation hub promotes only maintained entry points; historical material is explicitly separated.
