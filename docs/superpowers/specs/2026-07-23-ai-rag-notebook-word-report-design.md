# Thiết kế notebook và báo cáo Word học thuật cho hệ thống AI/RAG

## 1. Mục tiêu

Tái cấu trúc toàn bộ phần trình bày nghiên cứu AI/RAG của dự án theo mạch học thuật
tuần tự, dễ theo dõi đối với giảng viên:

1. Giới thiệu bài toán và động lực.
2. Trình bày cơ sở lý thuyết trước khi sử dụng thuật ngữ hoặc metric.
3. Mô tả dữ liệu và phương pháp thực nghiệm.
4. Trình bày kết quả thật, phân tích nguyên nhân và ra quyết định kỹ thuật.
5. Kết luận rõ những gì đã chứng minh và những gì chưa đủ bằng chứng.

Hai artifact bàn giao chính:

- Một notebook duy nhất: `ai/notebooks/rag_retrieval_research.ipynb`.
- Một báo cáo Word có thể chỉnh sửa:
  `output/reports/Bao_cao_do_an_AI_RAG_CMC_Restaurant.docx`.

## 2. Tài liệu tham chiếu

### 2.1 Mẫu notebook

`D:/01_Projects/AI/AVC/AI/do-an-cuoi-ky/tri-tue-nhan-tao/notebooks/Traffic_Sign_Recognition_Pipeline.ipynb`

Chỉ học cách tổ chức pipeline:

- Chia thành các phần lớn có đầu vào và đầu ra rõ ràng.
- Xen kẽ giải thích, code, kết quả trực quan và nhận xét.
- Phần trước tạo dữ liệu hoặc mô hình cho phần sau.

Không sao chép nội dung nhận diện biển báo.

### 2.2 Mẫu báo cáo học thuật

`D:/03_Downloads/Documents/Nhom1_TTNT_FINAL.pdf`

Chỉ học hình thức học thuật:

- Bìa trường/khoa/môn học.
- Tóm tắt, mục lục, danh mục hình, danh mục bảng và thuật ngữ.
- Năm chương: Giới thiệu, Cơ sở lý thuyết, Phương pháp thực nghiệm,
  Thực nghiệm và kết quả, Kết luận và hướng phát triển.
- Tài liệu tham khảo và phụ lục.
- Bảng có tiêu đề, hình có caption, nội dung phải dẫn chiếu và phân tích.

Không dùng báo cáo tiến độ làm template và không sao chép ngữ cảnh nhận diện biển báo.

## 3. Các ràng buộc bắt buộc

- Không tạo hoặc bàn giao báo cáo HTML.
- Không dùng HTML để dựng sơ đồ hoặc biểu đồ.
- Trực quan hóa chỉ dùng thư viện Python:
  Matplotlib, Seaborn và Matplotlib patches.
- Không dùng Plotly hoặc output tương tác phụ thuộc trình duyệt.
- Notebook hiển thị code; báo cáo Word không hiển thị code.
- Không tạo số minh họa, placeholder chart hoặc metric hard-code.
- Mọi số liệu trong Word và notebook phải đọc từ artifact đã khóa.
- Mọi tỷ lệ phải có tử số/mẫu số hoặc `n`.
- Không đưa hình `not_measured` vào nội dung chính.
- Những nội dung chưa đo chỉ xuất hiện trong một bảng hạn chế/hướng phát triển.
- Chỉ giữ một notebook `.ipynb`.
- Word phải chỉnh sửa được bằng Microsoft Word, dùng style thật thay vì ảnh chụp văn bản.

## 4. Đối tượng đọc

Đối tượng chính là giảng viên môn Trí tuệ nhân tạo. Người đọc cần hiểu:

- Bài toán chatbot + RAG là gì.
- Vì sao kiến trúc được xây dựng theo cách hiện tại.
- Dữ liệu đi qua những bước nào.
- BM25, Dense, Hybrid, session memory, evidence routing và verifier hoạt động ra sao.
- Thực nghiệm được tổ chức công bằng như thế nào.
- Số liệu cho phép kết luận gì và không cho phép kết luận gì.

Không giả định người đọc đã biết cấu trúc source code hoặc tên artifact.

## 5. Thiết kế notebook

### 5.1 Nhịp trình bày chuẩn

Mỗi kỹ thuật hoặc thí nghiệm phải theo thứ tự:

1. **Vấn đề:** Thành phần này giải quyết lỗi hoặc nhu cầu nào?
2. **Nguyên lý:** Giải thích khái niệm bằng ngôn ngữ và công thức phù hợp.
3. **Input/Output:** Dữ liệu đi vào và đầu ra là gì?
4. **Hiện thực:** Code Python hoặc trích nguồn runtime đang dùng.
5. **Kết quả:** Bảng hoặc biểu đồ sinh trực tiếp từ artifact.
6. **Phân tích:** Vì sao có kết quả đó, giới hạn của phép đo.
7. **Quyết định:** Giữ, loại hoặc cần thử nghiệm thêm.

Không sử dụng lại khuôn năm mục chung cho mọi chương.

### 5.2 Cấu trúc notebook

#### PHẦN I — BÀI TOÁN VÀ DỮ LIỆU

1. Bối cảnh chatbot nhà hàng và phát biểu bài toán.
2. Vì sao LLM thuần hoặc always-RAG có thể trả lời sai.
3. Các nhóm câu hỏi: menu, live data, FAQ/chính sách, follow-up và small talk.
4. Ba nguồn dữ liệu: database trực tiếp, knowledge base và session state.
5. Phân tích corpus/dataset bằng số liệu thật.
6. Ingestion, chunking, stable ID, content hash và versioned index.

#### PHẦN II — XÂY DỰNG RETRIEVAL

1. Chuẩn hóa truy vấn.
2. BM25: nguyên lý, code và ví dụ kết quả.
3. Dense retrieval: embedding, cosine similarity, code và ví dụ.
4. Hybrid RRF: công thức hợp nhất thứ hạng và ví dụ.
5. Typed menu filters cho ngân sách, số người, category và tag.
6. So sánh cùng một truy vấn qua BM25, Dense và Hybrid.

#### PHẦN III — XÂY DỰNG CHATBOT CÓ NGỮ CẢNH

1. Kiến trúc tổng thể.
2. Intent và evidence routing.
3. Reference resolution cho các câu như “món đó”, “còn món khác?”.
4. Typed session memory và rolling summary.
5. Live database path, KB RAG path, deterministic path và clarification path.
6. Structured claims, evidence mapping, verifier và useful abstention.
7. Một phiên chat mẫu 12 lượt được dùng xuyên suốt để minh họa state thay đổi.

#### PHẦN IV — THỰC NGHIỆM VÀ KẾT QUẢ

1. Dataset, split, hardware/software và protocol.
2. Giải thích Hit@5, MRR, nDCG, faithfulness, availability và latency.
3. So sánh bảy phương pháp retrieval trên cùng 110 case.
4. Kiểm định cặp và đánh đổi quality-latency-RAM.
5. Đánh giá 50 phiên hội thoại nhiều lượt.
6. So sánh GPT-5.5 và DeepSeek trên cùng case/evidence/prompt/budget.
7. Failure taxonomy và bốn case study.
8. Cấu hình được chọn và điều kiện release.

#### PHẦN V — KẾT LUẬN

1. Tổng hợp phát hiện.
2. Cấu hình hệ thống đề xuất.
3. Những giới hạn còn tồn tại.
4. Human review, frozen test, calibration và staging cần thực hiện tiếp.

### 5.3 Chính sách hình

Nội dung chính chỉ dùng:

- Sơ đồ kiến trúc `design` có giá trị giải thích.
- Biểu đồ `measured`.
- Biểu đồ có mẫu nhỏ nhưng số đo thật, nếu caption ghi rõ `n` và giới hạn.

Không dùng trong nội dung chính:

- R03: leakage matrix chưa audit.
- R04: chunking comparison chưa chạy.
- R12: calibration chưa có prediction được hiệu chỉnh.
- R16: ablation chỉ có một cấu hình hoàn thành.

Mỗi hình phải có:

- ID và caption tiếng Việt.
- Nguồn artifact.
- Split và `n`.
- Đoạn “Nhận xét” ngay sau hình.
- Đoạn “Quyết định” nếu hình được dùng để chọn cấu hình.

## 6. Thiết kế báo cáo Word

### 6.1 Hình thức

- Khổ A4 dọc.
- Font Times New Roman, cỡ nội dung 13 pt, giãn dòng 1.5.
- Lề: trên 2 cm, dưới 2 cm, trái 3 cm, phải 2 cm.
- Header có logo CMC và tên môn “Trí tuệ nhân tạo”.
- Footer có số trang.
- Heading đánh số theo `1`, `1.1`, `1.1.1`.
- Bảng dùng header xanh đậm theo mẫu PDF.
- Caption hình/bảng được đánh số theo chương.
- Mục lục và danh mục có field để Word cập nhật.

### 6.2 Phần đầu

1. Bìa.
2. Tóm tắt và từ khóa.
3. Mục lục.
4. Danh mục hình.
5. Danh mục bảng.
6. Danh mục thuật ngữ/viết tắt.
7. Phân công công việc.

Thông tin bìa được tách thành cấu hình để người dùng có thể chỉnh sửa.

### 6.3 Nội dung năm chương

#### Chương 1 — Giới thiệu

- Bối cảnh và động lực.
- Phát biểu bài toán chatbot + RAG.
- Thách thức: hallucination, stale data, blind retrieval và mất ngữ cảnh.
- Câu hỏi nghiên cứu.
- Mục tiêu, phạm vi và đóng góp.
- Cấu trúc báo cáo.

#### Chương 2 — Cơ sở lý thuyết

- LLM và giới hạn knowledge cutoff/grounding.
- RAG và evidence-first generation.
- BM25, Dense Retrieval và Hybrid RRF.
- Query understanding, intent và reference resolution.
- Session memory.
- Claim verification và abstention.
- Các metric và công thức.

#### Chương 3 — Phương pháp thực nghiệm

- Tổng quan kiến trúc hệ thống.
- Dữ liệu và EDA.
- Pipeline ingestion/index.
- Pipeline runtime chat.
- Bảy cấu hình retrieval.
- Protocol session evaluation.
- Protocol paired GPT-5.5/DeepSeek.
- Môi trường phần cứng/phần mềm và provenance.

#### Chương 4 — Thực nghiệm và kết quả

- Kết quả retrieval.
- Kiểm định thống kê.
- Kết quả session/context.
- Kết quả grounding và safety.
- So sánh GPT-5.5/DeepSeek.
- Phân tích lỗi, case study và trade-off.
- Cấu hình ứng viên production.

#### Chương 5 — Kết luận và hướng phát triển

- Tổng hợp kết quả đã chứng minh.
- Bài học kiến trúc.
- Hạn chế và threats to validity.
- Công việc tiếp theo.

Cuối báo cáo có tài liệu tham khảo và phụ lục về contract, artifact provenance,
bảng metric chi tiết và lệnh tái lập. Không đưa code source vào Word.

## 7. Luồng dữ liệu sinh artifact

```text
Locked JSON/CSV artifacts
        |
        v
Python loaders + metric helpers
        |
        +--> Matplotlib/Seaborn figures (PNG 300 DPI)
        |
        +--> Notebook tables, outputs and Vietnamese analysis
        |
        +--> Word report tables, figures and narrative
```

Notebook và Word phải dùng chung helper tính metric để không lệch số liệu.

## 8. Xử lý lỗi và dữ liệu thiếu

- Thiếu artifact bắt buộc hoặc sai hash: dừng build.
- Artifact tùy chọn chưa có: không tạo figure giả.
- Metric không có mẫu số: không hiển thị `0%`; ghi trong bảng hạn chế.
- Figure file thiếu: Word build thất bại với tên figure cụ thể.
- Caption không có source/split/n: validation thất bại.
- Word không được sinh nếu notebook/report data model chưa qua preflight.

## 9. Kiểm thử và nghiệm thu

### Notebook

- Chỉ có một file `.ipynb`.
- Chạy sạch từ đầu, không cell lỗi.
- Có ít nhất năm phần lớn theo pipeline.
- Không còn 15 chương lặp cùng khuôn.
- Không còn hình `not_measured` trong nội dung chính.
- Code và output biểu đồ đều hiển thị.
- Không chứa output HTML hoặc Plotly.

### Word

- Mở được bằng Microsoft Word.
- Có bìa, mục lục, danh mục hình/bảng/thuật ngữ, năm chương, tài liệu tham khảo và phụ lục.
- Không chứa source code.
- Mọi hình/bảng đều có caption và được phân tích trong văn bản.
- Số liệu khớp artifact và notebook.
- Render kiểm tra không có chữ/hình bị cắt, bảng tràn trang hoặc heading mồ côi.

### Cleanup

- Không sinh HTML.
- Xóa báo cáo HTML cũ khỏi output hiện hành.
- PDF chỉ được dùng tạm để kiểm tra render Word, không phải artifact bàn giao.
- Thư mục output cuối chỉ giữ Word và các figure PNG cần thiết.

## 10. Tiêu chí hoàn thành

Thiết kế được xem là hoàn thành khi giảng viên có thể đọc từ đầu đến cuối và trả lời:

1. Hệ thống được xây dựng như thế nào?
2. Mỗi thành phần giải quyết vấn đề gì?
3. Dữ liệu và evidence đi qua pipeline ra sao?
4. Thí nghiệm được tổ chức như thế nào?
5. Phương pháp nào tốt hơn theo bằng chứng hiện có?
6. Hệ thống còn thiếu bằng chứng gì trước khi production?

