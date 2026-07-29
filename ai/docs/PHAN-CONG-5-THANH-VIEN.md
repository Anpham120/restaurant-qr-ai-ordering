# Phân công 5 thành viên — chia theo dây chuyền xây dựng

## Ý tưởng: mỗi người một khâu, đầu ra khâu này là đầu vào khâu sau

Hệ thống này được xây theo 8 bước, và **thứ tự đó chính là phương pháp** (xem `ai/README.md`).
Chia việc theo đúng dây chuyền đó có ba lợi ích:

1. Mỗi người **hiểu sâu một khâu** thay vì biết mơ hồ cả hệ thống.
2. Mỗi khâu có **đầu ra kiểm được**, nên bàn giao là bàn giao một thứ đo được, không phải "em
   làm xong rồi".
3. **Báo cáo tự chia theo người**: notebook có 6 phần, mỗi người viết đúng phần khâu mình.

```
TV1              TV2              TV3              TV4              TV5
Bài toán    →   Đánh giá    →   Trả lời     →   Tri thức    →   An toàn
& Dữ liệu       & Thước đo      tất định         & RAG            & Tích hợp
bước 0–1        bước 2–3        bước 4           bước 5–6         bước 7 + dịch vụ
Phần I          Phần II         Phần III         Phần IV          Phần V–VI
```

## Cái giá của dây chuyền, và cách khắc phục

Dây chuyền thuần có một nhược điểm thật: **TV5 ngồi chờ TV1–TV4**. Nếu không xử lý thì bốn
người làm ba tuần rồi người thứ năm mới bắt đầu.

Cách khắc phục: **mỗi người bắt đầu bằng việc viết tiêu chí kiểm chứng cho khâu mình.** Tiêu chí
đến từ *định nghĩa khâu*, không từ mã người trước — nên viết được ngay từ ngày đầu.

| TV | Tuần 1 (làm ngay, không chờ) | Tuần 2+ (cần đầu vào) |
|---|---|---|
| 1 | rà lại từ điển nhãn, viết nội dung tri thức | — |
| 2 | viết ca đánh giá cho khâu mình + kịch bản đa lượt | chạy thước đo trên hệ thống thật |
| 3 | thẻ giỏ hàng và bộ nhớ phiên (mã hiện có đã đủ để làm) | chỉnh theo ca của TV2 |
| 4 | dựng BM25 + hybrid trên **đoạn giả** theo định dạng đã chốt | đổi sang đoạn thật của TV1 |
| 5 | `/health`, `/ready`, xác thực token, hợp đồng schema | nối `/v1/chat` khi TV3 xong |

Nói cách khác: **dây chuyền cho phần nội dung, song song cho phần kiểm chứng.**

---

# TV1 — Bài toán & Dữ liệu (bước 0–1)

### Câu hỏi khâu này trả lời
*AI được phép trả lời gì, dữ liệu có gì, và khi một nhãn không có mặt thì kết luận được gì?*

### Kiến thức phải nắm
- Phân loại ba loại câu hỏi (A tra cứu / B tri thức / C phán đoán) và vì sao **loại A không
  được để mô hình sinh trả lời**.
- Rút dấu tiếng Việt là phép **mất thông tin**. Bảy lỗi bản cũ đều từ đây.
- **Độ phủ nhãn quyết định lọc được hay không**: nhóm phủ 91/91 thì thiếu nhãn là lỗi dữ liệu;
  nhóm không phủ hết thì thiếu nhãn là *chưa ghi nhận*, **không** phải *không có*.

### Việc còn lại

> **Đã xong** — xem `ai/docs/05-knowledge-base.md`. Kho hiện có **84 tài liệu /
> 327 đoạn** trong MỘT kho, hai chế độ trả lời (24 `verbatim` + 60 `synthesize`; 56 sinh từ
> thực đơn, 28 người viết). Việc của TV1 nay là **đọc để hiểu và bảo vệ**, và mở rộng thêm khi
> có nhu cầu thật.

Nếu cần thêm tài liệu:
1. Thêm nhóm nhãn vào `DERIVED_GROUPS` trong `build_knowledge.py` — nhưng chỉ khi nhóm đó có câu
   hỏi mà **lớp tra khóa không trả lời được**.
2. Thêm tài liệu người viết vào `ai/knowledge/written/`, bắt buộc `audience: guest`.
3. Chạy lại `build_knowledge.py` và xác nhận 112 ca không tụt.

### Sở hữu tệp
`ai/knowledge/*` · `ai/scripts/build_knowledge.py` ·
`build_tag_dictionary.py` · `audit_allergen_tags.py` · `backend/data/menu-tags.json`

### Tự đo bằng
```bash
python ai/scripts/build_knowledge.py --check
python ai/scripts/build_tag_dictionary.py --check
python ai/scripts/audit_allergen_tags.py
python -m unittest test_chunker test_packaging   # trong ai/app
```

### Bàn giao cho TV2
Định dạng đoạn, **chốt ngay tuần 1** để TV2 và TV4 không phải chờ:
```python
KnowledgeChunk(chunk_id="{doc_id}#{i}", doc_id=..., title=..., topic_keys=[...], text=..., source="derived|demo")
```

### Viết Phần I của notebook
Bài toán, ba loại câu hỏi, từ điển dữ liệu, bảy vụ đụng chữ, độ phủ nhãn.

---

# TV2 — Đánh giá & Thước đo (bước 2–3)

### Câu hỏi khâu này trả lời
*Làm sao biết hệ thống trả lời đúng hay sai — và làm sao biết thước đo của mình đúng?*

### Kiến thức phải nắm
Đây là khâu chứa bài học đắt nhất của dự án: **thước đo sai 3 lần trước khi hệ thống sai**, và
một lỗ trong thước đo làm con số 0,9960 tụt xuống 0,7368 khi bịt lại.

- **Khóa đáp án là truy vấn, không phải danh sách.** Danh sách viết tay thì không có cách nào
  kiểm — bản cũ có 96 khóa trỏ sai chỗ suốt nhiều tháng.
- **Test hai chiều.** Một thước đo chỉ có test "bắt được lỗi" thì qua được bằng cách chấm đỏ mọi
  thứ. Phải có cả test "câu trả lời tốt phải xanh".
- **Ba nhóm, không phải hai.** Ca an toàn là *chốt*, không phải số liệu — đưa vào tập phát triển
  thì tỷ lệ chung che mất một ca dị ứng đỏ.
- **Bộ dò lỗ** tìm lỗi *chưa nghĩ tới*: đưa câu trả lời chắc chắn tệ qua toàn bộ tập ca.

### Việc còn lại
1. **~25 kịch bản đa lượt** (`session_scripts.json`) đo bộ nhớ phiên — 112 ca hiện có đều một
   lượt nên không đo được ngữ cảnh. Bốn nhóm: dị ứng phải nhớ (chốt an toàn), ghi đè ràng buộc,
   không lặp món, tham chiếu ngược.
2. **~120 ca đánh giá truy hồi** cho TV4, khóa đáp án là điều kiện chọn.
3. Mở rộng thước đo: 4 phép kiểm giỏ hàng + chốt `safety_cart_no_allergen`.

### Sở hữu tệp
`ai/evaluation/cases.json` · `session_scripts.json` · `retrieval_cases.json` ·
`answer_metric.py` · `menu_selectors.py` · `validate_cases.py` · `build_split.py` ·
`probe_metric_holes.py` · `test_answer_metric.py`

### Tự đo bằng
```bash
python ai/evaluation/validate_cases.py
python ai/evaluation/build_split.py --check
python ai/evaluation/probe_metric_holes.py
python -m unittest discover -s ai/evaluation -p "test_*.py"
```

### Bàn giao cho TV3
Tập ca + thước đo. TV3 chạy `run_baseline.py` và biết ngay mình đúng bao nhiêu.

### Viết Phần II của notebook
Tập đánh giá, khóa đáp án dạng truy vấn, chia ba nhóm, thước đo hai chiều, bộ dò lỗ.

---

# TV3 — Trả lời tất định (bước 4)

### Câu hỏi khâu này trả lời
*Bao nhiêu câu trả lời được mà KHÔNG cần mô hình sinh?*

### Kiến thức phải nắm
- **Số nền** là mốc để mọi thứ sau so vào. Bản cũ chỉ 33% câu trả lời do mã tất định sinh, và
  không ai biết vì sao.
- **Khớp cụm dài trước, rồi ăn hết đoạn đã khớp.** Cơ chế này chặn 96 chỗ đụng chữ (32 cụm nằm
  trong cụm khác, 90 cụm nằm trong tên món).
- **Ràng buộc khác ngữ cảnh.** "Tôi ăn chay" là ràng buộc (lọc cứng); "tôi đi hẹn hò" là ngữ
  cảnh (chỉ sắp thứ tự). Lẫn hai thứ thì câu hẹn hò chỉ còn **đúng một món**.
- **Fail-closed cho dị nguyên**: không bao giờ nới, kể cả khi kết quả rỗng.

### Việc còn lại
1. **Thẻ giỏ hàng** (`ai/app/cart.py`), 5 bất biến: món phải tồn tại và giá lấy từ thực đơn;
   `requires_customer_confirmation` luôn `true`; món bị `avoid_tags` loại **không bao giờ** vào
   thẻ; chỉ sinh thẻ ở nhánh `filter`/`compare`/`item_detail`; `reason` nêu **ràng buộc đã
   thỏa** chứ không phải câu quảng cáo.
2. **Bộ nhớ phiên** (`ai/app/session.py`), ba quy tắc hợp nhất khác nhau:

   | Loại | Quy tắc | Vì sao |
   |---|---|---|
   | dị nguyên | **cộng dồn, không bao giờ bỏ** | khai ở lượt 1 thì lượt 5 vẫn phải nhớ |
   | ràng buộc cứng | lượt mới **ghi đè** cùng nhóm | "rẻ hơn nữa" phải thay ngân sách cũ |
   | ngữ cảnh | cộng vào, giữ 5 gần nhất | tích lũy nhưng không phình vô hạn |

   **Rolling summary sinh tất định**, không nhờ mô hình — bộ nhớ sai thì sai suốt phiên.
3. Mở rộng từ vựng cho các `topic_keys` TV1 thêm.

### Sở hữu tệp
`ai/app/understand.py` · `answer.py` · `cart.py` · `session.py` · `test_understand.py`

### Tự đo bằng
```bash
python ai/evaluation/run_baseline.py --all      # trả mã khác 0 nếu có lỗi an toàn
python ai/evaluation/run_ablation.py            # cơ chế nào thật sự có giá trị
python -m unittest discover -s ai/app -p "test_*.py"
```

### Bàn giao cho TV4
Hợp đồng `Reply` — **hình dạng hiện có, không đổi**, chỉ thêm trường `cart`:
```python
Reply(text=..., items=[...], kind=..., asks_back=..., branch=..., cart=[...])
```

### Viết Phần III của notebook
Số nền, 6 nhánh trả lời, ablation từng cơ chế, ràng buộc vs ngữ cảnh, một cơ chế bị bỏ vì gây hại.

---

# TV4 — Tri thức & RAG (bước 5–6)

### Câu hỏi khâu này trả lời
*Câu chính sách lấy dữ liệu ở đâu, và phương pháp truy hồi nào tốt hơn?*

### Kiến thức phải nắm
- **BM25**: xếp hạng theo tần suất từ, có chuẩn hóa độ dài tài liệu. `k1=1.5`, `b=0.75`. Mạnh ở
  câu có tên riêng, yếu ở câu diễn đạt khác từ.
- **Embedding**: vector ngữ nghĩa, so bằng cosine. Mạnh ở diễn đạt khác từ, yếu ở tên riêng và
  **không hiểu số**.
- **Hybrid RRF**: `RRF(d) = Σ 1/(k + rank_r(d))` với `k=60`. Gộp theo **thứ hạng** chứ không theo
  điểm, nên không cần chuẩn hóa hai thang điểm khác nhau.
- **Chỉ số**: Hit@1, Hit@5, MRR@5, nDCG@5, và **forbidden@5** — cái cuối quan trọng nhất vì nó
  đo việc trích sai chủ đề.

### Việc còn lại
1. Ba phương pháp cùng một giao diện `search(query, k) -> list[RetrievedChunk]`.
2. **So trên HAI bài toán, không phải một** — đây là điểm mạnh nhất của phần nghiên cứu:

   | Bài toán | Ứng viên | Kỳ vọng |
   |---|---|---|
   | truy hồi tri thức | BM25 / embedding / hybrid | hybrid tốt nhất |
   | **chọn món** | BM25 / embedding / **lọc theo nhãn** | lọc theo nhãn thắng dứt khoát |

   Bài toán thứ hai chứng minh bằng số rằng **không phải chỗ nào cũng nên dùng RAG**: câu "món
   nào dưới 50.000đ" thì BM25 và embedding không hiểu số, còn lọc theo `price` đúng 100%.
3. Ablation: tắt rút dấu cho BM25, tắt chuẩn hóa vector cho embedding.

### Sở hữu tệp
`ai/app/rag/*` · `ai/evaluation/run_retrieval_comparison.py` · `ai/app/llm_understand.py`

### Tự đo bằng
```bash
python ai/evaluation/run_retrieval_comparison.py
python ai/evaluation/run_with_model.py         # trả mã khác 0 nếu mô hình làm tụt ca nào
```

### Bàn giao cho TV5
Kết quả truy hồi + trạng thái nạp model cho `/ready`.

### Viết Phần IV của notebook
Ba phương pháp, công thức, bảng so sánh, ablation, và kết luận về khi nào KHÔNG nên dùng RAG.

---

# TV5 — An toàn & Tích hợp (bước 7 + dịch vụ)

### Câu hỏi khâu này trả lời
*Điều gì tuyệt đối không được sai, và làm sao khách thật dùng được?*

### Kiến thức phải nắm
- **An toàn không được phụ thuộc mô hình sinh.** Đây là phát hiện quan trọng nhất của dự án:
  hai ca dị ứng từng chỉ mô hình cứu được, tức proxy chết là **mất bảo vệ dị ứng**. Đã đưa về
  mã tất định.
- **Fail-closed** khác **fail-open**: thiếu nhãn dị nguyên thì loại món (fail-closed); thiếu
  nhãn độ cay thì không kết luận (nhưng nhóm này phủ 91/91 nên không xảy ra).
- **Ranh giới quyền**: AI không tự tạo đơn. Backend đã cưỡng chế — `ApplyAiSessionUpdates` bỏ
  qua mọi trạng thái "đã thêm vào giỏ" mà AI khai.

### Việc còn lại
1. **Dịch vụ HTTP** (`ai/app/service.py`): `/health`, `/ready`, `/v1/chat`, `/v1/chat/stream`,
   `/v1/cache/invalidate`, xác thực `AI_INTERNAL_TOKEN`.
2. **Hợp đồng** `ai/contracts/ai-chat-v1.schema.json` — viết nó **tự bật lại** phép kiểm có điều
   kiện trong `AiContractBoundaryTests.cs`.
3. Gọn payload backend (`ChatAiProvider.cs`: 24 trường → ~10).
4. **Công cụ phân tích nguyên nhân sai** (`analyze_failures.py`), 6 lớp nguyên nhân — và lớp
   quan trọng nhất là `criterion_too_strict`: **ca viết sai, không phải hệ thống sai**.
5. Notebook Phần V–VI + hợp nhất số liệu toàn dự án.

### Sở hữu tệp
`ai/app/service.py` · `ai/contracts/*` · `ai/evaluation/analyze_failures.py` ·
`ai/notebooks/*` · `.github/workflows/ci.yml` · `deploy/docker-compose.yml` ·
`backend/src/.../Chat/ChatAiProvider.cs`

### Tự đo bằng
```bash
python -m unittest discover -s ai/app -p "test_service*.py"
python ai/evaluation/analyze_failures.py
python ai/notebooks/build_teaching_notebook.py --check
dotnet test backend/RestaurantQrAiOrdering.sln
```

### Điều kiện chấp nhận — không thay được bằng test
`docker compose up` → quét QR → hỏi 5 câu gồm một câu khai dị ứng → thẻ giỏ hiện đúng và thêm
được vào giỏ → hỏi tiếp **không nhắc lại dị ứng**, xác nhận vẫn được bảo vệ → đóng phiên, mở
lại, xác nhận **bộ nhớ đã mất**.

### Viết Phần V–VI của notebook
Mô hình sinh chỉ để hiểu chứ không để chọn, chốt an toàn, kết quả tổng hợp, hạn chế, hướng phát triển.

---

## Ba điều cấm chung — ai vi phạm cũng làm CI đỏ

| Cấm | Vì sao | Cưỡng chế bởi |
|---|---|---|
| Nới lỏng lọc dị nguyên, kể cả khi kết quả rỗng | thà nói "không có món phù hợp" còn hơn mời món gây dị ứng | `run_baseline.py` trả mã khác 0 |
| Để mô hình sinh **chọn** món hoặc **nêu** giá | mô hình không tất định; chọn món và giá phải tra bảng | `test_llm_understand.py`, 19 test bất biến |
| Sửa tay tệp do script sinh | dữ liệu lệch khỏi bộ sinh mà không ai biết | các bước `--check` trong CI |

## Quy tắc sở hữu tệp

Chỉ người sở hữu được sửa tệp trong cột "Sở hữu tệp". Cần đổi tệp của người khác thì **nhắn
họ**, không tự sửa. Đây là quy tắc chống xung đột git, và cũng chống việc hai người sửa cùng một
chỗ theo hai hướng ngược nhau.

## Mỗi tuần báo đúng ba dòng

```
TV3 — tuần 2
  số đo: run_baseline.py --all -> 104/112 (tuần trước 101/112), 0 lỗi an toàn
  làm được: thẻ giỏ + 5 test bất biến; bộ nhớ dị nguyên cộng dồn
  đang vướng: chưa rõ "món khác đi" nên bỏ bao nhiêu món đã gợi ý — cần TV2 viết ca
```

Dòng **số đo** bắt buộc và phải là con số chạy được. Bài học đắt nhất của dự án này là *thước đo
sai 3 lần trước khi hệ thống sai*, nên "cảm giác đã tốt hơn" không tính là tiến độ.

## Ba tài liệu ai cũng phải đọc trước khi bắt đầu

1. **`ai/README.md`** — 5 nguyên tắc. Quan trọng nhất: *rút dấu để khớp cách khách gõ, không để
   quyết định nội dung*.
2. **`ai/docs/00-problem-statement.md`** — ba điều AI tuyệt đối không làm.
3. **`ai/docs/01-data-dictionary.md` mục 5** — **thiếu nhãn nghĩa là gì**. Chỗ dễ gây lỗi an
   toàn nhất: nhóm `allergen` chỉ phủ 44/91 món, nên món không có nhãn **không** có nghĩa là
   không chứa.
