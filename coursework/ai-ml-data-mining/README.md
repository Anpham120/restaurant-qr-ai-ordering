# CMC Restaurant AI/ML & Data Mining Coursework

Thư mục này chứa artifact học phần Học máy và Khai phá dữ liệu cho dự án CMC Restaurant QR AI Ordering.

Mục tiêu của phần này là chứng minh phần AI của dự án không chỉ là chatbot gọi LLM API. Notebook tập trung vào dữ liệu, tiền xử lý, phân tích giỏ hàng, luật kết hợp, gợi ý món và đánh giá kết quả.

## Ranh Giới Với 9router Và LLM

- Notebook này không gọi 9router.
- Notebook này không gọi OpenAI, 9router hay bất kỳ external LLM API nào.
- Dự án sản phẩm có thể gọi LLM qua API ở phần chatbot/RAG, nhưng nhóm không huấn luyện LLM.
- Đóng góp ML/Data Mining nằm ở dataset, preprocessing, association rule mining, content-based recommendation, baseline và evaluation.

## Cấu Trúc

```text
coursework/ai-ml-data-mining/
├── CMC_Restaurant_AI_ML_Data_Mining.ipynb
├── README.md
├── data/
│   ├── menu_items.csv
│   ├── order_transactions.csv
│   └── faq_entries.csv
├── outputs/
│   ├── association_rules.csv
│   ├── recommendation_examples.csv
│   └── charts/
└── report/
    └── ai_ml_data_mining_summary.md
```

## Dataset

- `data/menu_items.csv`: danh mục món, giá, tag mô tả, trạng thái còn món.
- `data/order_transactions.csv`: dữ liệu giao dịch dạng long-form, mỗi dòng là một item trong đơn.
- `data/faq_entries.csv`: câu hỏi/intent mẫu để giải thích cách insight hỗ trợ chatbot/RAG.

Dataset hiện là dữ liệu tổng hợp nhỏ, dùng cho trình bày học phần. Khi có dữ liệu thật, có thể thay bằng log đơn hàng đã ẩn danh.

## Cách Chạy Trong Google Colab

1. Mở `CMC_Restaurant_AI_ML_Data_Mining.ipynb` bằng Google Colab.
2. Upload cả thư mục `coursework/ai-ml-data-mining/` hoặc clone repository vào Colab.
3. Đặt working directory là thư mục `coursework/ai-ml-data-mining/`.
4. Chạy lần lượt các cell từ trên xuống.
5. Kiểm tra output:
   - `outputs/association_rules.csv`
   - `outputs/recommendation_examples.csv`
   - biểu đồ trong `outputs/charts/`

## Nội Dung Notebook

- Đọc và kiểm tra dataset schema.
- EDA: món bán chạy, phân bố danh mục, kích thước đơn, giá trị trung bình đơn.
- Content-based recommendation dựa trên category, tags, price range, description và availability.
- Association rule mining với support, confidence, lift.
- Baseline gợi ý món phổ biến.
- Đánh giá bằng Precision@K, Recall@K, support/confidence/lift và các case định tính.
- Kết luận cách dùng output để hỗ trợ chatbot/RAG mà không bịa món hoặc giá.

## Lưu Ý Khi Thuyết Trình

- Nói rõ chatbot gọi external LLM API, không phải LLM do nhóm tự train.
- Notebook là phần học máy/khai phá dữ liệu riêng: tạo insight từ menu/order/FAQ.
- Gợi ý món phải lọc `is_available = true`; không được gợi ý món tạm hết hoặc món không có trong menu.
- Association rules chỉ là bằng chứng thống kê trên dữ liệu mẫu, chưa phải kết luận kinh doanh cuối cùng.
