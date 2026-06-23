# Kịch bản thuyết trình bảo vệ đồ án

**Đề tài:** Xây dựng Chatbot đặt món nhà hàng ứng dụng LLM và RAG
*(Building a Restaurant Food-Ordering Chatbot using LLM and RAG)*
**Môn:** Học máy & Khai phá dữ liệu · **Thời lượng:** ~10 phút · **Slide:** 12 trang
**File slide:** `CMC_RAG_Chatbot_Defense.pptx`

> Cách dùng: mỗi slide có **Lời thoại** (đọc/nói tự nhiên, không học thuộc) và **Ghi chú** (thao tác, chuyển ý). Con số trong ngoặc là thời gian mục tiêu.

---

## Phân bổ thời gian

| Slide | Nội dung | Thời gian | Dồn |
|------:|----------|:---------:|:---:|
| 1 | Mở đầu / Tiêu đề | 0:15 | 0:15 |
| 2 | Đặt vấn đề & Mục tiêu | 0:55 | 1:10 |
| 3 | Góc nhìn Học máy & KPDL | 0:45 | 1:55 |
| 4 | Lựa chọn kỹ thuật & đánh đổi | 1:00 | 2:55 |
| 5 | Kiến trúc hệ thống | 0:45 | 3:40 |
| 6 | Knowledge Base & BM25 | 0:55 | 4:35 |
| 7 | Guardrails — an toàn AI | 0:55 | 5:30 |
| 8 | Output Parser | 0:45 | 6:15 |
| 9 | Evaluation | 0:45 | 7:00 |
| 10 | **Demo trực tiếp** | 1:30 | 8:30 |
| 11 | Hạn chế & hướng phát triển | 0:45 | 9:15 |
| 12 | Kết luận & cảm ơn | 0:20 | 9:35 |

> Chừa ~25 giây đệm. Nếu cháy giờ: rút gọn slide 3 và 8, giữ nguyên demo.

---

## Lời mở đầu (trước slide 1)

> "Em xin kính chào thầy/cô trong hội đồng. Em tên là **[Họ tên]**, hôm nay em xin trình bày đồ án môn Học máy & Khai phá dữ liệu: **Xây dựng chatbot đặt món nhà hàng ứng dụng LLM và RAG**. Bài trình bày gồm: bài toán và mục tiêu, các phương pháp học máy đã dùng, kiến trúc hệ thống, phần đánh giá, và một demo ngắn trên hệ thống thật."

---

## Slide 1 — Tiêu đề (0:15)

**Lời thoại:** "Đề tài tập trung vào một trợ lý hội thoại cho nhà hàng đặt món qua mã QR — vừa trả lời chính xác, vừa an toàn, và quan trọng là **đo lường được** chất lượng."

**Ghi chú:** nói nhanh, không dừng lâu. Chuyển sang slide 2 ngay.

---

## Slide 2 — Đặt vấn đề & Mục tiêu (0:55)

**Lời thoại:** "Nhà hàng cho khách gọi món bằng QR. Khách hỏi rất nhiều và lặp lại: còn món gì, combo nào hợp, bị dị ứng nên tránh gì, mấy giờ mở cửa, thanh toán ra sao. Nhân viên trả lời thủ công thì chậm và thiếu nhất quán. Nếu dùng một chatbot ngây thơ, nó **dễ bịa giá, bịa món, thậm chí tự ý đặt đơn** — đó là rủi ro vận hành thật.

Vì vậy mục tiêu của em gồm bốn điểm: một, chatbot trả lời **dựa trên kho tri thức của chính nhà hàng** và có trích nguồn; hai, **an toàn** — chặn bịa đặt và tuyệt đối không để AI tự đặt đơn; ba, **đánh giá định lượng** bằng bộ câu hỏi chuẩn; bốn, **tích hợp vào hệ thống thật** chứ không chỉ là notebook."

**Ghi chú:** nhấn mạnh cụm "không tự đặt đơn" — đây là điểm chốt xuyên suốt.

---

## Slide 3 — Góc nhìn Học máy & Khai phá dữ liệu (0:45)

**Lời thoại:** "Em xin đặt đồ án trong khung của môn học. Hệ thống dùng bốn nhóm kỹ thuật: **Truy xuất thông tin** với mô hình Okapi BM25 dựa trên TF–IDF; **khai phá dữ liệu văn bản** để tách tài liệu thành các đoạn và dùng ý tưởng luật kết hợp để gợi ý cặp món; **mô hình ngôn ngữ** kiến trúc Transformer để sinh câu trả lời; và **đánh giá mô hình** bằng các chỉ số khách quan. Đây đều là nội dung cốt lõi của Học máy và Khai phá dữ liệu."

**Ghi chú:** chỉ tay lần lượt 4 thẻ. Đừng đi sâu — slide sau sẽ giải thích từng phần.

---

## Slide 4 — Lựa chọn kỹ thuật & Đánh đổi (1:00)

**Lời thoại:** "Có hai quyết định thiết kế quan trọng.

Thứ nhất, **RAG thay vì fine-tuning**. Dữ liệu nhà hàng — menu, giá, chính sách — thay đổi liên tục. RAG cho phép **cập nhật tức thì** chỉ bằng cách sửa kho tri thức, **không phải huấn luyện lại**, lại **trích được nguồn** nên minh bạch và chống bịa. Fine-tuning thì tốn dữ liệu, tốn GPU và khó cập nhật.

Thứ hai, **BM25 thay vì embeddings**. Kho tri thức của em nhỏ, chỉ 35 đoạn. Ở quy mô này, thống kê từ khóa của BM25 đã đủ chính xác, lại **không cần model embedding hay vector database**, minh bạch và dễ giải thích. Tiếng Việt được xử lý bằng chuẩn hóa bỏ dấu. Embeddings sẽ làm nặng hạ tầng mà lợi ích thêm rất nhỏ."

**Ghi chú:** đây là slide hay bị hỏi nhất — nói chậm, rõ. Xem mục Q&A 1 & 2.

---

## Slide 5 — Kiến trúc hệ thống (0:45)

**Lời thoại:** "Về kiến trúc: khách dùng **giao diện chat React** sau khi quét QR. Yêu cầu đi qua **backend .NET** — nơi giữ vai trò xác thực đơn. Phần thông minh nằm ở **dịch vụ AI viết bằng Python**, gồm RAG cộng LLM, đọc từ **kho tri thức 7 tài liệu, 35 đoạn**. Mô hình ngôn ngữ là **Gemini 3.1 Pro** gọi qua một gateway chuẩn OpenAI.

Mỗi câu hỏi đi qua pipeline ở dưới: guardrails đầu vào, BM25 truy xuất 5 đoạn liên quan, dựng prompt, LLM sinh JSON, output parser kiểm duyệt, rồi mới trả gợi ý cho khách xác nhận."

**Ghi chú:** lướt theo mũi tên trái → phải, rồi chỉ vào dòng pipeline.

---

## Slide 6 — Knowledge Base & BM25 (0:55)

**Lời thoại:** "Kho tri thức gồm **7 file Markdown** được tách thành **35 đoạn**, nội dung là menu, combo, chính sách đặt món, dị ứng, FAQ. Mỗi đoạn có tiêu đề và nhãn chủ đề.

Bộ truy xuất dùng **Okapi BM25** với tham số chuẩn: k1 bằng 1.5 điều chỉnh độ bão hòa tần suất từ, b bằng 0.75 chuẩn hóa theo độ dài đoạn. Em **tăng trọng số 1.5 lần** khi từ khóa khớp ở tiêu đề, và lấy **5 đoạn** đưa vào ngữ cảnh. Toàn bộ văn bản được **chuẩn hóa bỏ dấu** trước khi đánh chỉ mục, nên dù khách gõ có dấu hay không dấu vẫn khớp tốt."

**Ghi chú:** không cần đọc hết công thức — nêu ý nghĩa tham số là đủ.

---

## Slide 7 — Guardrails (0:55)

**Lời thoại:** "An toàn là phần em đầu tư nhiều nhất, gồm **7 cờ**. Năm cờ ở đầu vào: phát hiện ý định **đặt đơn** để bắt xác nhận, chặn đòi **bịa giá**, chặn đòi **món ngoài thực đơn**, phát hiện **lạc chủ đề**, và phát hiện **ngôn từ xúc phạm**. Hai cờ hệ thống: khi LLM trả **sai cấu trúc JSON** thì chặn cứng đầu ra, và khi **LLM lỗi hoặc timeout** thì hệ thống rơi về chế độ chỉ-RAG an toàn thay vì sập.

Và đây là nguyên tắc cốt lõi của cả đồ án:" *(chỉ vào banner)* "**AI không bao giờ tự đặt đơn**. Trường `requires_customer_confirmation` luôn bằng true — khách bắt buộc phải tự bấm xác nhận."

**Ghi chú:** dừng 1 nhịp ở banner cho hội đồng đọc.

---

## Slide 8 — Output Parser (0:45)

**Lời thoại:** "Đầu ra của LLM không được tin tuyệt đối, nên đi qua 5 bước kiểm duyệt: **trích JSON**; **kiểm tra schema** — nếu danh sách gợi ý sai kiểu thì gắn cờ và chặn; **đối chiếu menu** — chỉ giữ món có mã hợp lệ và còn bán, món bịa bị loại; **chuẩn hóa số lượng** về khoảng 1 đến 20; và **ép xác nhận**. Cuối cùng, **backend .NET vẫn kiểm tra lại toàn bộ đơn** trước khi ghi cơ sở dữ liệu — AI chỉ gợi ý, không có quyền ghi."

**Ghi chú:** nhấn "AI không có quyền ghi DB" — bổ trợ cho slide 7.

---

## Slide 9 — Evaluation (0:45)

**Lời thoại:** "Em đánh giá bằng **15 câu hỏi chuẩn** phủ các tình huống: gợi ý món, FAQ, dị ứng, chính sách, và các ca guardrail. Ba chỉ số: **Retrieval Hit@5** — BM25 có lấy đúng nguồn kỳ vọng không, đạt **11/14**, khoảng 78.6%; **Guardrail Accuracy** — nhận đúng cờ an toàn, **4/4**, 100%; và **Overall Pass** tổng thể **12/15**, 80%. Các con số này được **tính tự động ngay trong notebook**, không phải nhập tay."

**Ghi chú:** chỉ vào cột biểu đồ tương ứng khi đọc số. Nếu hỏi vì sao retrieval không phải 100% → Q&A 5.

---

## Slide 10 — DEMO TRỰC TIẾP (1:30)

> **Chuẩn bị trước khi vào phòng:** mở sẵn hệ thống (frontend + backend + dịch vụ AI) và một tab chat trắng. Có sẵn ảnh chụp màn hình dự phòng phòng khi mạng lỗi.

**Lời thoại mở:** "Em xin demo nhanh trên hệ thống đang chạy thật."

**Kịch bản 4 ca (làm tuần tự, mỗi ca ~20 giây):**

1. **Gợi ý món** — gõ: *"Gợi ý món cho 2 người ăn trưa"*.
   → Nói: "AI gợi ý món **từ menu thật**, hiện card kèm **nút xác nhận** — nó không tự thêm vào giỏ."
2. **Hỏi đáp FAQ** — gõ: *"Nhà hàng mở cửa mấy giờ? Thanh toán thế nào?"*
   → Nói: "Trả lời lấy đúng từ tài liệu FAQ trong kho tri thức."
3. **Dị ứng** — gõ: *"Tôi bị dị ứng hải sản, nên tránh món nào?"*
   → Nói: "Hệ thống tra tài liệu dị ứng và **cảnh báo đúng món** cần tránh."
4. **Guardrail** — gõ: *"Hôm nay thời tiết thế nào?"*
   → Nói: "Câu lạc chủ đề bị cờ **OUT_OF_SCOPE** chặn và **kéo khách về** chuyện gọi món."

**Lời thoại chốt:** "Như vậy đủ bốn năng lực chính: gợi ý đúng dữ liệu, hỏi-đáp, cảnh báo an toàn, và chặn lạc đề."

**Ghi chú:** nếu mạng/LLM lỗi → nói "hệ thống rơi về chế độ RAG-only" (đúng như slide 7) rồi dùng ảnh dự phòng. Không sửa code trước hội đồng.

---

## Slide 11 — Hạn chế & Hướng phát triển (0:45)

**Lời thoại:** "Em cũng thẳng thắn về hạn chế: kho tri thức còn **nhỏ** nên kết quả chưa đại diện quy mô lớn; bộ 15 câu do **một mình em gán nhãn** nên có thiên lệch; khi không có API thì đánh giá chạy ở **chế độ fallback**, chưa phản ánh đầy đủ chất lượng LLM; và BM25 dựa từ khóa nên **chưa hiểu ngữ nghĩa sâu**.

Hướng phát triển: kết hợp **BM25 với embeddings** (hybrid + semantic rerank), đo **faithfulness bằng RAGAS**, thêm **streaming và bộ nhớ hội thoại**, **tự đồng bộ kho tri thức** từ database menu, và **mở rộng bộ đánh giá** với nhiều người gán nhãn."

**Ghi chú:** nói tự tin — thể hiện tư duy phản biện chứ không phải xin lỗi.

---

## Slide 12 — Kết luận & Cảm ơn (0:20)

**Lời thoại:** "Tóm lại: đồ án xây dựng một chatbot RAG **bám sát dữ liệu nhà hàng**, **an toàn nhiều lớp** với guardrails và output parser, AI không tự đặt đơn; có **đánh giá định lượng minh bạch** và **tích hợp vào hệ thống thật**. Em xin cảm ơn thầy/cô đã lắng nghe và rất mong nhận được câu hỏi, góp ý ạ."

**Ghi chú:** dừng, mỉm cười, sẵn sàng Q&A.

---

## Chuẩn bị Q&A (câu hỏi thường gặp)

**1. Vì sao chọn RAG mà không fine-tune model?**
Dữ liệu nhà hàng đổi liên tục (giá, món, chính sách). RAG cập nhật bằng cách sửa KB, không cần train lại, trích được nguồn nên minh bạch và chống bịa. Fine-tune tốn dữ liệu/GPU và mỗi lần đổi menu phải train lại.

**2. Vì sao BM25 mà không dùng embeddings / vector DB?**
Ở quy mô 35 đoạn, BM25 (thống kê từ khóa) đã đủ chính xác, không cần GPU hay hạ tầng vector, lại minh bạch dễ giải thích. Embeddings phù hợp khi KB lớn và nhiều cách diễn đạt đồng nghĩa — em để ở hướng phát triển (hybrid).

**3. Làm sao chống chatbot bịa giá / bịa món (hallucination)?**
Ba lớp: (a) guardrails đầu vào chặn yêu cầu bịa; (b) prompt buộc chỉ dùng dữ liệu truy xuất; (c) output parser đối chiếu **mã món trong menu thật** — món/giá không khớp bị loại. Giá cuối cùng do backend quyết, không lấy từ lời LLM.

**4. Làm sao đảm bảo AI không tự đặt đơn cho khách?**
AI chỉ trả về *gợi ý* với `requires_customer_confirmation = true` (luôn). Frontend bắt khách bấm xác nhận; backend .NET mới là nơi tạo đơn và kiểm tra lại toàn bộ. AI **không có quyền ghi** database.

**5. Vì sao Retrieval Hit@5 chỉ 78.6%, không phải 100%?**
3 câu trượt rơi vào trường hợp thông tin trải ở nhiều tài liệu hoặc cách diễn đạt khác từ khóa trong KB — đúng hạn chế của BM25 thuần từ khóa. Đây là lý do hướng phát triển đề xuất hybrid retrieval.

**6. Bộ đánh giá chạy khi không có API thì có đáng tin không?**
Retrieval và guardrail **không phụ thuộc LLM** nên số liệu hai phần đó là thật và lặp lại được. Overall có phần phụ thuộc LLM; em đã ghi rõ trong mục "threats to validity".

**7. Hệ thống xử lý tiếng Việt thế nào?**
Chuẩn hóa Unicode + bỏ dấu + lowercase trước khi đánh chỉ mục và khi so khớp, nên khách gõ có dấu/không dấu đều khớp. Các mẫu guardrail cũng viết trên dạng đã bỏ dấu.

**8. Nếu LLM sập / quá tải thì sao?**
Cờ `AI_PROVIDER_UNAVAILABLE` kích hoạt fallback **RAG-only**: vẫn trả thông tin truy xuất được từ KB kèm trích nguồn, thay vì lỗi trắng. Hệ thống không sập.

**9. Đâu là đóng góp về mặt Học máy / Khai phá dữ liệu?**
Áp dụng và **so sánh có lập luận** IR (BM25) với hướng embeddings; tách & biểu diễn văn bản; ý tưởng luật kết hợp cho gợi ý cặp món; và một **khung đánh giá định lượng** (golden set + 3 chỉ số) — đúng quy trình của môn.

**10. Khác gì so với gọi thẳng ChatGPT?**
Chatbot thuần LLM không biết menu/giá thật và dễ bịa. Hệ thống của em **neo câu trả lời vào dữ liệu nhà hàng** (RAG), thêm guardrails + kiểm duyệt đầu ra + chốt ở backend — phù hợp môi trường vận hành thật.

---

## Mẹo trình bày

- Tập nói to thành tiếng **2–3 lần** bấm giờ; mục tiêu 9:30–10:00.
- Thuộc **ý**, không thuộc **chữ**. Mỗi slide nhớ 1 câu chốt.
- Demo: mở sẵn mọi thứ, có **ảnh dự phòng**; tuyệt đối không gỡ lỗi trước hội đồng.
- Khi bí câu hỏi: "Đây là điểm hay, trong phạm vi đồ án em xử lý theo hướng… và em xem [X] là hướng mở rộng."
- Giữ nhịp chậm ở slide 4, 7 (hay bị hỏi); lướt nhanh slide 1, 3.
