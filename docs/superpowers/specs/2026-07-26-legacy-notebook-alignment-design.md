# Thiết kế đồng bộ notebook lịch sử với runtime hiện tại

## Mục tiêu

Làm notebook canonical có độ sâu và chất lượng trực quan của notebook cũ, nhưng
không biến metric/dataset/commit lịch sử thành bằng chứng production hiện hành.

## Phân loại nội dung

Mỗi phần tái sử dụng phải mang một trong ba nhãn:

- **Đang chạy trong runtime:** có implementation và contract hiện tại tương ứng.
- **Historical research:** giữ phương pháp, biểu đồ hoặc case study cũ để giải
  thích; không dùng làm quyết định release.
- **Cần chạy lại:** phương pháp vẫn đúng nhưng artifact/metric không trùng hash
  canonical hiện tại; hiển thị lệnh và điều kiện tái chạy.

## Nội dung tái sử dụng có kiểm chứng

1. KB inventory, chunk distribution, risk tier, variants và chunk strategy.
2. Normalize tiếng Việt: before/after, lexical normalization, scoring
   normalization và vocabulary mismatch.
3. BM25, Dense E5-small, Hybrid RRF: công thức, điều kiện so sánh, false
   positive, error analysis, ablation variants/normalize, latency, heatmap.
4. Evidence routing, guardrails, session memory, claim verifier và case study
   đa lượt.

Các mục trên được gắn dữ liệu/code hiện hành khi runtime có implementation;
metric cũ chỉ dùng dưới nhãn Historical research.

## Nội dung mới bắt buộc

- Mục mở đầu “Notebook cũ ↔ runtime hiện tại” gồm bảng `notebook claim`,
  `runtime evidence`, `status`, `impact`.
- DeepSeek primary/Luna HTTP-429-only fallback, ba profile pipeline, canonical
  manifest, artifact hash compatibility và CI fail-closed.
- Quy tắc: `pipeline_selection.json` hash khác canonical bundle thì hiện
  `RERUN REQUIRED`, không được tuyên bố winner deployable.

## Trình bày

Không dùng biểu đồ generic lặp lại. Mỗi biểu đồ phải có câu hỏi, dữ liệu nguồn,
nhãn trạng thái, nhận xét và quyết định. Các chart historical dùng caption
“Historical research — không phải release metric”; chart current ghi hash hoặc
artifact path.

## Kiểm thử

- Test structural kiểm tra bảng alignment, ba nhãn và các subsection cũ được
  tái dùng.
- Notebook execute không có error output.
- Không có metric historical trong cell kết luận production nếu hash không
  tương thích.
