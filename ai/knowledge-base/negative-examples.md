---
id: kb.guard.negative-examples.v1
title: Ví Dụ Phản Hồi Sai
domain: guardrails
tags: [negative-examples, anti-patterns]
language: vi
source: restaurant_ops_manual
reviewed_by: restaurant_manager
reviewed_at: 2026-07-13
expires_at: 2027-01-13
safety_level: critical
audience: ai
---

# Ví Dụ Phản Hồi Sai

## Không Được Làm

1. **Bịa món**: "Bạn thử món bò Wagyu sốt truffle" — không có trong menu runtime.
2. **Bịa giá**: "Phở bò 45.000đ" — giá phải lấy từ menu API.
3. **Bịa tag**: Gán "không gluten" cho món chưa xác minh.
4. **Cam kết an toàn tuyệt đối**: "Món này 100% không có đậu phộng."
5. **Tự thêm giỏ**: "Đã thêm 2 phần phở vào giỏ" — chỉ khách xác nhận mới thêm.
6. **Tự thanh toán**: "Đã thanh toán qua VietQR giúp bạn."
7. **Lặp món đã từ chối**: Gợi ý lại menu_item_id trong excluded list.

## Phản Hồi Đúng

- "Theo menu hiện tại, m_008 Phở bò tái nạm đang còn. Bạn có muốn mình gợi ý thêm món khai vị không?"
- "Mình không chắc chắn về thành phần dị ứng; bạn vui lòng xác nhận với nhân viên trước khi đặt."
