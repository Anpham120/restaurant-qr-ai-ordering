# Menu Và Quy Tắc Gợi Ý Món

AI chỉ được gợi ý món có trong menu backend gửi sang request hoặc món có trong knowledge base đã được duyệt. Không tự tạo tên món, giá, combo hoặc ưu đãi mới.

## Nhóm Món Chính

- Cơm gà xối mỡ: món chính phổ biến, hợp khách muốn ăn no nhanh.
- Cơm sườn nướng: món chính vị đậm, hợp bữa trưa hoặc bữa tối.
- Phở bò tái: món nước nóng, hợp khách muốn món nhẹ nhưng đủ no.
- Bún bò Huế: món cay, chỉ gợi ý nếu trạng thái còn hàng.

## Khai Vị Và Món Nhẹ

- Gỏi cuốn tôm thịt: món nhẹ, ít dầu, hợp ăn kèm.
- Chả giò hải sản: món chiên giòn, hợp đi cùng món nước hoặc đồ uống mát.

## Đồ Uống Và Tráng Miệng

- Trà đào cam sả: đồ uống mát, hợp món cay hoặc món nướng.
- Cà phê sữa đá: đồ uống cà phê, hợp khách muốn tỉnh táo.
- Chè khúc bạch: tráng miệng mát, hợp sau món chính.
- Bánh flan caramel: chỉ gợi ý nếu trạng thái còn hàng.

## Quy Tắc Giá

Giá món phải lấy từ backend hoặc dữ liệu menu đã duyệt. Nếu không có giá trong context, AI phải nói rằng hệ thống chưa có đủ thông tin giá.
