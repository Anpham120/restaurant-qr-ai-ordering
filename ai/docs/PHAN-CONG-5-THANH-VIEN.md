# Phân công 5 thành viên

## Cách chia: một người làm NỀN TẢNG, bốn người làm bốn khâu của pipeline

```
        ┌──────────────────────────────────────────────────────────────┐
        │  TV1  NỀN TẢNG — dữ liệu & đo lường                          │
        │  kho tri thức · từ điển nhãn · tập đánh giá · thước đo        │
        │  KHÔNG phải một chặng runtime: mọi khâu DÙNG nó, không đi qua │
        └──────────────────────────────────────────────────────────────┘
                 │ cung cấp dữ liệu và tiêu chí cho cả 4 khâu dưới
                 ▼
khách quét QR, gõ một câu
        │
   ┌────▼──────────────────────────────────────────┐
   │ TV5  CỔNG VÀO & PHIÊN                         │  service.py · session.py
   │      nhận HTTP, xác thực, NẠP bộ nhớ phiên    │
   └────┬──────────────────────────────────────────┘
        │  ChatTurn(question, session_state)
   ┌────▼──────────────────────────────────────────┐
   │ TV2  HIỂU CÂU HỎI                             │  understand.py · llm_understand.py
   │      câu này ràng buộc gì?                    │
   └────┬──────────────────────────────────────────┘
        │  Request
   ┌────▼──────────────────────────────────────────┐
   │ TV3  TRUY HỒI                                 │  rag/bm25.py · embedding.py · hybrid.py
   │      câu này cần đoạn tri thức nào?           │
   └────┬──────────────────────────────────────────┘
        │  Evidence
   ┌────▼──────────────────────────────────────────┐
   │ TV4  CHỌN MÓN & GIỎ HÀNG                      │  answer.py · cart.py
   │      món nào thỏa? thẻ giỏ nào?               │
   └────┬──────────────────────────────────────────┘
        │  Reply + Cart
   ┌────▼──────────────────────────────────────────┐
   │ TV5  GHI bộ nhớ phiên, trả JSON cho backend   │
   └───────────────────────────────────────────────┘
```

### Vì sao cách chia này đúng hơn hai cách trước

Dự án đã thử hai cách, và cả hai đều có một chỗ gãy:

| Cách | Chỗ gãy |
|---|---|
| chia theo **thứ tự dựng** | TV5 ngồi chờ TV1–TV4; TV1 xong sớm rồi rảnh |
| chia **thuần pipeline** | dữ liệu và đo lường **không phải chặng runtime**, phải gửi vào các khâu → TV phụ trách truy hồi gánh cả nội dung kho, tức **hai nền kiến thức** |

Cách hiện tại sửa đúng chỗ gãy thứ hai: **gom dữ liệu và đo lường thành một vai riêng (TV1)**, rồi
bốn người còn lại nhận bốn khâu runtime thuần. Nhờ vậy:

- **TV3 chỉ làm truy hồi**, không phải soạn nội dung kho → một nền kiến thức, không phải hai.
- **Đo lường có tên**, không thành "việc chung". Nếu mỗi người tự chấm phần mình thì đó đúng bệnh
  bản cũ: 8 đường xử lý đều "chạy đúng" theo người viết chúng, không ai đo cả hệ thống, và **thước
  đo sai 3 lần trước khi hệ thống sai**.
- **Bốn khâu runtime chạy song song** ngay từ ngày 1, vì giao diện chốt trước.

### Cái giá phải biết trước

**TV1 nằm trên đường tới hạn của hai người.** TV3 không đo được phép so truy hồi trước khi TV1 xong
~120 ca truy hồi; TV5 không đo được bộ nhớ phiên trước khi TV1 xong ~25 kịch bản đa lượt. Nên thứ
tự trong tuần 1 của TV1 là: **ca đánh giá trước, mở rộng kho sau.**

**Tải việc không đều.** TV2 gần như đã xong (hiểu câu hỏi đạt 0 lỗi an toàn), còn TV3 và TV5 phải
xây từ số không. TV2 nên nhận thêm: hỗ trợ TV5 phần hợp nhất bộ nhớ (vì quy tắc hợp nhất đọc và ghi
vào chính `Request` mà TV2 sở hữu).

---

## Giao diện đã chốt — đọc trước khi viết dòng mã nào

Năm hợp đồng dưới đây **chốt ngay tuần 1** và không đổi mà không thông báo. Chúng là điều kiện để 4
khâu runtime làm song song: ai cũng biết mình nhận gì và phải trả gì, nên viết được ngay cả khi khâu
trước chưa xong (dùng dữ liệu giả theo đúng hình dạng).

```python
# TV5 -> TV2
ChatTurn(question: str, session_state: SessionState | None)

# TV2 -> TV3  (hình dạng HIỆN CÓ, không đổi)
Request(text, folded, require_tags, prefer_tags, avoid_tags, budget_max, budget_strict,
        categories, wants, named_items, policy_topic, asks_price, asks_allergy,
        asks_extreme, is_comparison, off_topic, unparsed_restriction, ...)

# TV3 -> TV4
Evidence(verbatim: str | None,            # tài liệu answer_mode=verbatim, trả NGUYÊN VĂN
         chunks: list[KnowledgeChunk])    # tài liệu answer_mode=synthesize, cho mô hình đọc

# TV4 -> TV5
Reply(text, items, kind, asks_back, branch, notes, cart: list[CartAction])
CartAction(menu_item_id, name, quantity, reason, evidence_ids,
           requires_customer_confirmation=True)   # LUÔN True, không nhánh nào đặt False

# TV1 cung cấp cho tất cả
KnowledgeChunk(chunk_id, doc_id, title, heading, topic_keys, source, answer_mode, text)
cases.json + answer_metric.score(case, answer, menu, named) -> Verdict
```

Ai cần đổi một trong các hợp đồng này thì **nhắn cả nhóm trước khi sửa**.

---

# TV1 — Nền tảng: dữ liệu & đo lường

### Câu hỏi khâu này trả lời
*AI được phép nói gì, dựa vào dữ liệu nào — và làm sao biết câu trả lời đúng hay sai?*

### Vì sao hai việc này thuộc cùng một người
Chúng giống nhau ở điểm quan trọng nhất: **cả hai đều không phải chặng runtime, và cả hai đều là
thứ mọi khâu khác đo dựa vào.** Tách chúng ra thì hoặc chúng bị gửi vào các khâu (và người nhận
gánh thêm một nền kiến thức lạ), hoặc chúng thành "việc chung" và không ai làm.

Chúng cũng đòi **cùng một loại kỷ luật**: *số phải tính được, không được viết tay*. Dự án đã mắc lỗi
đó hai lần và cả hai đều ở phần TV1 phụ trách — `"hơn 90 món"` khi thực đơn có đúng 91, và kiểm kê
đụng chữ ghi `32/90` khi thật là `53/40`.

### Kiến thức phải nắm

**Phần dữ liệu**
- Ba loại câu hỏi **A tra cứu / B tri thức / C phán đoán**, và vì sao loại A **không** được để mô
  hình sinh trả lời.
- **Rút dấu tiếng Việt là phép mất thông tin.** Bảy lỗi bản cũ đều từ đây, và chúng là **một lớp
  lỗi** xuất hiện bảy lần. Cách chặn là đổi *hình dạng dữ liệu* (nhãn mang tiền tố nhóm), không
  phải sửa từng lỗi.
- **Độ phủ nhãn quyết định lọc được hay không.** Nhóm phủ 91/91 thì thiếu nhãn là *lỗi dữ liệu*;
  nhóm phủ một phần thì thiếu nhãn là *chưa ghi nhận*, **không** phải *không có*. Nhãn `allergen`
  chỉ phủ 44/91 món — nên danh sách lọc ra **không phải kết luận về an toàn**.
- **MỘT kho, HAI chế độ trả lời.** `verbatim` trả nguyên văn (mô hình không chạm vào chữ);
  `synthesize` là đầu vào cho mô hình viết. Số **kho** gộp được; số **chế độ trả lời** không, vì nó
  là chuyện an toàn.
- **Provenance `derived` vs `demo`**: `derived` sinh từ thực đơn nên không thể lệch; `demo` là nội
  dung người viết.
- **Chunking**: chia theo heading `##`, kèm tiêu đề tài liệu vào mỗi đoạn, `chunk_id` tất định. Cửa
  `audience: guest` **từ chối** tệp không phải nội dung cho khách — không phải lọc bỏ.

**Phần đo lường**
- **Khóa đáp án là truy vấn, không phải danh sách.** Danh sách viết tay thì không có cách nào kiểm —
  bản cũ có 96 khóa trỏ sai chỗ suốt nhiều tháng.
- **Test hai chiều.** Thước đo chỉ có test "bắt được lỗi" thì qua được bằng cách chấm đỏ mọi thứ.
- **Ba nhóm, không phải hai.** Ca an toàn là **chốt**, không phải số liệu — một ca chốt đỏ là
  **chặn**, kể cả khi tỷ lệ chung tăng.
- **Bộ dò lỗ** tìm lỗi *chưa nghĩ tới*. Khi bịt một lỗ, con số nền tụt từ **0,9960 xuống 0,7368** —
  tức 99,6% kia gần như hoàn toàn ảo.
- **`criterion_too_strict` là lớp lỗi dễ bỏ qua nhất.** Dấu hiệu: **nhiều ca đỏ cùng MỘT thông báo**
  thì thường là tiêu chí sai, không phải hệ thống sai. Vừa xảy ra: 7 ca dị ứng mới đỏ đồng loạt vì
  khóa đáp án ghi `allowed: savoury` trong khi câu hỏi không nói "món ăn".

### Đã xong
Kho tri thức **84 tài liệu / 327 đoạn** (24 `verbatim` + 60 `synthesize`; 56 `derived` + 28 `demo`),
303 đoạn được xếp hạng. Từ điển **84 nhãn / 16 nhóm**, hai nguồn thực đơn khớp 91/91. Tập đánh giá
**119 ca / 41 họ**, chia chốt 21 / phát triển 61 / niêm phong 37. Thước đo **37 test**, bộ dò lỗ tìm
**0 lỗ**.

### Việc còn lại — làm theo đúng thứ tự này
Hai việc đầu **chặn người khác**, nên làm trước cả việc mở rộng kho:

1. **~120 ca đánh giá truy hồi** (`retrieval_cases.json`) → **TV3 chờ cái này**. Khóa đáp án là
   *điều kiện chọn*, và phải có `forbidden_selectors` — chỉ số **forbidden@5** quan trọng nhất vì nó
   đo việc trích đoạn **sai chủ đề**.
2. **~25 kịch bản đa lượt** (`session_scripts.json`) → **TV5 chờ cái này**. Bốn nhóm:
   `allergy_persists` (5, **chốt an toàn**), `constraint_overrides` (6), `no_repeat` (5),
   `context_reference` (9).
3. **5 phép kiểm giỏ hàng** cho TV4, cộng chốt `safety_cart_no_allergen`.
4. `analyze_failures.py` — phân loại mọi ca đỏ vào **6 lớp nguyên nhân**: `vocab_miss`,
   `retrieval_miss`, `constraint_conflict`, `data_gap`, `criterion_too_strict`, `model_error`.
5. Mở rộng kho **khi có nhu cầu thật**. Tiêu chí: *nhóm này có câu hỏi nào mà lớp tra khóa không trả
   lời được không?* Thêm tài liệu cho nhóm đã đúng 100% là tạo **đường thứ hai cho cùng một việc**.

### Sở hữu tệp
`ai/knowledge/*` · `ai/app/rag/chunker.py` · `ai/app/test_chunker.py` ·
`ai/scripts/build_knowledge.py` · `build_tag_dictionary.py` · `audit_allergen_tags.py` ·
`backend/data/menu-tags.json` · `ai/evaluation/*` **toàn bộ**

### Tự đo bằng
```bash
python ai/scripts/build_knowledge.py --check
python ai/scripts/build_tag_dictionary.py --check
python ai/scripts/audit_allergen_tags.py
python ai/evaluation/validate_cases.py
python ai/evaluation/build_split.py --check
python ai/evaluation/probe_metric_holes.py
python -m unittest discover -s ai/evaluation -p "test_*.py"
python -m unittest test_chunker            # trong ai/app
```

---

# TV2 — Hiểu câu hỏi

### Câu hỏi khâu này trả lời
*Câu khách vừa gõ nêu ra những ràng buộc gì, và cái gì hệ thống KHÔNG hiểu?*

### Kiến thức phải nắm
- **Khớp cụm dài trước, rồi ăn hết đoạn đã khớp.** Cơ chế này bảo vệ **72 cụm có nguy cơ** (53 bị
  chứa trong cụm khác, 40 nằm trong tên món, 21 thuộc cả hai). Số này do
  `test_understand.collision_census()` tính lại mỗi lần chạy, **không viết tay**.
- **Ràng buộc khác ngữ cảnh.** "Tôi ăn chay" là ràng buộc (lọc cứng); "tôi đi hẹn hò" là ngữ cảnh
  (chỉ sắp thứ tự). Lẫn hai thứ thì câu hẹn hò chỉ còn **1 món** trong 91.
- **Mô hình chỉ HIỂU, không CHỌN.** Nó trả về nhãn, và mọi nhãn đi qua **cổng kiểm**: nhãn không có
  thật hoặc sai vai thì **bị bỏ**, không phải được dùng rồi hy vọng đúng.
- **An toàn không được phụ thuộc mô hình sinh.** Proxy chết thì khách mất phần gợi ý tinh, **không
  mất bảo vệ dị ứng**.

### Hai bài học đắt nhất, cả hai đều ở khâu này

**1. Một cơ chế an toàn chưa bao giờ chạy.** Dòng 408 có hai byte `0x08` thật trong chuỗi
raw-string, nên `\bkhong ...` thực chất là `<backspace>khong ...` và mẫu "không ⟨chủ đề⟩" là **mã
chết**. Vô hình (không hiện trên màn hình lẫn trong `git diff`), im lặng (regex không lỗi, chỉ không
khớp), bị che (`AVOID_FRAMING` có sẵn `khong co` nên "không **có** hải sản" vẫn chạy). 112 ca đánh
giá không bắt được vì không ca nào dùng đúng dạng đó.

→ `test_source_hygiene.py` nay ép: **cơ chế nào được khai là hàng rào an toàn thì phải có ca chứng
minh nó CHẠY**, không phải chỉ có mặt trong mã.

**2. Đo một cơ chế thì phải CHẠY nó.** Khi nối tên món tới nhóm dị nguyên, bộ dò của tôi phân tích
*chuỗi con* và loại **17/19** ứng viên (`cua` nằm trong `gio mo cua`, `ca` nằm trong `ca phe`). Tin
nó thì lỗ an toàn vẫn mở. Nhưng phân tích chuỗi con **không biết** về cơ chế ăn đoạn đang bảo vệ
đúng mấy chỗ đó. Chạy `understand()` thật: **19/19 an toàn**.

### Việc còn lại
1. Nhận `session_state` từ TV5 và hợp nhất theo **ba quy tắc** (phối hợp với TV5 về hình dạng —
   TV2 nên chủ động nhận phần này vì quy tắc đọc và ghi vào chính `Request`).
2. Mở rộng từ vựng cho `topic_keys` mới khi TV1 thêm tài liệu.
3. Nối thêm tên món tới nhóm dị nguyên khi gặp cách nói chưa phủ — **luôn kèm ca nhóm CHỐT của
   TV1**, và đo bằng cách **chạy `understand()` thật**.

### Sở hữu tệp
`ai/app/understand.py` · `llm_understand.py` · `test_understand.py` · `test_llm_understand.py` ·
`test_source_hygiene.py`

### Tự đo bằng
```bash
python -m unittest test_understand test_llm_understand test_source_hygiene   # trong ai/app
python ai/evaluation/run_baseline.py --all
python ai/evaluation/run_ablation.py
```

---

# TV3 — Truy hồi

### Câu hỏi khâu này trả lời
*Câu này cần đoạn tri thức nào — và phương pháp lấy nào tốt hơn, đo được?*

### Kiến thức phải nắm
- **BM25** (`k1=1.5`, `b=0.75`, tách từ dùng `understand.fold`), **embedding**
  (`intfloat/multilingual-e5-small`, 384 chiều, cosine), **hybrid RRF** (`k=60`).
- **Chỉ số**: Hit@1, Hit@5, MRR@5, nDCG@5, và **forbidden@5** — chỉ số cuối quan trọng nhất, vì nó
  đo việc trích đoạn **sai chủ đề**. Con số phải kèm `n`: 120 ca thì một ca lệch là 0,8%.
- **Giao thức đo độ trễ**: screening 1 lần và release 7 lần là hai giao thức khác nhau. Bản cũ trộn
  chúng rồi so 29ms với 81ms như cùng loại.
- **Đoạn `verbatim` bị loại khỏi chỉ mục xếp hạng** — chúng đã có đường tới khách riêng (tra khóa,
  trả nguyên văn). Để trong chỉ mục là hai đường tới cùng nội dung, và đường xếp hạng có thể trích
  một câu chính sách ra giữa câu tư vấn món.
- **Không phải chỗ nào cũng nên dùng RAG.** Nhóm nhãn `price` phủ 91/91 món nên lọc theo nhãn đúng
  **100%**, còn BM25 và embedding **không hiểu số**.

### Nhận từ TV1
Kho **303 đoạn `synthesize`** với 4 bất biến đã ép: mọi đoạn kèm tiêu đề tài liệu, `chunk_id` tất
định và không trùng, dãy mã liên tục từ 0, cửa `audience: guest`. Đây là **hiện vật đã hoàn thành** —
TV3 không phải soạn nội dung, chỉ làm cách lấy.

### Việc còn lại
1. `ai/app/rag/bm25.py`, `embedding.py`, `hybrid.py` — cùng một giao diện
   `Retriever.search(query, k) -> list[RetrievedChunk]`.
2. So ba phương pháp trên **hai bài toán** — đây là phần đáng báo cáo nhất:

   | Bài toán | Ứng viên | Dự kiến |
   |---|---|---|
   | truy hồi tri thức | BM25 / embedding / hybrid | embedding thắng ở câu diễn đạt khác từ; BM25 thắng ở câu có tên riêng |
   | chọn món | BM25 / embedding / **lọc theo nhãn** | **lọc theo nhãn thắng dứt khoát** |

   Bài toán thứ hai quan trọng vì nó chứng minh **bằng số** rằng không phải chỗ nào cũng nên dùng
   RAG. Nếu hybrid không hơn BM25 thì đó là **kết quả**, phải báo đúng như vậy.
3. Ablation: tắt rút dấu cho BM25, tắt chuẩn hóa vector cho embedding.
4. Đưa lại `sentence-transformers`, `torch`, `numpy` vào `ai/requirements.txt`. Ảnh Docker lên
   **~3GB** — đây là **quyết định có đánh đổi**, phải ghi vào tài liệu kèm con số, không phải mặc
   định. Bước 5 đã **bỏ** chúng sau khi đo rằng 24 chủ đề tra khóa đúng 100%.

### Chặn bởi
Cần **~120 ca truy hồi của TV1** để đo. Tuần 1 làm được BM25 + hybrid trên **303 đoạn thật đã có**,
kiểm bằng ví dụ nhỏ tính tay được (BM25 xếp đúng thứ tự; RRF khớp công thức trên 2 danh sách).

### Sở hữu tệp
`ai/app/rag/bm25.py` · `embedding.py` · `hybrid.py` · `retriever.py` ·
`ai/evaluation/run_retrieval_comparison.py`

### Tự đo bằng
```bash
python ai/evaluation/run_retrieval_comparison.py    # chưa viết
python -m unittest test_bm25 test_hybrid            # chưa viết
```

### Điều phải nói ra trong báo cáo
**Chưa chạy phép so nào.** Viết con số về BM25/embedding trước khi chạy là **bịa**, và một báo cáo
có một số bịa thì mọi số còn lại mất giá trị. Tập niêm phong của phép so **chỉ được mở một lần**.

---

# TV4 — Chọn món & giỏ hàng

### Câu hỏi khâu này trả lời
*Với những ràng buộc đã hiểu, món nào thỏa — và thẻ giỏ gợi ý gồm gì?*

### Kiến thức phải nắm
- **Sáu nhánh loại trừ**, không nhánh nào chồng nhánh nào, và thứ tự là thứ tự loại trừ. Bản cũ có
  **8 đường chồng nhau**, 2 trong số đó bị một cờ tắt mà hệ thống vẫn chạy đúng.
- **Fail-closed cho dị nguyên**: áp cuối cùng, **không bao giờ nới**, kể cả khi kết quả rỗng. Thà
  nói "không có món nào phù hợp" còn hơn mời khách món có thể gây dị ứng.
- **Nhóm nhãn không phủ hết 91 món chỉ được dùng theo chiều khẳng định** (đưa lên trước), không được
  dùng để loại.
- **Thẻ giỏ phải sinh từ ĐÚNG danh sách món mà `answer.py` đã chọn.** Không có đường sinh thẻ riêng
  — hai đường sẽ lệch nhau, và lệch ở đây nghĩa là thẻ giỏ chứa món khách dị ứng.

### Đã xong
`answer.py` — 6 nhánh, fail-closed, `prefer_tags` chỉ xếp thứ tự. 108/119 ca, 0 lỗi an toàn.

### Đã xong
`answer.py` 6 nhánh loại trừ, fail-closed. `cart.py` với **5 bất biến**, 20 test — cộng
`test_answer.py` 13 test cho phần trước đó chỉ được kiểm qua 119 ca.

**Một lỗi thật đã sửa ở khâu này:** câu "Món nào không cay?" trả **sáu loại bia**. Đo được
**13/119 ca** khách hỏi "món" mà nhận toàn đồ uống, và **cả 13 đều QUA** đánh giá vì khóa đáp án
không cấm đồ uống. Nguyên nhân là thứ tự sắp: 5 món rẻ nhất thực đơn đều là đồ uống
(12.000–30.000đ) còn món ăn rẻ nhất 35.000đ. Sửa bằng cách xếp món ăn trước — **ngữ cảnh, không
phải ràng buộc**, nên "món nào rẻ hơn 20 nghìn" vẫn đúng là trả đồ uống. 13 ca → 2 ca.

### Năm bất biến của `cart.py`

1. Mọi món trong thẻ phải tồn tại trong thực đơn, **giá lấy từ thực đơn**.
2. `requires_customer_confirmation` **luôn `true`**. Không có nhánh nào đặt `false`.
3. Món bị `avoid_tags` loại **không bao giờ** vào thẻ — kể cả khi mô hình đề xuất.
4. Chỉ sinh thẻ ở nhánh `filter`, `compare`, `item_detail`. Nhánh `clarify`, `no_data`, `refuse`
   **không có thẻ** — gợi ý đặt món khi chưa hiểu câu hỏi là sai.
5. `reason` nêu **ràng buộc đã thỏa**, không phải câu quảng cáo. Sinh từ `require_tags` và
   `avoid_tags` nên không thể bịa.

Cộng: bỏ món trong `suggested_menu_item_ids` khi khách nói "món khác đi" (backend đã có
`GetExcludedMenuItemIds`).

### Sở hữu tệp
`ai/app/answer.py` · `cart.py` · `test_cart.py`

### Tự đo bằng
```bash
python ai/evaluation/run_baseline.py --all     # trả mã khác 0 nếu có lỗi an toàn
python -m unittest test_cart                   # trong ai/app
```

---

# TV5 — Cổng vào & phiên

### Câu hỏi khâu này trả lời
*Backend gọi vào thế nào, và bộ nhớ trong một phiên QR sống chết ra sao?*

### Kiến thức phải nắm
- **FastAPI**: endpoint, dependency, xác thực bằng token nội bộ, SSE cho `/v1/chat/stream`.
- **Ba quy tắc hợp nhất bộ nhớ**, và quy tắc đầu là **chốt an toàn**:

  | Loại | Quy tắc | Nếu sai |
  |---|---|---|
  | dị nguyên (`avoid_tags`) | **cộng dồn, không bao giờ bỏ** | khai dị ứng lượt 1 → lượt 5 bị mời món hải sản |
  | ràng buộc cứng (`spice`, `price`, `diet`, `party`) | lượt mới **ghi đè** cùng nhóm | "rẻ hơn nữa" cộng thêm thay vì thay ngân sách cũ |
  | ngữ cảnh (`prefer_tags`) | cộng vào, giữ **5 gần nhất** | bộ nhớ phình vô hạn |

- **Rolling summary phải sinh TẤT ĐỊNH**, không nhờ mô hình. Câu trả lời sai thì sai một lượt; bộ
  nhớ sai thì **sai suốt phiên**.
- **Thoái hóa êm**: thiếu cấu hình hay proxy chết thì trả câu trả lời tất định, không sập. Dự án đã
  mắc lỗi này một lần — `urllib.request.Request(...)` nằm ngoài khối `try` nên thiếu cấu hình là
  **sập**, trong khi tài liệu khẳng định nó thoái hóa êm. CI tìm ra vì CI là môi trường duy nhất
  không có `ai/.env`.

  → **Khẳng định về hành vi khi lỗi thì phải có test cho đúng đường lỗi đó.**

### Đã có sẵn, đừng viết lại
Backend **đã xóa bộ nhớ đúng lúc**: `IChatStore.DeleteSessionsByTableSession` được gọi khi đóng
phiên (`TableEndpoints.cs:508`), khi hết hạn (`:708`/`:713`), và khi thanh toán
(`TableInvoiceEndpoints.cs:401`). `SuggestedCartActionResponse` và `ChatSessionStateSnapshot` cũng đã
có. Backend đọc JSON của AI **hoàn toàn bằng `TryGetProperty`** nên mọi trường đều optional — dịch
vụ mới chỉ cần trả tập trường nhỏ hơn với **đúng tên cũ**, nên **không phải phá hợp đồng**.

### Đã xong
1. `ai/app/service.py` — 5 endpoint, 24 test. Ca **thiếu token trả 401**; token trống trong môi
   trường thì **từ chối mọi yêu cầu** (503), không mở cửa.
2. `ai/app/session.py` — ba quy tắc hợp nhất, 22 test, rolling summary tất định.
3. `ai/contracts/ai-chat-v1.schema.json` — viết xong, và `test_contract.py` đối chiếu nó với
   **phản hồi THẬT** trên 8 dạng câu hỏi. Phép kiểm phía backend đã tự bật lại.

### Việc còn lại
1. `deploy/docker-compose.yml` — bỏ `AI_PIPELINE_PROFILE` (biến giữ chỗ của bản cũ).
2. **Chạy thật** `docker compose up` — điều kiện chấp nhận không thay được bằng test, xem dưới.

### Chặn bởi
Cần **~25 kịch bản đa lượt của TV1** để đo bộ nhớ. Tuần 1 làm được `/health`, `/ready`, xác thực
token, hợp đồng schema, và ba quy tắc hợp nhất trên **dữ liệu giả**.

### Sở hữu tệp
`ai/app/service.py` · `session.py` · `test_service.py` · `test_session.py` · `ai/contracts/*` ·
`ai/Dockerfile` · `deploy/docker-compose.yml`

### Tự đo bằng
```bash
python -m unittest test_service test_session test_packaging   # trong ai/app
dotnet test backend/RestaurantQrAiOrdering.sln
```

### Điều kiện chấp nhận — không thay được bằng test
`docker compose up` → quét QR → hỏi 5 câu gồm một câu khai dị ứng → thẻ giỏ hiện đúng và thêm được
vào giỏ → hỏi tiếp **không nhắc lại dị ứng**, xác nhận vẫn được bảo vệ → đóng phiên, mở lại, xác
nhận **bộ nhớ đã mất**.

---

## Ai làm được gì ngay tuần 1 — không ai phải chờ

| TV | Tuần 1 (làm ngay) | Tuần 2+ (cần đầu vào) |
|---|---|---|
| **1** | **~120 ca truy hồi** rồi **~25 kịch bản đa lượt** — hai việc này chặn TV3 và TV5 | `analyze_failures.py`, mở rộng kho nếu cần |
| **2** | rà lại từ vựng, nối tên món dị nguyên còn thiếu | hợp nhất `session_state` khi TV5 chốt hình dạng |
| **3** | BM25 + hybrid trên **303 đoạn thật đã có**, kiểm bằng ví dụ tính tay được | chạy phép so khi TV1 xong ca truy hồi |
| **4** | `cart.py` + 5 bất biến (`answer.py` đã có, đủ để làm) | chỉnh theo ca giỏ hàng của TV1 |
| **5** | `/health`, `/ready`, token, hợp đồng schema, 3 quy tắc hợp nhất trên dữ liệu giả | nối `/v1/chat` khi TV4 xong `cart` |

Điều làm việc này chạy được: **tiêu chí kiểm chứng viết được trước khi mã tồn tại**, vì tiêu chí đến
từ định nghĩa khâu chứ không từ mã người khác.

---

## Ba điều cấm chung — ai vi phạm cũng làm CI đỏ

| Cấm | Vì sao | Cưỡng chế bởi |
|---|---|---|
| Nới lỏng lọc dị nguyên, kể cả khi kết quả rỗng | thà nói "không có món phù hợp" còn hơn mời món gây dị ứng | `run_baseline.py` trả mã khác 0 |
| Để mô hình sinh **chọn** món hoặc **nêu** giá | mô hình không tất định; chọn món và giá phải tra bảng | `test_llm_understand.py` |
| **Viết số vào tài liệu** thay vì tính nó | số viết tay luôn trôi khỏi dữ liệu. Dự án đã mắc hai lần: "hơn 90 món" khi có đúng 91, và kiểm kê đụng chữ "32/90" khi thật là 53/40 | `--check` trong CI, `collision_census()` |

## Quy tắc sở hữu tệp

Chỉ người sở hữu được sửa tệp trong cột "Sở hữu tệp". Cần đổi tệp của người khác thì **nhắn họ**,
không tự sửa. Đây là quy tắc chống xung đột git, và cũng chống việc hai người sửa cùng một chỗ theo
hai hướng ngược nhau.

Các hợp đồng ở mục "Giao diện đã chốt" là ngoại lệ: **đổi chúng phải nhắn cả nhóm.**

## Mỗi tuần báo đúng ba dòng

```
TV4 — tuần 2
  số đo: run_baseline.py --all -> 111/119 (tuần trước 108/119), 0 lỗi an toàn
  làm được: thẻ giỏ + 5 test bất biến
  đang vướng: chưa rõ "món khác đi" nên bỏ bao nhiêu món đã gợi ý — cần TV1 viết ca
```

Dòng **số đo** bắt buộc và phải là con số chạy được. Bài học đắt nhất của dự án là *thước đo sai 3
lần trước khi hệ thống sai*, nên "cảm giác đã tốt hơn" không tính là tiến độ.

## Ba tài liệu ai cũng phải đọc trước khi bắt đầu

1. **`ai/README.md`** — 5 nguyên tắc của bản dựng lại.
2. **`ai/notebooks/he_thong_ai_tu_van_dat_mon.ipynb`** — 66 ô, mỗi ô mã tính lại từ mã sống. Chạy nó
   là hiểu toàn hệ thống bằng **số**, không bằng lời.
3. **`ai/docs/00-problem-statement.md`** — AI được phép trả lời gì, và tuyệt đối không làm gì.

## Trạng thái hiện tại

| TV | Xong | Còn lại |
|---|---|---|
| **1** | kho 84 tài liệu / 327 đoạn · từ điển 84 nhãn · 119 ca / 41 họ · thước đo 37 test · bộ dò 0 lỗ | ca truy hồi, kịch bản đa lượt, ca giỏ hàng, `analyze_failures.py` |
| **2** | hiểu câu hỏi + mô hình + cổng kiểm · 0 lỗi an toàn | nhận ngữ cảnh phiên |
| **3** | — | BM25, embedding, hybrid, phép so trên hai bài toán |
| **4** | `answer.py` 6 nhánh · `cart.py` 5 bất biến · sửa lỗi "hỏi món trả toàn bia" | chỉnh theo ca giỏ hàng của TV1 |
| **5** | 5 endpoint · `session.py` 3 quy tắc · hợp đồng schema | **chạy thật `docker compose`** |

**Số đo hiện tại:** 108/119 (90,8%) chỉ bằng mã tất định · 119/119 khi có mô hình · **0 lỗi an toàn
ở cả hai chế độ** · nhóm chốt 21/21 · 9/9 cơ chế ablation có giá trị, 5 là hàng rào an toàn ·
**196 test `ai/app`** + 37 test `ai/evaluation`.

**Thứ duy nhất còn chặn khách dùng được:** chưa chạy thật `docker compose up`. Mọi con số trên tồn
tại trong test; chạy thật là phép kiểm cuối cùng, và nó **không thay được bằng test** vì nó kiểm
đúng thứ test không chạm tới — container, mạng, và việc backend gọi được dịch vụ.
