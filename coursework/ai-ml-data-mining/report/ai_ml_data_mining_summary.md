# AI/ML & Data Mining Summary

## Mục Tiêu

Artifact này trình bày phần Học máy và Khai phá dữ liệu của CMC Restaurant QR AI Ordering. Phần sản phẩm có chatbot dùng external LLM API và RAG, nhưng phần học phần tập trung vào dữ liệu menu/order/FAQ, khai phá luật kết hợp và gợi ý món có đánh giá.

## Dữ Liệu

Dữ liệu mẫu gồm ba nguồn:

- `menu_items.csv`: 12 món, danh mục, giá, tag, mô tả và trạng thái còn món.
- `order_transactions.csv`: 10 đơn hàng dạng long-form với item, số lượng, loại đơn, bàn/session và segment khách.
- `faq_entries.csv`: 5 câu hỏi/intent mẫu liên kết tới món thật trong menu.

Dataset là synthetic nhưng giữ cấu trúc gần với app: menu item, order item, order type, table/session context và availability.

## Phương Pháp

### 1. Content-Based Recommendation

Notebook tạo đặc trưng từ category, tags, description, price range và availability. Khi người dùng đưa ngữ cảnh như "hải sản", "đồ uống thanh mát" hoặc "nhóm 4 người", hệ thống chỉ gợi ý các món đang còn bán và có trong menu.

Ý nghĩa với app:

- Giúp chatbot/RAG lấy insight có kiểm soát.
- Không để chatbot tự bịa món, giá hoặc trạng thái còn hàng.
- Có thể dùng như lớp pre-filter trước khi LLM diễn giải câu trả lời.

### 2. Association Rule Mining

Notebook tính các luật dạng `A -> B` từ giỏ hàng:

- support: tỷ lệ đơn chứa cả A và B.
- confidence: xác suất khách gọi B khi đã gọi A.
- lift: mức độ liên quan so với ngẫu nhiên.

Ví dụ output:

- `Gỏi cuốn tôm thịt -> Lẩu Thái hải sản`
- `Bò lúc lắc -> Nem rán Hà Nội`
- `Phở bò đặc biệt -> Trà đào cam sả`

Các luật này phù hợp để gợi ý combo hoặc upsell nhẹ trong chatbot, nhưng vẫn cần kiểm tra availability.

### 3. Baseline

Baseline dùng món phổ biến hoặc món phổ biến theo ngữ cảnh, ví dụ:

- order type là Pickup thì ưu tiên `Phở bò đặc biệt`, `Trà đào cam sả`.
- nhóm đông thì ưu tiên món share như `Lẩu Thái hải sản`, `Tôm rang muối`.

Baseline giúp so sánh với content-based và association rules.

## Đánh Giá

Notebook dùng:

- Precision@K và Recall@K cho các case gợi ý mẫu.
- support, confidence, lift cho luật kết hợp.
- đánh giá định tính theo các tình huống demo.

Kết quả mẫu cho thấy các case có tag rõ như hải sản hoặc đồ uống có Precision@3 cao hơn, còn case nhóm đông cần kết hợp luật kết hợp và món phổ biến.

## Kết Luận

Phần AI của dự án được tách rõ:

- Chatbot sản phẩm: gọi external LLM API và RAG, không train LLM.
- ML/Data Mining: xử lý dữ liệu menu/order/FAQ, khai phá luật, tạo gợi ý, đánh giá bằng metric.

Cách trình bày này phù hợp với bài tập lớn môn Học máy và Khai phá dữ liệu vì có dataset, preprocessing, mô hình gợi ý đơn giản, luật kết hợp, baseline, metric và kết luận.

## Giới Hạn

- Dữ liệu hiện là synthetic, quy mô nhỏ.
- Association rules dễ nhiễu nếu số đơn thấp.
- Recommendation chưa dùng lịch sử cá nhân dài hạn.
- Notebook không triển khai production API và không gọi 9router.
- Khi tích hợp app thật, phải lọc món tạm hết và kiểm tra giá từ backend trước khi hiển thị.
