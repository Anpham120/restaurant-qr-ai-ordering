# Chính Sách Bảo Mật

## Phiên bản được hỗ trợ

| Phiên bản | Hỗ trợ |
| --- | --- |
| 0.1.x | ✅ |

## Báo cáo lỗ hổng

Vui lòng **không** mở issue công khai cho lỗ hổng bảo mật.

- Gửi báo cáo riêng tư qua [GitHub Security Advisories](https://github.com/Anpham120/restaurant-qr-ai-ordering/security/advisories/new), hoặc
- Liên hệ trưởng nhóm dự án.

Khi báo cáo, mô tả bước tái hiện, phạm vi ảnh hưởng và phiên bản/commit liên quan.
Chúng tôi sẽ phản hồi trong thời gian sớm nhất.

## Quản lý secrets

- Không commit secrets vào mã nguồn. Mọi khóa/bí mật nạp qua biến môi trường và
  GitHub Environments (`staging`, `production`).
- Tài khoản demo chỉ bật khi đặt `SEED_DEMO_USERS=true` (local/dev).
- Admin khởi tạo qua `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD`.
- Xoay vòng định kỳ `JWT_SIGNING_KEY` và mật khẩu PostgreSQL.
