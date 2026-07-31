---
id: kb.written.reading_labels.v1
title: Cách đọc nhãn trên thực đơn, và giới hạn của chúng
topic_keys: [reading_labels]
source: demo
audience: guest
answer_mode: synthesize
---

# Cách đọc nhãn trên thực đơn, và giới hạn của chúng

## Mỗi món có khoảng 15 nhãn, chia 16 nhóm

Nhãn là cách trợ lý lọc món. Hiểu nhóm nhãn nào **phủ hết** 91 món và nhóm nào **chỉ phủ một
phần** là điều quyết định khi đọc câu trả lời của trợ lý.

## Bốn nhóm phủ 91/91 món — lọc theo chúng là chắc chắn

- **Độ cay** (`spice`) — mọi món có mức cay.
- **Mức giá** (`price`) — mọi món có mức.
- **Khẩu phần** (`party`) — mọi món có ghi phù hợp mấy người.
- **Mùa** (`season`) — mọi món có ghi phù hợp mùa nào.

Khi bạn nói "không cay" hoặc "dưới 100 nghìn", trợ lý lọc trên bốn nhóm này và kết quả đầy đủ.

## Các nhóm phủ MỘT PHẦN — thiếu nhãn nghĩa là *chưa ghi*, không phải *không có*

- **Dị nguyên** (`allergen`) phủ 44/91 món. Đây là nhóm quan trọng nhất và cũng là nhóm phủ thấp
  nhất trong các nhóm đáng lo. 47 món còn lại **chưa có ghi nhận** — và điều đó chỉ nghĩa là thực
  đơn chưa ghi.
- **Vùng miền** (`region`) phủ 65/91.
- **Vị** (`flavour`) phủ 72/91.
- **Cách chế biến** (`method`) phủ 57/91.
- **Nguyên liệu** (`ingredient`) phủ 57/91.
- **Sức khỏe** (`health`) phủ 67/91.
- **Dịp ăn** (`occasion`) phủ 79/91.
- **Đối tượng** (`audience`) phủ 52/91.
- **Chế độ ăn** (`diet`) phủ 17/91 — đúng 17 món chay.
- **Nổi bật** (`promo`) phủ 4/91 — 3 món bán chạy, 2 món đặc trưng.

## Hệ quả thực dụng của việc phủ một phần

Khi bạn hỏi "món nào có tỏi", trợ lý chỉ trả được món **có ghi nhãn** nguyên liệu tỏi. Món có tỏi
mà chưa ghi nhãn sẽ không xuất hiện. Nên với câu hỏi về nguyên liệu, câu trả lời của trợ lý là
*những món thực đơn ghi nhận*, không phải *tất cả món chứa thứ đó*.

Chiều ngược lại thì đáng tin hơn: nếu một món **có** nhãn thì nhãn đó đúng.

## Nhãn cảm quan không phải kết quả phân tích

Nhãn như "ít calo", "thanh nhẹ", "giàu protein" là **đánh giá của người nhập thực đơn**, không
phải kết quả đo dinh dưỡng. Dùng chúng để gợi ý thì được; dùng chúng như số liệu y tế thì không.

Thực đơn **không có** số liệu dinh dưỡng nào — không kcal, không gam đường, không natri.

## Vì sao một món có tới 15 nhãn

Vì các nhóm độc lập với nhau. Một món có thể vừa không cay, vừa bình dân, vừa phù hợp một người,
vừa cả năm, vừa miền Bắc, vừa món nước, vừa phù hợp trẻ em. Bảy nhãn cho một món là bình thường,
và nhiều nhãn **không** nghĩa là món đó đặc biệt hơn.
