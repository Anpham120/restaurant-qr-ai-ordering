# Phân công 5 thành viên — chia theo PIPELINE HỆ THỐNG

## Ý tưởng: mỗi người một khâu trong luồng xử lý một câu hỏi

Chia theo **đường đi thật của một câu hỏi lúc phục vụ**, không theo thứ tự dự án được dựng.

```
khách quét QR, gõ một câu
        │
   ┌────▼──────────────────────────────────────────────┐
   │ A  CỔNG VÀO & PHIÊN                               │  service.py · session.py
   │    nhận HTTP, xác thực token, NẠP bộ nhớ phiên    │
   └────┬──────────────────────────────────────────────┘
        │  ChatTurn(question, session_state)
   ┌────▼──────────────────────────────────────────────┐
   │ B  HIỂU CÂU HỎI                                   │  understand.py · llm_understand.py
   │    câu này ràng buộc gì? → require/prefer/avoid   │
   └────┬──────────────────────────────────────────────┘
        │  Request
   ┌────▼──────────────────────────────────────────────┐
   │ C  TRUY HỒI TRI THỨC                              │  rag/* · knowledge/*
   │    câu này cần đoạn tri thức nào?                 │
   └────┬──────────────────────────────────────────────┘
        │  Evidence
   ┌────▼──────────────────────────────────────────────┐
   │ D  CHỌN MÓN & GIỎ HÀNG                            │  answer.py · cart.py
   │    món nào thỏa? thẻ giỏ nào?                     │
   └────┬──────────────────────────────────────────────┘
        │  Reply + Cart
   ┌────▼──────────────────────────────────────────────┐
   │ A  GHI bộ nhớ phiên, trả JSON cho backend         │
   └───────────────────────────────────────────────────┘

   ┌───────────────────────────────────────────────────┐
   │ E  ĐO LƯỜNG & AN TOÀN  (xuyên ngang cả 4 khâu)    │  evaluation/*
   │    đúng hay sai? và làm sao biết thước đo đúng?   │
   └───────────────────────────────────────────────────┘
```

### Ba lợi ích so với chia theo thứ tự dựng

1. **Cả 5 người làm song song từ ngày 1.** Giao diện giữa các khâu chốt trước (mục "Giao diện đã
   chốt" ở dưới), nên không ai phải chờ ai xong mới bắt đầu.
2. **Sở hữu tệp sạch.** Một người một module → ít xung đột git, và khi cần đổi thì biết nhắn ai.
3. **Khớp cách gỡ lỗi thật.** Production trả lời sai thì câu hỏi đầu tiên là *"sai ở khâu nào?"* —
   và mỗi khâu có đúng một người phụ trách.

---

## Cái giá của cách chia này, và nó là cái giá thật

**Dữ liệu và đo lường KHÔNG phải khâu runtime.** Một câu hỏi không "đi qua" từ điển nhãn hay tập
đánh giá — chúng là thứ các khâu *dùng*, không phải chặng chúng *chạy qua*. Nên chia thuần theo
pipeline thì hai thứ đó phải gửi vào đâu đó, và mỗi cách gửi đều có giá:

| Thứ | Gửi vào | Cái giá phải chấp nhận |
|---|---|---|
| Từ điển nhãn (`menu-tags.json`, `build_tag_dictionary.py`) | **B** | B là nơi duy nhất dùng từ vựng nên hợp lý; nhưng B gánh cả việc dữ liệu |
| Kho tri thức (`knowledge/*`, `chunker.py`, `build_knowledge.py`) | **C** | **C gánh HAI nền kiến thức**: dữ liệu nhà hàng *và* truy hồi thông tin |
| Đo lường (`evaluation/*`) | **E** | E không phải một chặng — nó là vai xuyên ngang, và phải được gọi là **vai** chứ không phải "việc chung" |

Dòng thứ hai là cái giá đáng kể nhất, và phải nói rõ: bản phân công trước tách **nội dung kho**
(dữ liệu nhà hàng, provenance) khỏi **cách lấy đoạn** (tf-idf, cosine, chỉ số xếp hạng) vì hai việc
cần hai nền kiến thức khác nhau. Chia thuần pipeline thì gộp chúng lại. Lập luận cũ không sai — nó
bị **đánh đổi** cho việc song song hóa.

**Điều làm cái giá đó chịu được:** kho tri thức **đã xây xong và CI đã canh** (84 tài liệu / 327
đoạn, `build_knowledge.py --check`). C **thừa hưởng một hiện vật đã hoàn thành** chứ không phải tự
soạn nội dung từ đầu, nên việc còn lại của C gần như hoàn toàn là truy hồi.

**Điều KHÔNG được xảy ra:** để đo lường tan vào 4 khâu kia. Nếu mỗi người tự đo phần mình thì đó
đúng bệnh của bản cũ — 8 đường xử lý, mỗi đường "chạy đúng" theo người viết nó, không ai đo cả hệ
thống, và **thước đo sai 3 lần trước khi hệ thống sai**.

---

## Giao diện đã chốt — đọc trước khi viết dòng mã nào

Năm hợp đồng dưới đây **chốt ngay tuần 1** và không đổi mà không thông báo. Chúng là điều kiện để
5 người làm song song: ai cũng biết mình nhận gì và phải trả gì, nên viết được ngay cả khi khâu
trước chưa xong (dùng dữ liệu giả theo đúng hình dạng).

```python
# A -> B
ChatTurn(question: str, session_state: SessionState | None)

# B -> C  (hình dạng HIỆN CÓ, không đổi)
Request(text, folded, require_tags, prefer_tags, avoid_tags, budget_max, budget_strict,
        categories, wants, named_items, policy_topic, asks_price, asks_allergy,
        asks_extreme, is_comparison, off_topic, unparsed_restriction, ...)

# C -> D
Evidence(verbatim: str | None,            # tài liệu answer_mode=verbatim, trả NGUYÊN VĂN
         chunks: list[KnowledgeChunk])    # tài liệu answer_mode=synthesize, cho mô hình đọc

# D -> A  (hình dạng HIỆN CÓ, chỉ thêm trường cart)
Reply(text, items, kind, asks_back, branch, notes, cart: list[CartAction])
CartAction(menu_item_id, name, quantity, reason, evidence_ids,
           requires_customer_confirmation=True)   # LUÔN True, không nhánh nào đặt False

# E đọc tất cả, và sở hữu mọi ca CHỐT
```

Ai cần đổi một trong 5 hợp đồng này thì **nhắn cả nhóm trước khi sửa**, vì mỗi hợp đồng có đúng
hai người phụ thuộc.

---

# Khâu A — Cổng vào & phiên

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
  **sập**. Khẳng định về hành vi khi lỗi **phải có test cho đúng đường lỗi đó**.

### Việc còn lại
1. `ai/app/service.py` — 5 endpoint: `/health`, `/ready`, `/v1/chat`, `/v1/chat/stream`,
   `/v1/cache/invalidate`. Có ca **thiếu token phải 401**.
2. `ai/app/session.py` — ba quy tắc hợp nhất trên, cộng rolling summary tất định.
3. `ai/contracts/ai-chat-v1.schema.json` — viết lại. Việc này **tự bật lại** phép kiểm có điều kiện
   trong `backend/tests/.../AiContractBoundaryTests.cs`.
4. `deploy/docker-compose.yml` — bỏ `AI_PIPELINE_PROFILE` (biến giữ chỗ của bản cũ).

### Đã có sẵn, đừng viết lại
Backend **đã xóa bộ nhớ đúng lúc**: `IChatStore.DeleteSessionsByTableSession` được gọi khi đóng
phiên (`TableEndpoints.cs:508`), khi hết hạn (`:708`/`:713`), và khi thanh toán
(`TableInvoiceEndpoints.cs:401`). `SuggestedCartActionResponse` và `ChatSessionStateSnapshot` cũng
đã có. Backend đọc JSON của AI **hoàn toàn bằng `TryGetProperty`** nên mọi trường đều optional —
dịch vụ mới chỉ cần trả tập trường nhỏ hơn với đúng tên cũ.

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

# Khâu B — Hiểu câu hỏi

### Câu hỏi khâu này trả lời
*Câu khách vừa gõ nêu ra những ràng buộc gì, và cái gì hệ thống KHÔNG hiểu?*

### Kiến thức phải nắm
- **Rút dấu tiếng Việt là phép mất thông tin.** Bảy lỗi bản cũ đều từ đây, và chúng là **một lớp
  lỗi** xuất hiện bảy lần. Cách chặn là **đổi hình dạng dữ liệu**: nhãn mang tiền tố nhóm
  (`spice:hot` chứ không `hot`), không phải sửa từng lỗi.
- **Khớp cụm dài trước, rồi ăn hết đoạn đã khớp.** Cơ chế này bảo vệ **72 cụm có nguy cơ** (53 bị
  chứa trong cụm khác, 40 nằm trong tên món, 21 thuộc cả hai). Số này do
  `test_understand.collision_census()` tính lại mỗi lần chạy, **không viết tay**.
- **Ràng buộc khác ngữ cảnh.** "Tôi ăn chay" là ràng buộc (lọc cứng); "tôi đi hẹn hò" là ngữ cảnh
  (chỉ sắp thứ tự). Lẫn hai thứ thì câu hẹn hò chỉ còn **1 món** trong 91.
- **Mô hình chỉ HIỂU, không CHỌN.** Nó trả về nhãn, và mọi nhãn nó trả về đi qua **cổng kiểm**:
  nhãn không có thật hoặc sai vai thì **bị bỏ**, không phải được dùng rồi hy vọng đúng.
- **An toàn không được phụ thuộc mô hình sinh.** Hai cách khai dị ứng từng chỉ mô hình hiểu được;
  chúng đã được đưa về mã tất định. Proxy chết thì khách mất phần gợi ý tinh, **không mất bảo vệ
  dị ứng**.

### Bài học đắt nhất của khâu này
Một cơ chế an toàn của khâu này **chưa bao giờ chạy**: dòng 408 có hai byte `0x08` thật trong chuỗi
raw-string, nên `\bkhong ...` thực chất là `<backspace>khong ...` và mẫu "không ⟨chủ đề⟩" là **mã
chết**. 119 ca đánh giá không bắt được vì không ca nào dùng đúng dạng đó.

Vô hình (0x08 không hiện trên màn hình lẫn trong `git diff`), im lặng (regex không lỗi, chỉ không
khớp), và bị che (`AVOID_FRAMING` có sẵn `khong co` nên "không **có** hải sản" vẫn chạy).

→ **`test_source_hygiene.py` nay ép: cơ chế nào được khai là hàng rào an toàn thì phải có ca chứng
minh nó CHẠY, không phải chỉ có mặt trong mã.**

### Việc còn lại
1. Nhận `session_state` từ khâu A và hợp nhất theo ba quy tắc (phối hợp với A về hình dạng).
2. Mở rộng từ vựng cho `topic_keys` mới khi khâu C thêm tài liệu.
3. Nối thêm tên món tới nhóm dị nguyên khi gặp cách nói chưa phủ — **luôn kèm ca nhóm CHỐT của
   khâu E**, và đo bằng cách **chạy `understand()` thật**, không phân tích chuỗi con. Bộ dò chuỗi
   con đã cho **dương tính giả 17/19** một lần, vì nó không biết về cơ chế ăn đoạn.

### Sở hữu tệp
`ai/app/understand.py` · `llm_understand.py` · `test_understand.py` · `test_llm_understand.py` ·
`test_source_hygiene.py` · `ai/scripts/build_tag_dictionary.py` · `backend/data/menu-tags.json`

### Tự đo bằng
```bash
python ai/scripts/build_tag_dictionary.py --check
python -m unittest test_understand test_llm_understand test_source_hygiene   # trong ai/app
python ai/evaluation/run_ablation.py
```

---

# Khâu C — Truy hồi tri thức

### Câu hỏi khâu này trả lời
*Câu này cần đoạn tri thức nào — và phương pháp lấy nào tốt hơn, đo được?*

### Kiến thức phải nắm
- **MỘT kho, HAI chế độ trả lời.** `answer_mode: verbatim` trả nguyên văn (mô hình không chạm vào
  chữ); `answer_mode: synthesize` là đầu vào cho mô hình viết. Số **kho** gộp được; số **chế độ trả
  lời** không, vì nó là chuyện an toàn.
- **Đoạn `verbatim` bị loại khỏi chỉ mục xếp hạng** — chúng đã có đường tới khách riêng. Để trong
  chỉ mục là hai đường tới cùng nội dung.
- **BM25** (`k1=1.5`, `b=0.75`, tách từ dùng `understand.fold`), **embedding**
  (`intfloat/multilingual-e5-small`, 384 chiều, cosine), **hybrid RRF** (`k=60`).
- **Chỉ số**: Hit@1, Hit@5, MRR@5, nDCG@5, và **forbidden@5** — chỉ số cuối quan trọng nhất, vì nó
  đo việc trích đoạn **sai chủ đề**.
- **Giao thức đo độ trễ**: screening 1 lần và release 7 lần là hai giao thức khác nhau. Bản cũ trộn
  chúng rồi so 29ms với 81ms như cùng loại.
- **Không phải chỗ nào cũng nên dùng RAG.** Nhóm nhãn `price` phủ 91/91 món nên lọc theo nhãn đúng
  **100%**, còn BM25 và embedding **không hiểu số**. Bước 5 đã bỏ `sentence-transformers` (~3GB)
  khỏi ảnh Docker sau khi đo rằng 24 chủ đề chính sách tra khóa đúng 100%.

### Đã có sẵn
Kho tri thức **xong và CI canh**: 84 tài liệu / 327 đoạn (24 `verbatim` + 60 `synthesize`; 56
`derived` + 28 `demo`), 303 đoạn được xếp hạng. Bốn bất biến đã ép: mọi đoạn kèm tiêu đề tài liệu,
`chunk_id` tất định và không trùng, dãy mã liên tục, cửa `audience: guest` **từ chối** tệp không
phải nội dung cho khách.

### Việc còn lại
1. `ai/app/rag/bm25.py`, `embedding.py`, `hybrid.py` — cùng một giao diện
   `Retriever.search(query, k) -> list[RetrievedChunk]`.
2. So ba phương pháp trên **hai bài toán**, và đây là phần đáng báo cáo nhất:

   | Bài toán | Ứng viên | Dự kiến |
   |---|---|---|
   | truy hồi tri thức | BM25 / embedding / hybrid | embedding thắng ở câu diễn đạt khác từ; BM25 thắng ở câu có tên riêng |
   | chọn món | BM25 / embedding / **lọc theo nhãn** | **lọc theo nhãn thắng dứt khoát** |

3. Ablation: tắt rút dấu cho BM25, tắt chuẩn hóa vector cho embedding.
4. Mở rộng kho khi có nhu cầu **thật** — tiêu chí: *nhóm này có câu hỏi nào mà lớp tra khóa không
   trả lời được không?*

### Sở hữu tệp
`ai/app/rag/*` · `ai/knowledge/*` · `ai/scripts/build_knowledge.py` ·
`ai/scripts/audit_allergen_tags.py` · `test_chunker.py`

### Tự đo bằng
```bash
python ai/scripts/build_knowledge.py --check
python ai/scripts/audit_allergen_tags.py
python -m unittest test_chunker                      # trong ai/app
python ai/evaluation/run_retrieval_comparison.py     # chưa viết
```

### Điều phải nói ra trong báo cáo
**Chưa chạy phép so nào.** 4/5 điều kiện để phép so có nghĩa đã đủ; thiếu **tập đánh giá truy hồi**
của khâu E. Viết con số về BM25/embedding bây giờ là **bịa**, và một báo cáo có một số bịa thì mọi
số còn lại mất giá trị.

---

# Khâu D — Chọn món & giỏ hàng

### Câu hỏi khâu này trả lời
*Với những ràng buộc đã hiểu, món nào thỏa — và thẻ giỏ gợi ý gồm gì?*

### Kiến thức phải nắm
- **Sáu nhánh loại trừ**, không nhánh nào chồng nhánh nào, và thứ tự là thứ tự loại trừ. Bản cũ có
  **8 đường chồng nhau** và 2 trong số đó bị một cờ tắt mà hệ thống vẫn chạy đúng.
- **Fail-closed cho dị nguyên**: áp cuối cùng, **không bao giờ nới**, kể cả khi kết quả rỗng.
- **Nhóm nhãn không phủ hết 91 món chỉ được dùng theo chiều khẳng định** (đưa lên trước), không
  được dùng để loại — vì thiếu nhãn ở nhóm đó nghĩa là *chưa ghi nhận*, không phải *không phù hợp*.
- **Thẻ giỏ phải sinh từ ĐÚNG danh sách món mà `answer.py` đã chọn.** Không có đường sinh thẻ riêng
  — hai đường sẽ lệch nhau, và lệch ở đây nghĩa là thẻ giỏ chứa món khách dị ứng.

### Việc còn lại
`ai/app/cart.py` với **5 bất biến**, mỗi cái một test:

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

# Khâu E — Đo lường & an toàn

### Câu hỏi khâu này trả lời
*Hệ thống trả lời đúng hay sai — và làm sao biết THƯỚC ĐO của mình đúng?*

> **Đây không phải một chặng của pipeline, và đó chính là lý do nó phải là một vai CÓ TÊN.** Nếu
> đo lường tan vào 4 khâu kia thì mỗi người tự chấm phần mình, và đó đúng bệnh của bản cũ.

### Kiến thức phải nắm
- **Khóa đáp án là truy vấn, không phải danh sách.** Danh sách viết tay thì không có cách nào kiểm
  — bản cũ có 96 khóa trỏ sai chỗ suốt nhiều tháng.
- **Test hai chiều.** Thước đo chỉ có test "bắt được lỗi" thì qua được bằng cách chấm đỏ mọi thứ.
  Phải có cả test "câu trả lời tốt phải xanh".
- **Ba nhóm, không phải hai.** Ca an toàn là **chốt**, không phải số liệu.
- **Bộ dò lỗ** tìm lỗi *chưa nghĩ tới*: đưa câu trả lời chắc chắn tệ qua toàn bộ tập ca. Khi bịt
  một lỗ, con số nền tụt từ **0,9960 xuống 0,7368** — tức 99,6% kia gần như hoàn toàn ảo.
- **`criterion_too_strict` là lớp lỗi dễ bỏ qua nhất.** Dấu hiệu: **nhiều ca đỏ cùng MỘT thông
  báo** thì thường là tiêu chí sai, không phải hệ thống sai. Vừa xảy ra: 7 ca dị ứng mới đỏ đồng
  loạt vì khóa đáp án ghi `allowed: savoury` trong khi câu hỏi không nói "món ăn".

### Việc còn lại
1. **~120 ca đánh giá truy hồi** cho khâu C, khóa đáp án là **điều kiện chọn**, có
   `forbidden_selectors`.
2. **~25 kịch bản đa lượt** (`session_scripts.json`) cho khâu A. Bốn nhóm: `allergy_persists`
   (5, **chốt an toàn**), `constraint_overrides` (6), `no_repeat` (5), `context_reference` (9).
3. **5 phép kiểm giỏ hàng** cho khâu D, cộng chốt `safety_cart_no_allergen`.
4. `analyze_failures.py` — phân loại mọi ca đỏ vào **6 lớp nguyên nhân**: `vocab_miss`,
   `retrieval_miss`, `constraint_conflict`, `data_gap`, `criterion_too_strict`, `model_error`.
   Lớp thứ 5 quan trọng nhất và dễ bị bỏ qua nhất.

### Sở hữu tệp
`ai/evaluation/*` toàn bộ

### Tự đo bằng
```bash
python ai/evaluation/validate_cases.py
python ai/evaluation/build_split.py --check
python ai/evaluation/probe_metric_holes.py
python -m unittest discover -s ai/evaluation -p "test_*.py"
```

---

## Ai làm được gì ngay tuần 1 — không ai phải chờ

| Khâu | Tuần 1 (làm ngay) | Tuần 2+ (cần đầu vào) |
|---|---|---|
| **A** | `/health`, `/ready`, xác thực token, hợp đồng schema, ba quy tắc hợp nhất trên dữ liệu giả | nối `/v1/chat` khi D xong `cart` |
| **B** | rà lại từ vựng, nối tên món dị nguyên còn thiếu | nhận `session_state` khi A chốt hình dạng |
| **C** | BM25 + hybrid trên **303 đoạn thật đã có** | chạy phép so khi E xong tập truy hồi |
| **D** | `cart.py` + 5 bất biến (`answer.py` đã có, đủ để làm) | chỉnh theo ca của E |
| **E** | viết ca truy hồi + kịch bản đa lượt (tiêu chí đến từ *định nghĩa khâu*, không từ mã) | chạy thước đo trên hệ thống thật |

Điều làm việc này chạy được: **tiêu chí kiểm chứng viết được trước khi mã tồn tại**, vì tiêu chí
đến từ định nghĩa khâu chứ không từ mã người khác.

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

Năm hợp đồng ở mục "Giao diện đã chốt" là ngoại lệ: **đổi chúng phải nhắn cả nhóm**, vì mỗi hợp
đồng có đúng hai người phụ thuộc.

## Mỗi tuần báo đúng ba dòng

```
Khâu D — tuần 2
  số đo: run_baseline.py --all -> 111/119 (tuần trước 108/119), 0 lỗi an toàn
  làm được: thẻ giỏ + 5 test bất biến
  đang vướng: chưa rõ "món khác đi" nên bỏ bao nhiêu món đã gợi ý — cần khâu E viết ca
```

Dòng **số đo** bắt buộc và phải là con số chạy được. Bài học đắt nhất của dự án là *thước đo sai 3
lần trước khi hệ thống sai*, nên "cảm giác đã tốt hơn" không tính là tiến độ.

## Ba tài liệu ai cũng phải đọc trước khi bắt đầu

1. **`ai/README.md`** — 5 nguyên tắc của bản dựng lại.
2. **`ai/notebooks/he_thong_ai_tu_van_dat_mon.ipynb`** — 66 ô, mỗi ô mã tính lại từ mã sống. Chạy
   nó là hiểu toàn hệ thống bằng **số**, không bằng lời.
3. **`ai/docs/00-problem-statement.md`** — AI được phép trả lời gì, và tuyệt đối không làm gì.

## Trạng thái hiện tại

| Khâu | Xong | Còn lại |
|---|---|---|
| **A** | — | toàn bộ: 5 endpoint, bộ nhớ phiên |
| **B** | hiểu câu hỏi + mô hình + cổng kiểm, 0 lỗi an toàn | nhận ngữ cảnh phiên |
| **C** | kho tri thức 84 tài liệu / 327 đoạn | BM25, embedding, hybrid, phép so |
| **D** | `answer.py` 6 nhánh, fail-closed | `cart.py` |
| **E** | 119 ca / 41 họ, thước đo 37 test, bộ dò 0 lỗ | tập truy hồi, kịch bản đa lượt, `analyze_failures.py` |

**Số đo hiện tại:** 108/119 (90,8%) chỉ bằng mã tất định · 119/119 khi có mô hình · **0 lỗi an toàn
ở cả hai chế độ** · nhóm chốt 21/21 · 9/9 cơ chế ablation có giá trị, 5 là hàng rào an toàn.
