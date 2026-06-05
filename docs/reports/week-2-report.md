# Báo Cáo Tuần 2

> Template dùng cho Week 2 - Core Ordering. Khi nộp báo cáo thật, thay các placeholder bằng bằng chứng PR/build/test cụ thể.

## 1. Thông Tin Chung

- Dự án: Restaurant QR AI Ordering.
- Milestone: Week 2 - Core Ordering.
- Issue lead/docs: #10 - API contract, seed data plan, and integration test scenarios.
- Branch: `issue-10/anpham120-api-contract-seed-integration`.
- PR: `<link PR>`.
- Commit chính: `<commit hash>`.
- Người phụ trách: `Anpham120`.

## 2. Mục Tiêu Tuần 2

- Khóa API contract cho auth, menu, tables, order creation, order detail và error shape.
- Thống nhất shared enum/status names cho frontend, backend, admin, chatbot và realtime.
- Định nghĩa seed data plan cho `T01` đến `T08` và menu demo.
- Chuẩn bị checklist tích hợp thủ công cho QR customer order, pickup, delivery mock và admin availability.
- Ghi nhận contract drift risk trước khi member code tiếp.

## 3. Phần Đã Hoàn Thành

| Hạng mục | Trạng thái | Bằng chứng |
| --- | --- | --- |
| API contract auth/menu/tables/orders/error | `<done/todo>` | `docs/API_CONTRACT.md` |
| Shared enum/status names | `<done/todo>` | `docs/API_CONTRACT.md#2-shared-enum--status-names` |
| Seed data plan `T01`-`T08` và menu | `<done/todo>` | `docs/API_CONTRACT.md#10-seed-data-plan-tuần-2` |
| Manual integration scenarios | `<done/todo>` | `docs/TEST_PLAN.md` |
| Review open PRs for drift | `<done/todo>` | `<gh pr list evidence>` |
| Verification | `<done/todo>` | `<build/test/diff evidence>` |

## 4. Seed Data Chuẩn

- Tables: `T01`, `T02`, `T03`, `T04`, `T05`, `T06`, `T07`, `T08`.
- QR route demo: `/table/T01` đến `/table/T08`.
- Menu item IDs: `m_001` đến `m_012`.
- Unavailable demo items: `m_003`, `m_010`.
- Demo cần hỗ trợ: QR dine-in, public menu, admin availability, chatbot suggestion, pickup, delivery mock.

## 5. Integration Checklist

- QR customer order từ `/table/T05`.
- Online pickup từ `/menu`.
- Delivery mock có `deliveryInfo`.
- Admin đổi `isAvailable` và customer/chatbot không đặt món hết hàng.

## 6. Contract Drift / Risk

- `<risk 1>`.
- `<risk 2>`.
- `<risk 3>`.

## 7. Verification Evidence

```text
git diff --check
<output>

docs/file existence check
<output>

frontend build
<output hoặc lý do không chạy>

backend test
<output hoặc lý do không chạy>
```

## 8. Giới Hạn / Chưa Làm

- Không implement feature code trong issue #10.
- Không sửa backend/frontend member-owned logic.
- Không chạm deployment production.
- Không chạm `.playwright-cli/` hoặc `tmp/`.

## 9. Báo Cáo Kết Quả Để Comment Issue

```text
## Bao cao ket qua
- Issue:
- Branch:
- PR:
- Commit chinh:
- Da lam:
- File/chuc nang da thay doi:
- Cach test:
- Bang chung:
- Phan chua lam / gioi han:
- Co sua ngoai scope khong:
```
