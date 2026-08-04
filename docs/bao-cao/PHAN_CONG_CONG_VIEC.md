# Phân công công việc — giai đoạn hoàn thiện và bảo vệ

**Học phần:** Công nghệ phần mềm — INFO2005
**Repository:** <https://github.com/Anpham120/restaurant-qr-ai-ordering>
**Ngày lập:** 02/08/2026

---

## 1. Thành viên và mảng phụ trách

| # | Họ và tên | MSSV | GitHub | Mảng | Đã làm (đối chiếu GitHub) |
|---|---|---|---|---|---|
| 1 | **Phạm Duy An** | BIT240002 | [@Anpham120](https://github.com/Anpham120) | **Nhóm trưởng** · Thiết kế hệ thống · AI/RAG · DevOps | 16 issue · 270 PR · 392 commit |
| 2 | **Bùi Đào Đức Anh** | BIT240025 | [@buidaoducanh1210](https://github.com/buidaoducanh1210) | Backend — xác thực, phiên bàn, thanh toán | 8 issue · 9 PR · 22 commit |
| 3 | **Nguyễn Quang Hiếu** | BIT240091 | [@quanghieu1605](https://github.com/quanghieu1605) | Backend — CSDL, đơn hàng, realtime | 8 issue · 9 PR · 25 commit |
| 4 | **Đỗ Tuấn Anh** | BIT240015 | [@Tanh2k8-123](https://github.com/Tanh2k8-123) | Frontend — trải nghiệm khách hàng | 7 issue · 5 PR · 9 commit |
| 5 | **Lê Anh** | BIT240017 | [@totototototoads](https://github.com/totototototoads) | Frontend — giao diện vận hành | 7 issue · 8 PR · 9 commit |

## 2. Nguyên tắc chia việc lần này

Sản phẩm đã chạy production, nên phần việc còn lại **không phải viết thêm tính năng** mà là:

1. **Bù ba khoảng trống rubric bắt buộc** — ảnh chụp repo, ảnh màn hình AI/bếp/quầy, và bật branch ruleset.
2. **Xử lý 8 hạn chế đã ghi thẳng** ở §5.3 báo cáo — ưu tiên những cái ảnh hưởng tới điểm bảo vệ.
3. **Chuẩn bị vấn đáp** — mỗi người phải giải thích được **quyết định kỹ thuật** của mảng mình, không chỉ mô tả code đã viết.

Ba ràng buộc khi chia:

- **Không ai làm việc ngoài mảng của mình**, để phần trả lời vấn đáp trùng với phần đã làm thật.
- **Mỗi đầu việc mở một issue**, gán người, gắn milestone `Tuần 6 — Hoàn thiện và bảo vệ`, và đóng bằng một PR — giữ đúng quy trình đã dùng suốt 5 tuần.
- **Mỗi đầu việc có tiêu chí hoàn thành đo được**, không nhận việc kiểu "cải thiện giao diện".

> **Cân bằng đóng góp.** Hai bạn frontend hiện có 9 commit mỗi người — thấp nhất nhóm. Phần
> việc dưới đây cố ý dồn nhiều đầu việc **có thể chứng minh trên GitHub** cho Tuấn Anh và Lê Anh,
> vì rubric chấm *"đóng góp cá nhân đối chiếu được trên GitHub"* và đây là chỗ nhóm mỏng nhất.

---

## 3. Bảng phân công chi tiết

### Ưu tiên 1 — bắt buộc trước khi nộp (hạn: 05/08/2026)

Bốn việc đã hoàn thành trong đợt rà soát ngày 02/08/2026, ghi lại để không làm trùng:

| Mã | Đầu việc | Trạng thái | Kết quả |
|---|---|---|---|
| P1-1 | Ảnh chụp màn hình repository | **Xong** | 5 ảnh trong `docs/assets/report/` — milestones, issues, commit-activity, pull requests, releases. Đã chèn thành Hình 3.1–3.6 |
| P1-7 | Chạy `dotnet test` lấy số thật | **Xong** | **84/84 test đạt**, 0 lỗi. Đã điền vào §5.2.1 báo cáo |
| P1-9 | Tạo thêm bản phát hành | **Xong** | [v0.2.0](https://github.com/Anpham120/restaurant-qr-ai-ordering/releases/tag/v0.2.0) và [v0.3.0](https://github.com/Anpham120/restaurant-qr-ai-ordering/releases/tag/v0.3.0), mỗi bản có ghi chú đầy đủ và số liệu riêng |
| P1-10 | Sửa lỗi console cp1252 làm đường lỗi thành HTTP 500 | **Xong** | `_in_log` + cấu hình lại stdout, kèm 2 test hai chiều. Toàn bộ 388 test AI đạt mà không cần biến môi trường phụ |

Còn lại phải làm:

| Mã | Đầu việc | Người làm | Tiêu chí hoàn thành | Ghi chú |
|---|---|---|---|---|
| **P1-2** | Chụp màn hình **trợ lý AI** đang trả lời trên production | **Phạm Duy An** | 2 ảnh: một câu hỏi thường, một câu có ràng buộc dị ứng cho thấy món bị loại. Lưu `docs/assets/report/ai-chat-*.png` | Cần mở phiên bàn thật nên không chụp tự động được. Đây là điểm khác biệt lớn nhất của sản phẩm |
| **P1-3** | Chụp màn hình **bảng bếp** đang hoạt động | **Lê Anh** | 1 ảnh bảng bếp có đơn thật ở nhiều trạng thái, lưu `docs/assets/report/kitchen-board.png` | Cần đăng nhập vai trò Kitchen. Chứng minh US-06 |
| **P1-4** | Chụp màn hình **tất toán tại quầy** (COD + VietQR) | **Lê Anh** | 2 ảnh: hóa đơn bàn gộp nhiều lượt, và màn hình xác nhận VietQR, lưu `docs/assets/report/counter-*.png` | Cần đăng nhập vai trò CounterStaff. Chứng minh US-07 |
| **P1-5** | Chụp **luồng khách đầy đủ** trên điện thoại | **Đỗ Tuấn Anh** | 4 ảnh mobile: quét QR, thực đơn, giỏ, theo dõi trạng thái, lưu `docs/assets/report/customer-flow-*.png` | Đã có sẵn ảnh điểm vào (Hình 5.1); cần thêm 3 bước sau |
| **P1-6** | Bật **branch ruleset** và required checks | **Phạm Duy An** | `main` và `develop` không merge được khi CI đỏ; ảnh chụp Settings → Rules | Hạn chế #8 ở §5.3, cần quyền admin repo |
| **P1-8** | Đọc soát báo cáo, kiểm mọi link GitHub | **Bùi Đào Đức Anh** | Không link 404, không lỗi chính tả, số liệu khớp §7 Phụ lục | Rubric mục *Hình thức báo cáo* — 10 % |
| **P1-11** | Dọn ổ đĩa C của máy phát triển | **Phạm Duy An** | C: còn tối thiểu 20 GB trống | Trong đợt rà soát, C: xuống **0 MB** và chặn cả `dotnet test` lẫn lệnh `ls`. Đã giải phóng tạm 3,1 GB nhưng chưa xử lý gốc |

### Ưu tiên 2 — nâng điểm sản phẩm (hạn: 12/08/2026)

| Mã | Đầu việc | Người làm | Tiêu chí hoàn thành | Hạn chế xử lý |
|---|---|---|---|---|
| **P2-1** | Audit **nhãn dị nguyên cho 47 món còn lại** | **Phạm Duy An** | `python ai/scripts/audit_allergen_tags.py` xanh với độ phủ 91/91; chạy lại `run_baseline.py --all` vẫn **0 lỗi an toàn** | #7 |
| **P2-2** | **Human evaluation** 50 câu, ≥20 % chấm đôi | **Phạm Duy An** (thiết kế) + **cả nhóm** (chấm) | Bảng điểm + độ đồng thuận giữa hai người chấm; kết quả đưa vào §5.2.2 | #2 |
| **P2-3** | **Kiểm thử tải** trên staging | **Nguyễn Quang Hiếu** | Báo cáo: số bàn đồng thời tối đa trước khi p95 vượt 20 s; script lưu trong `tests/` | #1 |
| **P2-4** | Bổ sung **test backend cho luồng hóa đơn bàn nhiều lượt** | **Bùi Đào Đức Anh** | Test mới trong `TableInvoiceTests.cs` phủ: 3 lượt đơn → 1 hóa đơn → áp khuyến mãi → tất toán | Củng cố US-07 |
| **P2-5** | **Kiểm thử a11y** cho ứng dụng khách | **Đỗ Tuấn Anh** | Chạy Lighthouse/axe trên 3 màn hình chính; liệt kê lỗi và sửa lỗi mức *serious* trở lên | #4 |
| **P2-6** | **Ngân sách hiệu năng** frontend | **Lê Anh** | Đo kích thước bundle từng app; ghi lại và đặt ngưỡng cảnh báo | #4 |

### Ưu tiên 3 — chuẩn bị vấn đáp (hạn: trước buổi bảo vệ)

Rubric vấn đáp chiếm **20 %** và chấm *"giải thích được quyết định kỹ thuật & đóng góp cá nhân trên GitHub"*.
Mỗi người chuẩn bị trả lời **được** những câu sau về mảng của mình:

| Người | Câu hỏi phải trả lời được |
|---|---|
| **Phạm Duy An** | • Vì sao chọn modular monolith mà **không** microservices? Tiêu chí tách dịch vụ AI là gì?<br>• Vì sao bỏ hybrid retrieval dù ADR cũ đã chốt nó? Con số nào lật kết luận?<br>• Làm sao chứng minh AI **không thể** gợi ý món chứa dị nguyên khách đã nêu?<br>• Cổng deploy hai đầu hoạt động thế nào và nó chặn được lỗi gì? |
| **Bùi Đào Đức Anh** | • Capability token khác `sessionId` ở chỗ nào? Vì sao `sessionId` **không** đủ để cấp quyền?<br>• Mật khẩu lưu thế nào và vì sao không dùng hash thường?<br>• Vì sao VietQR phải xác nhận thủ công? Rủi ro còn lại là gì?<br>• Cơ chế khóa tài khoản chống được tấn công nào? |
| **Nguyễn Quang Hiếu** | • Vì sao mã đơn sinh bằng PostgreSQL sequence chứ không sinh ở tầng ứng dụng?<br>• `xmin` và `CONFLICT_STALE` giải quyết vấn đề gì? Cho một tình huống cụ thể.<br>• Unique index có điều kiện cưỡng chế bất biến nào?<br>• Vì sao dùng SignalR thay vì polling cho bảng bếp? |
| **Đỗ Tuấn Anh** | • Vì sao giỏ hàng lưu **phía máy chủ** thay vì `localStorage`?<br>• Nhiều thiết bị quét cùng QR thì chuyện gì xảy ra và vì sao đó là hành vi đúng?<br>• Frontend xử lý thế nào khi trợ lý AI trả câu chuyển nhân viên?<br>• Vì sao tách 5 app Vite thay vì một SPA? |
| **Lê Anh** | • Vì sao admin, quầy và bếp dùng **chung một build**? Vai trò quyết định gì?<br>• Vai trò trong frontend có phải là cơ chế bảo mật không? Vì sao?<br>• Bảng bếp cập nhật realtime bằng cách nào? Mất kết nối thì sao?<br>• Thao tác trên bảng bếp được thiết kế cho ràng buộc nào của người dùng? |

---

## 4. Quy trình thực hiện — giữ nguyên như 5 tuần trước

Mỗi đầu việc đi đúng vòng đời đã dùng suốt dự án:

```text
1. Mở issue          → tiêu đề [Tuần 6][Mảng] ...
                     → gắn nhãn role:* + type:* + week-6
                     → gán người + milestone "Tuần 6 — Hoàn thiện và bảo vệ"
2. Tạo nhánh         → issue-<số>/<tên>-<việc-ngắn>, nhánh cha là `develop`
3. Làm việc          → commit theo Conventional Commits
4. Mở PR             → target `develop`, ghi "Closes #<số>"
                     → điền PR template: mô tả, lệnh kiểm chứng, ảnh cho thay đổi UI
5. CI phải xanh      → 5 job của ci.yml + security.yml
6. Review            → nhóm trưởng review; PR đụng migration BẮT BUỘC có người xem
7. Merge             → squash vào `develop`
8. Phát hành         → develop → main qua promote-production.yml
```

**Việc cần làm trước tiên (nhóm trưởng):**

```bash
# Tạo milestone và nhãn cho giai đoạn cuối
gh api repos/Anpham120/restaurant-qr-ai-ordering/milestones \
  -f title="Tuần 6 — Hoàn thiện và bảo vệ" \
  -f description="Bù khoảng trống rubric, xử lý hạn chế đã ghi, chuẩn bị vấn đáp." \
  -f due_on="2026-08-12T00:00:00Z"

gh label create week-6 --description "Tuần 6 - Hoàn thiện và bảo vệ" --color d4c5f9
```

Sau đó mở 14 issue theo mã **P1-1 … P2-6** ở bảng trên, gán đúng người.

---

## 5. Lịch và điểm kiểm tra

| Mốc | Ngày | Ai chốt | Điều kiện đạt |
|---|---|---|---|
| Xong toàn bộ **Ưu tiên 1** | 05/08/2026 | Phạm Duy An | Báo cáo không còn placeholder ảnh nào; branch ruleset đã bật; số test backend đã đo thật |
| Xong toàn bộ **Ưu tiên 2** | 12/08/2026 | Phạm Duy An | 6 hạn chế được xử lý hoặc ghi rõ lý do hoãn; §5.2.2 và §5.3 cập nhật theo số mới |
| Diễn tập vấn đáp | Trước bảo vệ 3 ngày | Cả nhóm | Mỗi người trả lời trơn 4 câu của mình; ai vướng thì đọc lại tài liệu mảng đó |
| Nộp bài | Theo lịch học phần | Phạm Duy An | Báo cáo bản cuối + link repository + link sản phẩm chạy được |

---

## 6. Bảng tra nhanh: mảng nào đọc tài liệu nào

| Người | Tài liệu cần nắm chắc |
|---|---|
| **Phạm Duy An** | [SYSTEM_ANALYSIS_DESIGN](../archive/SYSTEM_ANALYSIS_DESIGN.md) · [AI_RAG_ARCHITECTURE](../ai/AI_OPERATIONS.md) · [ai/README.md](../../ai/README.md) · [CICD_PIPELINE](../devops/PIPELINE_AND_DEPLOY.md) · [PRODUCTION_OPERATIONS](../devops/PIPELINE_AND_DEPLOY.md) |
| **Bùi Đào Đức Anh** | [QR_SESSION_STATE_MACHINE](../backend/ARCHITECTURE.md) · [SECURITY.md](../../SECURITY.md) · [API_CONTRACT](../backend/API_CONTRACT.md) mục Auth & Payments |
| **Nguyễn Quang Hiếu** | [BACKEND_MODULAR_MONOLITH_ARCHITECTURE](../backend/ARCHITECTURE.md) · [BACKEND_DATABASE_SETUP](../backend/DATABASE.md) · [SYSTEM_ANALYSIS_DESIGN](../archive/SYSTEM_ANALYSIS_DESIGN.md) mục 5–7 (ERD, state machine) |
| **Đỗ Tuấn Anh** | [API_CONTRACT](../backend/API_CONTRACT.md) mục Cart & Orders · [QR_SESSION_STATE_MACHINE](../backend/ARCHITECTURE.md) · [AI_NO_TOUCH_BOUNDARY](../ai/AI_NO_TOUCH_BOUNDARY.md) |
| **Lê Anh** | [OPERATIONS_WORKSPACES](../frontend/OPS_APP.md) · [COUNTER_POS_RUNBOOK](../frontend/OPS_APP.md) · [SECURITY.md](../../SECURITY.md) mục Enforcement |

Toàn bộ tài liệu bắt đầu từ [Documentation Hub](../README.md).
