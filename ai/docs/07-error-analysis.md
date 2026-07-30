# Bước 7 — Truy hồi, phân tích nguyên nhân sai, và bốn phép đo phải làm lại

Bước này làm ba việc: dựng ba cách truy hồi rồi **so trên hai bài toán**, dựng công cụ truy nguyên
nhân của mọi ca không đạt, và dựng khả năng **tham chiếu ngược** mà công cụ đó chỉ ra là còn thiếu.

Phần đáng đọc nhất không phải bảng số, mà là **bốn phép đo đã phải làm lại** (mục 5). Cả bốn đều
thuộc loại không làm chương trình lỗi và không làm test đỏ — chúng chỉ làm con số nói sai.

---

## 1. Con số hiện tại

| Tập | Kết quả | Chốt an toàn |
|---|---|---|
| 122 ca trả lời (một lượt) | **122/122 (100%)** chỉ bằng mã tất định | 0 lỗi |
| 87 lượt phiên (33 kịch bản / 7 nhóm) | **87/87 (100%)**, 0 khoảng cách | 0 lỗi |
| 138 ca truy hồi | xem bảng dưới | nhóm chốt 8/8 abstain |
| ablation trả lời | 9/9 cơ chế có ít nhất một ca chứng minh | 5 là hàng rào an toàn |
| giỏ hàng gợi ý | 6 bất biến áp cho **cả 122 ca**, 217 thẻ sinh ra | `safety_cart_no_allergen` |

**Mô hình sinh đổi 0 ca.** Trước bước này nó đổi +11 ca, và con số đó từng được ghi là giá trị đo
được của mô hình. Đọc lại 11 ca đỏ thì cả 11 đỏ vì **bảng từ vựng thiếu cụm khách thật sự dùng**.
Thêm 23 cụm đã đo thì cả 11 về mã tất định. Nên "+11 ca nhờ mô hình" **không đo mô hình** — nó đo
độ thiếu của bảng từ vựng. Xem mục 5.1.

---

## 2. Truy hồi tri thức — BM25 vs embedding vs hybrid

Kho: **425 đoạn** `answer_mode: synthesize` (84 tài liệu `synthesize`, 108 tài liệu tổng). Đoạn `verbatim` không vào chỉ mục vì
chúng được trả **nguyên văn** qua tra khóa, không qua xếp hạng.

### Nhóm phát triển — 90 ca / 7 họ

| phương pháp | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | cấm@5 | p50 |
|---|---|---|---|---|---|---|
| bm25 | 0,409 | 0,568 | 0,467 | 0,352 | 12 | 0,8 ms |
| embedding | **0,557** | **0,625** | **0,581** | **0,459** | **11** | 52,3 ms |
| hybrid | 0,523 | 0,614 | 0,556 | 0,445 | 13 | 52,6 ms |

### Nhóm NIÊM PHONG — 40 ca / 4 họ · mở MỘT lần ngày 2026-07-30 · giao thức chốt (7 lần/truy vấn)

| phương pháp | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | cấm@5 | abstain | p50 |
|---|---|---|---|---|---|---|---|
| bm25 | 0,605 | 0,711 | 0,637 | 0,410 | 10 | 2/2 | 0,7 ms |
| embedding | **0,658** | **0,921** | **0,754** | **0,538** | **9** | 2/2 | 53,1 ms |
| hybrid | 0,605 | 0,895 | 0,719 | 0,524 | 10 | 2/2 | 53,7 ms |

**Kết luận: embedding thắng, và thắng trên tập held-out.** Thứ tự `embedding > hybrid > bm25` theo
Hit@5 giữ nguyên ở cả hai nhóm — hai nhóm gồm các HỌ khác nhau, nên đó là bằng chứng mạnh nhất có
được ở quy mô này.

**Ba điều phải nói kèm, nếu không bảng trên gây hiểu sai:**

1. **Số tuyệt đối của hai nhóm KHÔNG so được với nhau.** Nhóm niêm phong gồm `kb-written` (24 ca)
   và `kb-health` (12 ca) — tài liệu người viết về các chủ đề tách biệt rõ, dễ hơn. Chỉ THỨ TỰ
   giữa ba phương pháp là so được.
2. **Hybrid KÉM HƠN embedding đơn lẻ, và có `cấm@5` cao nhất.** Kế hoạch dự kiến "hybrid tốt
   nhất"; đo được ngược lại. Lý do đo được: RRF hợp nhất theo HẠNG nên nó bỏ hết thông tin về
   khoảng cách điểm — khi một bộ chắc chắn hơn bộ kia rất nhiều thì hợp nhất **kéo bộ tốt xuống**.
   Kết quả được báo đúng như đo được, không chỉnh `k` cho ra số đẹp.
3. **Tập niêm phong ĐÃ DÙNG HẾT.** Ghi trong `retrieval_split.json` (`sealed_opened: true`, kèm
   ngày). Từ nay con số trên 40 ca đó không còn là held-out, và câu hỏi tiếp theo cần một tập MỚI.

### Theo họ — chỗ duy nhất thấy được hai phương pháp mạnh ở đâu khác nhau

| họ | ca | bm25 | embedding | hybrid |
|---|---|---|---|---|
| kb-collision | 4 | 1,000 | 1,000 | 1,000 |
| kb-flavour | 12 | 0,583 | 0,583 | **0,667** |
| kb-ingredient | 20 | 0,550 | **0,600** | **0,600** |
| kb-method | 20 | **0,650** | 0,500 | 0,600 |
| kb-occasion | 12 | 0,417 | **0,750** | 0,500 |
| kb-region | 20 | 0,500 | **0,650** | 0,600 |
| kb-section | 2 | 1,000 | 1,000 | 1,000 |
| kb-number · kb-out-of-scope · kb-verbatim-topic | 8 | *(abstain 8/8)* | *(abstain 8/8)* | *(abstain 8/8)* |

Giả thuyết ban đầu — "BM25 thắng ở câu dùng đúng từ, embedding thắng ở câu diễn đạt khác" — **đúng
một phần**: embedding hơn hẳn ở `kb-occasion` (+0,333) và `kb-region` (+0,150), BM25 hơn ở
`kb-method` (+0,150). Nhưng nó không sạch sẽ như câu nói đó gợi ra, và tỷ lệ chung che mất điều đó.

### Vì sao `forbidden@5` quan trọng hơn Hit@5

Hit@5 = 1,0 **vẫn đúng** khi bộ truy hồi trả 1 đoạn đúng cùng 4 đoạn lạc đề. Với hệ thống này thì
4 đoạn lạc đề là 4 cơ hội để mô hình viết ra một câu sai về nhà hàng. Và ba họ chốt đo điều Hit@k
không đo được: **biết khi nào KHÔNG trả lời**. Một bộ luôn trả về 5 đoạn không bao giờ "trượt" —
nó chỉ trả sai.

Đo được sự khác biệt đó: embedding **luôn** cho điểm cho mọi đoạn nên nó luôn trả đủ 5; BM25 trả
RỖNG khi không chung từ nào. Cả hai vẫn đạt abstain 8/8 vì tiêu chí là *không lấy đoạn bị cấm*,
nhưng cơ chế khác nhau — và nếu kho lớn hơn thì khác biệt đó sẽ hiện thành số.

---

## 3. Chọn món — bài toán chứng minh KHÔNG phải chỗ nào cũng nên dùng RAG

8 ca, mỗi ca có một lý do riêng để có mặt (in ra khi chạy). Khóa đáp án là **điều kiện**, giải ra
danh sách món khi chạy.

| phương pháp | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | **cấm@5** | p50 |
|---|---|---|---|---|---|---|
| bm25 | 0,500 | 0,750 | 0,604 | 0,538 | 6/8 | 0,4 ms |
| embedding | 0,500 | 0,750 | 0,594 | 0,431 | 7/8 | 48,0 ms |
| hybrid | 0,375 | 0,875 | 0,573 | 0,525 | 6/8 | 46,3 ms |
| **lọc theo nhãn** | **1,000** | **1,000** | **1,000** | **1,000** | **0/8** | 0,3 ms |

`cấm@5` ở bài toán này = số ca nêu một món **không thỏa ràng buộc**. Đó là câu trả lời **SAI**,
không phải kém. Ba cách xếp hạng sai ở 6–7 trong 8 ca; lọc theo nhãn sai ở 0.

Bốn lý do, đo được từng ca:

| ca | vì sao xếp hạng theo độ tương đồng thua |
|---|---|
| `pick-price-01/02` | **không hiểu SỐ.** "50.000" với BM25 là một từ, không phải một lượng |
| `pick-spice-01` | **phủ định.** "món KHÔNG cay" và "món cay" chung gần hết từ |
| `pick-allergen-01` | **cần LOẠI TRỪ.** Câu chứa chữ "hải sản" nên cả hai kéo món hải sản LÊN ĐẦU — đúng ngược điều khách cần. Đây là ca an toàn |
| `pick-combo-01` | **hai ràng buộc cùng lúc.** Xếp hạng không có phép AND |

Một dự án chỉ đo bài toán tri thức sẽ kết luận "dùng RAG cho mọi thứ". Bảng này là lý do hệ thống
**không** dùng RAG cho việc chọn món, và lý do đó là một con số chứ không phải một ý kiến.

### Quyết định về `ai/requirements.txt`

Embedding thắng phép so nhưng **không** được đưa vào phụ thuộc của dịch vụ. Nó nằm riêng ở
`ai/requirements-rag.txt`. Ba lý do, đo được:

1. **Đường mà embedding phục vụ chưa có ai gọi.** `answer.py` trả lời câu chính sách bằng **tra
   khóa** trên 24 chủ đề `verbatim` — chính xác tuyệt đối, 0 ms. 425 đoạn `synthesize` là đầu vào
   cho mô hình VIẾT, và đường đó chưa dựng.
2. **Chậm hơn 75 lần** (0,7 ms → 53,1 ms), để đổi lấy **0 ca đúng thêm** trên đường hiện tại.
3. **Ảnh Docker +2–3GB.** Bước 5 đã bỏ chính nhóm thư viện này sau khi đo rằng 24 chủ đề không cần.

Điều kiện để nhập vào, ghi ra để lần sau không phải đoán: **khi đường `synthesize` được dựng.** Lúc
đó +21 điểm Hit@5 thành lợi ích thật.

---

## 4. Phân tích nguyên nhân sai — `analyze_failures.py`

Yêu cầu "phân tích cả những trường hợp sai cho biết rõ lý do vì sao" viết tay được **đúng một
lần**. Lần sửa sau thì bảng trong báo cáo thành sai, và không ai biết. Nên nó là công cụ.

Nó đọc **cả ba tập**, và việc gộp cả ba là cố ý: tập 119 ca hiện 0 đỏ, nên một công cụ chỉ đọc tập
đó sẽ in "không có gì để phân tích" và người đọc kết luận hệ thống không còn chỗ sai. Chọn tập là
cách dễ nhất để một báo cáo nói dối mà không câu nào sai.

### Kế hoạch nêu SÁU lớp. Phép đo chỉ ra lớp thứ BẢY.

| lớp | nghĩa | ca hiện tại |
|---|---|---|
| `vocab_miss` | từ vựng không có cụm khách dùng | 0 |
| `retrieval_miss` | lấy sai đoạn, hoặc không lấy được đoạn nào | 46 (bằng embedding) |
| `constraint_conflict` | ràng buộc xung đột → kết quả rỗng | 0 |
| `data_gap` | dữ liệu không có | 0 |
| `criterion_too_strict` | **tiêu chí của CA sai, không phải hệ thống sai** | 0 |
| `model_error` | mô hình đọc sai ràng buộc | 0 |
| **`capability_missing`** | **khả năng CHƯA ĐƯỢC DỰNG** | 0 *(đã dựng — xem mục 6)* |

Lớp thứ bảy được thêm vì gán sai lớp thì công cụ **chỉ người sau đi sửa sai chỗ**. Cụ thể: 9 lượt
tham chiếu ngược ban đầu bị xếp `vocab_miss`, nhưng thêm bao nhiêu cụm vào từ vựng cũng không sửa
được — hệ thống không lưu **dãy có thứ tự** các món đã nêu, nên "món đầu tiên" không có gì để trỏ
vào. Sửa nhãn lớp là sửa hướng đi của người đọc báo cáo.

Công cụ dùng bộ truy hồi **tốt nhất có mặt** và IN RA tên bộ đó. Phân tích bằng bộ kém nhất là
phóng đại số ca sai: cùng tập ca, BM25 cho 64 ca không đạt còn embedding cho 46.

---

## 5. Bốn phép đo đã phải làm lại

Cả bốn đều **không làm chương trình lỗi và không làm test đỏ** — nên chúng chỉ lộ ra khi đọc lại
từng ca, hoặc khi chạy thật.

### 5.1 Gán cho mô hình công của việc bù khiếm khuyết ở nơi khác

Phép đo cho 108/119 tất định và mô hình +11 ca; kết luận ghi ra là **"đó là giá trị đo được của
mô hình sinh"**. Con số đúng, kết luận sai: 11 ca kia đỏ vì bảng từ vựng thiếu cụm (*"chua chua"*,
*"tập gym"*, *"trời nóng"*, *"cụ già… dễ tiêu"*). Thêm 23 cụm → cả 11 về mã tất định, mô hình +0.

**Cách tránh:** xem TỪNG ca đỏ, không xem hiệu số hai cột. Hiệu số nói "có cải thiện"; chỉ từng ca
nói "cải thiện đó là gì".

**Còn phải nói cho đủ:** "mô hình đóng góp 0" **không** chứng minh nó vô dụng. Tập đánh giá do
người làm viết nên nó không chứa cách nói chưa ai nghĩ ra — mà đó lại đúng là chỗ mô hình dùng để
làm gì.
Kết luận trung thực: *giá trị của mô hình trên tập này bằng 0; giá trị với khách thật thì tập này
**không đo được**.* Nên nó được giữ nhưng tắt được bằng một cờ, và số nền không phụ thuộc nó.

### 5.2 Ablation gán mức mất cho phương pháp không có cơ chế đó

Bảng ablation bản đầu in cả ba phương pháp cho mọi cơ chế, nên nó có những dòng như:

```
tắt chuẩn hóa vector    bm25    +0.000   <-- KHÔNG mất gì, cơ chế này DƯ
```

BM25 **không có vector nào để chuẩn hóa**. Dòng đó không nói gì mà lại đọc như một kết luận. Tệ
hơn: "tắt rút dấu" sửa VĂN BẢN của đoạn, nên embedding cũng bị ảnh hưởng và bảng báo "tắt rút dấu
làm embedding mất 0,011" — rút dấu là cơ chế **tách từ của BM25**, embedding không dùng nó.

**Đã sửa:** mỗi cơ chế khai rõ nó thuộc phương pháp nào, và `fold_accents=False` chỉ đổi văn bản
BM25 thấy.

Bảng đúng:

| cơ chế bị tắt | phương pháp | Hit@5 | cấm@5 | mất | nhận xét |
|---|---|---|---|---|---|
| *(bản đầy đủ)* | bm25 | 0,568 | 12 | | |
| *(bản đầy đủ)* | embedding | 0,625 | 11 | | |
| tắt rút dấu | bm25 | 0,534 | 12 | −0,034 | cơ chế ĐÁNG GIỮ |
| tắt rút dấu | hybrid | 0,614 | 13 | +0,000 | không đổi → hybrid bị embedding chi phối |
| tắt chuẩn hóa L2 | embedding | 0,625 | 11 | +0,000 | **cơ chế DƯ với kho này** |
| tắt tiền tố E5 | embedding | 0,648 | 13 | +0,023 | Hit@5 TĂNG nhưng cấm@5 tăng +2 |

Hai kết quả trái với chú thích đã viết trong mã:

- **Chuẩn hóa L2 không mất gì.** Vector của `multilingual-e5-small` đã gần chuẩn đơn vị, nên phép
  chuẩn hóa không đổi thứ tự. Chú thích ghi "không chuẩn hóa thì đoạn DÀI được lợi thế" — đúng về
  lý thuyết, **sai với mô hình này**.
- **Tắt tiền tố E5 làm Hit@5 TĂNG.** Chú thích ghi "thiếu tiền tố thì vẫn chạy, chỉ kém đi". Sai.

Nhưng công cụ **không** kết luận "tắt đi tốt hơn" ở dòng cuối, vì `cấm@5` tăng từ 11 lên 13: bộ
truy hồi lấy được nhiều đoạn đúng hơn **kèm** nhiều đoạn lạc đề hơn. `forbidden@5` đã được đặt làm
chỉ số quyết định, nên kết luận phải dùng nó — một công cụ kết luận theo Hit@5 ở đó là công cụ nói
ngược lại thước đo mà chính nó đặt ra.

### 5.3 Ca ĐẠT SAI LÝ DO, và tiêu chí quá lỏng hai lần liền

Lượt "còn món nào giống vậy không?" **đạt** tiêu chí `refers_to_turn` (phải nhắc tên món của lượt
trước) — nhưng nó đạt vì hệ thống **in lại đúng danh sách cũ**. Với câu hỏi này, câu trả lời đúng
nêu món **khác**, nên đòi nhắc lại tên cũ là đòi **ngược**.

Sửa lần một: đổi sang "không lặp + chung một nhãn với lượt trước". Vẫn đạt sai lý do —
`season:all_year` gắn cho **69/91 món**, nên hai món bất kỳ gần như luôn chung một nhãn.

Sửa lần hai: "không lặp + **thỏa đúng ràng buộc của lượt được trỏ**". Ca chuyển sang đỏ, và đó là
kết quả đúng.

**Một ca đạt sai lý do tệ hơn một ca đỏ**, vì nó báo là đã bao phủ.

### 5.4 Mã chết ở bước 2 vì `reference_index` chỉ có ở bước 3

Để câu "món thứ hai có **hải sản** không?" được đọc là *hỏi về một món* thay vì *duyệt danh mục
hải sản*, bản đầu thêm `request.reference_index is not None` vào điều kiện ở **bước 2** của
`understand()`. Nhưng `reference_index` chỉ được đặt ở **bước 3**, khi vòng khớp từ vựng chạy. Ở
bước 2 nó luôn là `None`.

Không test nào đỏ. Chỉ có một ca vẫn sai, và nếu không chạy lại tập kịch bản thì bản sửa đó trông
như đã xong. Đây là lần thứ **sáu** lớp lỗi *"tệp có mặt khác nó chạy"* xuất hiện trong dự án này.

**Đã sửa:** `REFERENCE_PHRASES` sinh **từ `VOCAB`** (không viết tay — viết tay thì thêm cụm ở trên
mà quên thêm ở đây) và kiểm ở bước 2.

---

## 6. Tham chiếu ngược — khả năng mà công cụ chỉ ra là còn thiếu

`analyze_failures.py` xếp 9 lượt vào `capability_missing`. Ba cơ chế được dựng, và chúng **không
gộp được**:

| cơ chế | câu ví dụ | làm gì |
|---|---|---|
| `reference_index` | "món đầu tiên giá bao nhiêu?" | giải ra **một** món từ `last_listed_ids` |
| `scope_last_listed` | "món rẻ nhất **trong số đó**" | thu **phạm vi** về danh sách vừa nêu |
| `wants_similar` | "còn món nào **giống vậy**" | giữ ràng buộc, **BỎ** món đã nêu |

Gộp thành một cờ là chỗ dễ sai nhất: "món rẻ nhất trong số đó" cần *phạm vi* chứ không cần *một
món* — dùng cơ chế thứ nhất ở đó sẽ trả món ĐẦU danh sách thay vì món RẺ NHẤT. Còn "giống vậy" cần
đúng **ngược lại** của việc trỏ vào món cũ.

Hai trường mới trong `SessionState`, và khác nhau ở chỗ cốt lõi:

```
suggested_item_ids   TẬP tích lũy cả phiên, dùng để KHÔNG gợi lại.  Thứ tự vô nghĩa.
last_listed_ids      DÃY của MỘT lượt, dùng để TRỎ VÀO.             Thứ tự là tất cả.
```

Gộp hai thứ này là lý do tham chiếu ngược không làm được: "món đầu tiên" trong một tập tích lũy 24
món qua 6 lượt thì không trỏ vào đâu cả.

`reference_index` giải thành `named_items` ở bước **hợp nhất bộ nhớ**, không ở `answer.py`. Nên nó
tái dùng nguyên ba nhánh đã có và đã đo (`price_lookup`, `item_detail`, `allergen_named_dish`) thay
vì thêm nhánh thứ bảy — thêm nhánh thì phải đo lại cả sáu nhánh cũ.

Đo được: **9/9 lượt** chuyển từ khoảng cách sang đạt, `allergy_persists` giữ 25/25, 119 ca một lượt
giữ 122/122.

### Cờ `aspirational` đã BỎ, và bỏ nó là bắt buộc

Nhóm `context_reference` từng được đánh `aspirational: true` — "được phép đỏ, đo khoảng cách". Sau
khi khả năng được dựng và 9/9 đạt, cờ đó bị bỏ. Giữ "được phép đỏ" cho một khả năng **đã chạy**
nghĩa là lần sau nó hỏng thì tập ca báo *"khoảng cách"* chứ không báo *"tụt"* — tức không ai biết.

---

## 7. Ba chỗ khác đã sửa, và một tiêu chí đã đổi

**Lượt không đo gì.** 6 lượt của nhóm `constraint_overrides` có `expect` chỉ gồm `why` — không tiêu
chí nào, nên chúng **luôn qua**. `run_session_eval.py::_kiem_tieu_chi` giờ CHẶN hình dạng đó, cùng
với khóa `expect` viết sai tên (một tiêu chí sai tên khóa thì không bao giờ chạy và ca lặng lẽ luôn
xanh — bản trước của tập truy hồi có 96 khóa trỏ sai chỗ suốt nhiều tháng vì đúng cơ chế đó).

Tiêu chí lượt 1 quan trọng hơn nó trông: không kiểm rằng ràng buộc **đã vào** bộ nhớ thì lượt 2
xanh không phân biệt được hai trường hợp trái ngược — *"ghi đè đúng"* và *"không nhớ gì cả"*.

**Nêu tên món trong câu "chưa có dữ liệu".** Bản đầu thêm tên món vào câu no_data để khách biết hệ
thống đang nói về món nào. Thước đo đỏ đúng ở `O-nodata-01`: một ca "chưa có dữ liệu" **không được
nêu món** — nêu món ở đó đọc như một lời mời. Sửa thành: nêu tên **chỉ khi** khách trỏ bằng tham
chiếu ("món đó"), không nêu khi khách tự gõ tên (họ đã biết mình hỏi món nào).

**Một TIÊU CHÍ đã đổi, và lý do không phụ thuộc hệ thống làm gì.** Ca "món đó cho mấy người ăn?"
trước đòi `expect_kind: fact`. Thực đơn **không có dữ liệu khẩu phần**: nhóm nhãn `serving` chỉ có
`takeaway` (11 món), `hot` (1), `preorder` (12). Nên câu trả lời đúng là "chưa có dữ liệu", và một
tiêu chí đòi `fact` là tiêu chí đòi hệ thống **bịa ra con số**. Ca vẫn ở lại tập vì nó chốt rằng hệ
thống nói ra chỗ mình không biết — và vẫn nêu TÊN món để khách phát hiện nếu "món đó" bị hiểu sai.

Đổi tiêu chí là việc dễ bị dùng để làm đẹp số liệu, nên lý do được ghi ngay trong bộ sinh.

---

## 9. Bốn lỗi mà CHẠY THẬT tìm ra sau khi mọi test đã xanh

Ở thời điểm đó — 229 test xanh, 119/119 ca trả lời, 65/65 lượt phiên, 0 lỗi an toàn — việc chạy sáu lượt
qua backend thật vẫn tìm ra **bốn lỗi**. Cả bốn đều nằm ngoài tầm của tập ca đang có, và mỗi lỗi đã
trở thành một ca mới — nếu không nó sẽ quay lại.

### 9.1 Một câu `fact` phá dãy món mà khách còn đang trỏ vào

```
lượt 1  "cho mình món chay"             -> danh sách 6 món
lượt 2  "món đầu tiên giá bao nhiêu?"   -> fact, 1 món  -> dãy CÒN 1 MÓN
lượt 3  "món thứ hai có hải sản không?" -> "thứ hai" ngoài phạm vi -> liệt kê lại danh sách mới
```

`update_state` thay `last_listed_ids` mỗi khi lượt có nêu món — kể cả câu `fact` về **một** món.
Nhưng khách ở lượt 3 vẫn đang nói về danh sách của lượt 1; họ không coi một câu trả lời về một món
là một danh sách mới.

**Vì sao 25 kịch bản không bắt được:** mọi kịch bản `context_reference` chỉ có **MỘT** lượt tham
chiếu. Chuỗi hai lượt tham chiếu liên tiếp chưa từng được chạy.

**Sửa:** thay dãy chỉ khi `reply_kind == "list"`. Tham số `reply_kind` **không có giá trị mặc
định** — mặc định sẽ che đúng lỗi mà nó tồn tại để sửa.

**Ca mới:** nhóm `chained_reference` (3 kịch bản / 9 lượt). Đo hai chiều: với bản sửa 0 lượt đỏ,
bỏ bản sửa ra **3 lượt đỏ**.

**Và tiêu chí đầu của nhóm này QUÁ LỎNG** — lần thứ ba trong bước này. Với `refers_to_turn` ("phải
nhắc một món của lượt 1"), chỉ 1 trong 3 kịch bản bắt được lỗi: hai kịch bản kia **đạt sai lý do**
vì hệ thống không hiểu thì nó liệt kê lại danh sách cũ, và danh sách đó *chứa* tên món của lượt 1.
Phải thay bằng `refers_to_position` — đòi nhắc **đúng** món ở vị trí đó **và không nhắc món nào
khác**. Sau đó 3/3 bắt được.

### 9.2 Câu HỎI bị ghi vào bộ nhớ thành lời KHAI dị ứng

```
lượt 1  "Cơm gà Hội An có hải sản không?"  -> hỏi về thành phần MỘT món
lượt 2  "gợi ý món ăn giúp mình"           -> 26/91 món bị ẩn, và câu trả lời mở đầu bằng
                                              "thực đơn không ghi nhận thành phần bạn cần tránh"
```

Cả câu KHAI và câu HỎI đều sinh `avoid_tags` — và **phải cùng sinh**, vì để trả lời "món này có hải
sản không?" thì hệ thống cần biết nhãn hải sản. Nhưng bộ nhớ ghi cả hai như nhau, nên một câu hỏi tò
mò trở thành một ràng buộc suốt phiên, và hệ thống **khẳng định một điều khách chưa hề nói**.

**Vì sao đây KHÔNG phải nới ràng buộc an toàn:** nới là bỏ một điều khách **đã** khai. Ở đây không
có lời khai nào để bỏ — có một câu hỏi, và nó đã được trả lời đầy đủ.

**Sửa:** `Request.declared_avoidance` tách "khai" khỏi "hỏi"; `update_state` ghi dị nguyên của lượt
này vào bộ nhớ **chỉ khi** lượt đó khai. Nhãn đã có trong bộ nhớ thì giữ **vô điều kiện** — chốt an
toàn không đổi.

**Ca mới:** nhóm `question_not_declaration` (2 kịch bản / 8 lượt), đo **cả hai chiều**: câu hỏi
không được vào bộ nhớ, **và** câu khai vẫn phải vào và giữ. Không có chiều thứ hai thì bản sửa
chiều thứ nhất có thể phá chốt an toàn mà tập ca vẫn xanh. Với bản sửa 0 lượt đỏ, bỏ bản sửa ra
**4 lượt đỏ**.

### 9.3 Lỗi CHỮ trong câu khách đọc

```
"Mình chỉ đọc được phần thực đơn ghi, nên Bạn nhắc nhân viên…"
```

`STAFF_NOTE` bắt đầu bằng chữ B hoa và bị nối sau từ "nên". Thước đo chấm **đúng/sai về dữ liệu** —
món có thật không, giá đúng không, có lọt món cần tránh không — nên nó không chấm câu có đọc được
hay không. Câu này qua được mọi ca đánh giá.

**Ca mới:** `CauChuKHACHDOCTHAY` trong `test_answer.py` — quét **toàn bộ** câu trả lời của 119 ca:
chữ hoa giữa câu, khoảng trắng/dấu câu lặp, câu không có dấu kết. Quét toàn bộ chứ không vài ca mẫu,
vì lỗi chữ nằm ở nhánh nào thì chỉ ca đi qua nhánh đó mới lộ.

### 9.4 `last_listed_ids` không đi qua backend

Tham chiếu ngược chạy hoàn hảo trong bộ chạy kịch bản (nó giữ `SessionState` trong biến) nhưng sẽ
**mất sạch** trong hệ thống thật: mỗi lượt qua backend là một vòng
`session_updates -> JSON -> Postgres -> from_payload`, và khóa nào không có trong `constraints` thì
không sống qua vòng đó.

**Sửa:** thêm `last_listed_ids` và `last_categories` vào `session_updates()["constraints"]`. Không
cần đổi hợp đồng backend và không cần migration — `ChatAiProvider.ExtractSessionUpdates` copy **mọi**
khóa của dict đó vào `constraints_json` rồi trả lại nguyên vẹn.

**Ca mới:** 3 test trong `test_session.py`, gồm **chiều nghịch** (bỏ khóa ra thì MẤT) — không có
chiều nghịch thì test thuận cũng xanh với một hệ thống truyền dãy món qua đường khác, và ta không
biết đường nào đang giữ nó.

### Điều bốn lỗi này nói chung

Ba trong bốn lỗi là **lỗi khách nhìn thấy** (mất chỗ trỏ, mất 26 lựa chọn, chữ hoa giữa câu), và
không lỗi nào là lỗi an toàn — chốt fail-closed giữ 0 lỗi qua tất cả. Nhưng chúng nói một điều về
phương pháp: **tập ca kiểm đúng những gì người viết nghĩ ra để kiểm.** Một cuộc hội thoại thật có
những chuỗi không ai nghĩ tới, nên chạy thật không thay được bằng test — và ngược lại, mỗi lỗi tìm
được khi chạy thật phải trở thành một ca.

Xác nhận cuối qua backend thật (sau khi sửa cả bốn): tham chiếu ngược trỏ đúng món ở cả hai lượt,
**0 món hải sản lọt qua 5 lượt** trong đó 4 lượt không nhắc dị ứng.

---

## 11. Chấm giỏ hàng làm lộ hai lỗi sâu hơn chính nó

Đưa 6 bất biến giỏ hàng vào thước đo (mục 1) là một thay đổi ở **thước đo**, không ở hệ thống. Nó
làm lộ hai chỗ mà không phép đo nào trước đó chạm tới.

### 11.1 Thước đo KHÔNG so `kind` — nên câu liệt kê món được tính là "hỏi lại"

Với ca `kind: clarify`, thước đo chỉ kiểm `asks_back` và độ dài chữ ≥ 30. Nên một câu **liệt kê 6
món rồi hỏi "bạn muốn xem thêm không?"** thỏa cả hai và ĐẠT.

Đây đúng lớp lỗi bản cũ đã mắc và đã ghi lại: *tỷ lệ hỏi lại đọc ra 43% vì câu trả lời liệt kê món
rồi mời thêm bị tính là hỏi lại.* Lần đó sửa bằng cách chỉ xét `asks_back` ở ca `clarify` — nhưng
không ai thêm phép so `kind`, nên lỗ vẫn còn ở chiều ngược.

Đo trước khi bịt: **0/122 ca lệch `kind`** ở chế độ tất định. Nên phép kiểm `kind_matches` không
nới cũng không siết con số hiện tại — nó chặn một đường tụt trong tương lai. Và nó cần thiết vì lỗ
này bị **phép kiểm giỏ bắt hộ**, tức bắt tình cờ: đổi phép kiểm giỏ thì lỗ mở lại.

### 11.2 Mô hình đoán `wants` biến câu mơ hồ thành 6 món tùy ý

Ca duy nhất mô hình làm **TỤT** trong 122 ca, và nó vô hình cho tới khi thẻ giỏ được chấm:

```
"Cho mình 2 món"   (khách nêu SỐ LƯỢNG, không nêu loại)
  mã tất định  -> clarify, hỏi lại: "bạn muốn món ăn hay đồ uống, đi mấy người, tầm giá nào?"
  có mô hình   -> mô hình trả `wants: food` -> hệ thống LIỆT KÊ 6 món ăn bất kỳ + 3 thẻ giỏ
```

`wants` một mình là ràng buộc **yếu** — thu 56/91 món ăn hoặc 21/91 đồ uống — nhưng nó **đủ** để
`answer.py` thôi hỏi lại. Nên một `wants` do mô hình *đoán* làm hệ thống trả lời tự tin bằng một
phỏng đoán, và điều đó tệ hơn nói không biết.

**Cách sửa sai đã thử và bị loại bằng số:** "bỏ `wants` khỏi điều kiện thôi hỏi lại" — đo được nó
phá **5 ca** (`F-foodonly-01/02/03`, `F-drink-01`, `P-stillvague-01`), vì khi khách **nói** "món ăn"
thì gợi ý mới là đúng. Tập ca nói rõ điều đó.

Nên khác biệt không nằm ở `wants` mà ở **ai đặt nó**. Hai câu cho ra `Request` giống hệt nhau sau
khi qua mô hình:

| câu | ai đặt `wants` | trả lời đúng |
|---|---|---|
| "Tư vấn cho mình vài món ăn đi" | **khách nói** | gợi ý |
| "Cho mình 2 món" | **mô hình đoán** | hỏi lại |

Sửa bằng `Request.wants_from_model` — chỉ `enrich()` đặt cờ này, và `answer.py` không tính `wants`
có cờ vào "khách đã nói gì". Mô hình vẫn dùng `wants` để LỌC bình thường khi có ràng buộc khác đi
cùng; chỉ chặn đúng một chuyện: nó không được một mình thay lời khách.

Sau khi sửa: **122/122 ở cả hai chế độ**, mô hình làm tụt 0 ca.

Đây cũng là vấn đề `P-season-01` đã được ghi là mở từ trước — *"hiểu một phần tệ hơn không hiểu
gì, vì nó không kích hoạt hỏi lại và trả lời tự tin"*. Nó không tự sửa được cho tới khi có một ca
đo được nó, và ca đó đến từ việc chấm thẻ giỏ.

---

## 12. Đường `synthesize` — 303 đoạn tri thức trước đó không ai với tới

Trước bản này, **60/60 chủ đề `synthesize` không có đường nào từ câu khách**. Kho 303 đoạn tồn tại,
được kiểm, được dùng làm nguyên liệu cho phép so truy hồi — và không nhánh trả lời nào đọc nó.

### Khảo sát làm đổi thiết kế: 48/60 tài liệu KHÔNG nên đi đường này

| loại | số tài liệu | nhánh đúng | vì sao |
|---|---|---|---|
| `derived` (hương vị, vùng miền, cách chế biến, nguyên liệu…) | 48 | **nhánh lọc** | với "món bò có gì", liệt kê món bò thật hữu ích hơn một đoạn văn về nhóm nhãn `ingredient:beef` |
| `written` | 12 | **nhánh tri thức** | combo, ghép đồ uống, khẩu phần, cách gọi món — nhánh lọc không trả lời được |

Nên đường này phục vụ **11 chủ đề**, không phải 60. Chủ đề thứ 12 — `budget_planning` — cũng bị
loại, và bằng số: câu "Hai người 300 nghìn thì gọi được những gì?" hiện trả **danh sách món**, và
đó **đúng hơn** một đoạn văn về bốn mức giá. Khách nêu con số cụ thể thì họ muốn món.

### Trạng thái ĐO ĐƯỢC trước khi dựng: 10/10 sai

```
4 câu -> clarify    hỏi lại trong khi câu trả lời NẰM TRONG REPO
4 câu -> filter     trả danh sách món cho một câu hỏi tri thức
1 câu -> no_data    "chưa có dữ liệu" trong khi tài liệu có nội dung
1 câu -> sai chủ đề hỏi "gọi bao nhiêu món" mà trả về SỐ MÓN của thực đơn (91 món, 13 nhóm)
```

Không ca nào trong 122 ca cũ bắt được, vì không ca nào hỏi những câu này.

### Thiết kế: tra khóa tìm TÀI LIỆU, xếp hạng chọn ĐOẠN

```
understand.py   nhận chủ đề bằng TỪ VỰNG (tra khóa) -> knowledge_topic
answer.py       xếp hạng TRONG PHẠM VI tài liệu đó -> chọn 1 đoạn -> trả NGUYÊN VĂN
```

Không dùng ngưỡng tương đồng ở đâu cả. Chủ đề đã được nhận ra bằng tra khóa nên phần xếp hạng
**không quyết định trả lời về cái gì**, chỉ quyết định *mục nào của tài liệu đó* — phạm vi 3–8 đoạn
thay vì 303. Và câu trả lời là đoạn **nguyên văn**, không nhờ mô hình viết lại: một chữ số lệch
trong câu về nhà hàng là sai sự thật, cùng lý do với 24 chủ đề `verbatim`.

Từ vựng: **33 cụm, đo trước khi thêm** — 33/33 an toàn, **0/122 ca đổi**, và con số phải canh là
**0 ca dạng `list` bị đổi**. Dự án đã ghi rõ nguy cơ: *"Gộp hai loại thì câu 'món nào không cay' sẽ
trả về một đoạn văn thay vì danh sách món."* Xác nhận qua backend thật: câu đó vẫn trả danh sách món.

### Chọn đoạn trong tài liệu: nhận phần có nguyên tắc, từ chối phần chỉ hơn 1 ca

Hai lỗi lộ ra khi đo 10 câu:

1. **Đoạn MỞ ĐẦU bị chọn** ở 2 câu. 55/425 đoạn là mở đầu (`heading` rỗng) và chúng mô tả *tài
   liệu* — "Tài liệu này nói về cách ghép các món…" — nên không trả lời câu nào. **Loại chúng khỏi
   tập ứng viên.** Đây là quy tắc **cấu trúc**, không phải chỉnh tham số, nên nó không cần đo để
   biện minh — nhưng vẫn đo, và nó sửa đúng 2 ca.

2. **BM25 bị đoạn dài lấn**: "Có set bữa trưa nào không?" nhận mục *"Bảy món lẩu"* (133 từ) thay vì
   *"Bữa trưa cần gì"* (96 từ).

Chiến lược "ưu tiên mục có TIÊU ĐỀ trùng nhiều từ với câu hỏi nhất" sửa được lỗi 2 và đạt **6/7 so
với 5/7**. **Không nhận**, vì hai lý do đo được:

- **n = 7 thì một ca lệch là 14%.** Dự án có luật riêng cho chuyện này: *"Con số phải kèm `n` —
  120 ca thì một ca lệch là 0,8%."* Chọn chiến lược trên 7 điểm dữ liệu với biên 1 ca là đúng thứ
  luật đó tồn tại để tránh.
- Trên 3 câu **chưa có khóa đáp án**, nó chọn đoạn **kém hơn ở 2 câu**.

Ghi lại trong `answer.py::_knowledge_chunk` kèm điều kiện xét lại: cần tập ca **đủ lớn** cho việc
chọn đoạn, không phải cảm giác rằng tiêu đề là tín hiệu tốt.

### Tiêu chí ca: không ghim đoạn nào, nhưng chặn hoàn toàn việc bịa

`knowledge_chunk_topic` đòi câu trả lời chứa **nguyên văn một đoạn** của tài liệu đó — không chỉ
định đoạn nào. Ghim đoạn vào ca sẽ biến ca thành phép kiểm **cài đặt**: đổi chiến lược chọn đoạn là
ca đỏ dù câu trả lời vẫn đúng. Điều ca chốt quan trọng hơn: câu trả lời **không thể tự viết ra**.

10 ca mới, họ `knowledge_multi_section`. **132/132** ở cả hai chế độ.

### Và đường này lộ ra một khẳng định SAI của chính dự án

Chủ đề `serving_size` được dựng với lý do *"thực đơn không có dữ liệu khẩu phần"*, dựa trên việc
nhóm `serving` chỉ có `takeaway`/`hot`/`preorder`. Lý do đó **bỏ sót nhóm `party`**:

```
party:solo        "Cá nhân"
party:two_three   "2-3 người"
party:three_five  "3-5 người"      -> phủ 91/91 món
```

Chính dự án này dùng `party` làm **ràng buộc cứng** vì độ phủ 91/91. Nên hệ thống nói "chưa có dữ
liệu" cho một câu mà dữ liệu **có** — và một ca đánh giá đã bị **sửa tiêu chí theo cái sai đó**
(`no_data` thay vì `fact`).

Đó là điều tệ hơn cả lỗi ban đầu: **một tiêu chí bị sửa theo kết luận sai thì nó khóa cái sai lại**,
và ca trở thành bằng chứng rằng hệ thống đúng khi nói "không biết". Xem một nhóm nhãn rồi kết luận
về cả thực đơn là lỗi đọc dữ liệu, và **tiêu chí đánh giá là chỗ nó sống lâu nhất**.

Đã sửa: `serving_size` bị bỏ; câu về khẩu phần **một món** trả lời từ nhãn `party:*` của chính món
(`branch=serving_named_dish`), câu về khẩu phần **chung** đi tri thức `portion_timing`. Tiêu chí ca
kịch bản trả về `fact`, và cả hai lần đổi được ghi lại trong bộ sinh.

### Embedding vẫn KHÔNG vào ảnh Docker

Đường `synthesize` đã dựng, nhưng nó dùng **BM25 trong phạm vi 3–8 đoạn**, không phải embedding
trên 425 đoạn. Phạm vi nhỏ và các mục khác nhau ở **từ khóa** ("khẩu phần" / "thời gian chờ" /
"mang đi") — đúng chỗ BM25 mạnh. Nên điều kiện ghi trong `ai/requirements-rag.txt` **vẫn chưa
thỏa**: chưa có đường nào cần xếp hạng trên toàn kho.

---

## 8. Hạn chế của bước này

1. **Tập niêm phong truy hồi đã dùng hết** (2026-07-30). Câu hỏi tiếp theo cần tập MỚI.
2. **CI chỉ chạy BM25.** `sentence-transformers` + torch ≈ 2–3GB mỗi lần chạy. Con số của embedding
   đo tại máy, ghi ở mục 2 kèm ngày. Bỏ qua **không âm thầm**: bộ so in rõ đã bỏ qua và vì sao, và
   nó vẫn CHẶN nếu BM25 phạm nhóm chốt.
3. ~~**`last_listed_ids` không đi qua backend.**~~ **Đã sửa** — xem mục 9.4. Nó đi vòng tròn qua
   `constraints`, không cần đổi hợp đồng backend và không cần migration. Đã xác nhận qua backend
   thật, có 3 test chốt gồm một chiều nghịch.
4. ~~**`season:cooling` chỉ gắn cho 2/56 món ăn.**~~ **Đã sửa** — xem mục 10.
5. **Kho tri thức: 52/108 tài liệu là `demo`.** Chúng không thể sai về **con số** (số lấy từ thực
   đơn) nhưng có thể sai về **chính sách**, và chỉ chủ nhà hàng biết.
6. **Không có log khách thật.** Mọi ca do người viết. Con số đo được hệ thống có tôn trọng ràng
   buộc hay không; nó **không** đo được khách thật hỏi gì.

---

## 10. Lấp khiếm khuyết gắn nhãn mùa — bằng bản rà, không bằng tay

Phép so truy hồi làm lộ một khiếm khuyết dữ liệu: `season:cooling` gắn cho **5 đồ uống nhưng chỉ
2/56 món ăn**. Nên câu "trời nóng quá, ăn gì cho mát người" — câu hoàn toàn bình thường — lọc theo
`cooling` chỉ còn **2 món**, sát ngưỡng đến mức một món đổi nhãn là mất câu trả lời.

Cách xử lý đi theo đúng tiền lệ của bước 1 với nhãn dị nguyên: **viết bản rà đối chiếu nhãn với mô
tả món**, không chọn tay từng món. Chọn tay thì không kiểm lại được, và cũng không ai biết lần sau
nhãn có trôi hay không.

### `ai/scripts/audit_season_tags.py` — rà HAI CHIỀU

| chiều | bắt gì | vì sao cần |
|---|---|---|
| **thiếu nhãn** | mô tả có bằng chứng mà món không mang nhãn | đây là khiếm khuyết đã đo được |
| **nhãn lạ** | món mang nhãn mà mô tả không có bằng chứng nào | không có chiều này thì cách "sửa" dễ nhất là gắn nhãn cho thật nhiều món, bản rà luôn sạch mà nhãn thành vô nghĩa |

Bản rà thừa hưởng ba bài học của bản rà dị nguyên: khớp theo **biên từ** (không chuỗi con), bỏ qua
**câu phủ định**, và **ghi rõ vì sao** mỗi cụm là bằng chứng.

### Kết quả đầu tiên: 10 chỗ, và 7 trong 10 là DƯƠNG TÍNH GIẢ

Đây là phần đáng ghi lại. Bản rà **không** tự sửa dữ liệu, và lần này lý do đó trả lãi ngay:

| món | cụm khớp | đọc mô tả thì thấy | quyết định |
|---|---|---|---|
| Trà sen Tây Hồ | "thanh mát" | mô tả ghi **"Hãm nóng trong ấm sứ"** — "thanh mát" là HẬU VỊ | không gắn |
| Chè bưởi | "ăn lạnh" | ghi "Ăn lạnh **hoặc nóng**" — không dứt khoát | không gắn |
| Cà phê sữa đá | "đá viên" | ghi "Caffeine cao, phù hợp buổi sáng" — món tỉnh táo | không gắn |
| Cà phê dừa | "đá viên" | nhấn "béo ngậy", không nói gì về giải nhiệt | không gắn |
| Bia Hà Nội · Bia hơi · Cocktail | "thanh mát" / "tươi mát" | mô tả **VỊ**, không mô tả chức năng | không gắn |

Hai cụm phủ định (`hãm nóng`, `ăn lạnh hoặc nóng`) được **thêm vào bản rà** nên lần sau chúng bị
bắt tự động. Năm món còn lại vào `DA_XET_GIU_NGUYEN` kèm lý do — cùng vai với `NOT_ALLERGENS` của
bản rà dị nguyên: một phán đoán của người, ghi ra để đọc lại và bác được, thay vì để bản rà báo mãi
một chỗ mà không ai biết đã xem chưa.

Không từ khóa nào phân biệt được *"thanh mát" mô tả vị* với *"thanh mát" mô tả chức năng*. Chỗ đó
cần người đọc, và điều bản rà làm được là **thu 91 món xuống 10 chỗ để đọc**.

### Ba lỗ thật đã lấp

```
Gỏi cuốn tôm thịt         "Cuốn TƯƠI MÁT ... ít dầu mỡ"
Bánh tráng cuốn thịt heo  "THANH MÁT, không dầu mỡ. PHÙ HỢP MÙA NÓNG"
Đĩa trái cây theo mùa     "Đĩa trái cây tươi ... TƯƠI MÁT, giàu vitamin"
```

Cả ba có bằng chứng ngay trong mô tả **của chính món**, không phải suy từ ca đánh giá. Đó là ranh
giới giữa *sửa lỗi dữ liệu* và *chỉnh dữ liệu cho vừa thước đo*.

`season:cooling` món ăn: **2 → 4**. Bản rà cũng tìm ra hai lỗi của **chính nó**: "ăn nóng" bị dùng
làm bằng chứng cho `cold_season` (nhiệt độ phục vụ **không phải** tính mùa — gần như mọi món Việt
đều phục vụ nóng, nên một bằng chứng đúng với gần hết thực đơn không phân biệt được gì), và bốn món
lẩu/cháo/súp mang `cold_season` mà bằng chứng là **LOẠI món** chứ không phải chữ. Không thêm "lẩu"
vào danh sách bằng chứng, vì đo được: 7 món lẩu thì 3 mang `cold_season` và 4 mang `all_year` — tức
người gắn nhãn đã phân biệt có ý, và một từ khóa "lẩu" sẽ biến lựa chọn đó thành 4 lỗi giả.

### Hệ quả: từ vựng tách được theo ĐÚNG nghĩa nhãn

Trước đó cả ba cụm nóng gộp vào `season:hot_season`, và lý do là **độ bao** chứ không phải nghĩa.
Sau khi lấp lỗ thì lý do đó không còn:

```
"trời nóng"                        -> season:hot_season   (nhãn "Mùa nóng")
"cho mát", "mát người", "giải nhiệt" -> season:cooling      (nhãn "Giải nhiệt")
```

Câu "Trời nóng quá, ăn gì cho mát người" giờ cho `require = [hot_season, cooling]`, và phép AND ra
**3 món** — nhiều hơn **cả hai** phương án gộp trước đó (2 và 4 nhưng lệch nghĩa). Nhãn mùa không
nằm trong `exclusive_groups` nên một món mang được cả hai, và đó là lý do phép AND ở đây không triệt
tiêu.

Ba câu đo được sau khi sửa:

| câu | require | nêu ra |
|---|---|---|
| "Trời nóng quá, ăn gì cho mát người" | `hot_season` + `cooling` | 3 món, tất cả là món cuốn/gỏi/canh mát |
| "Có nước gì giải nhiệt không?" | `cooling` | 5 đồ uống, tất cả đúng |
| "Trời lạnh thế này ăn gì cho ấm" | `cold_season` | 6 món lẩu/cháo/tiềm |

122/122 ca, 82/82 lượt phiên, 0 lỗi an toàn — không ca nào tụt. Bản rà nằm trong CI.

---

## 13. Ba lỗi mà mọi thước đo đều xanh: khi dữ liệu đúng mà câu trả lời sai

Ba lỗi này tìm ra bằng cách gọi **backend thật + mô hình thật** và hỏi những câu không có trong tập
nào: câu bịa món, câu bịa giá, câu ngoài phạm vi. Ở thời điểm đó 132/132 ca, 82/82 lượt, 0 lỗi an
toàn, 244 test xanh, CI 4/4 xanh.

Điểm chung của cả ba — và là lý do không thước đo nào bắt được:

> Mọi tên món và mọi con số trong câu trả lời đều **có thật trong thực đơn**. Không có gì bị bịa.
> Nhưng khách đọc ra một điều **sai**.

Các phép kiểm chống bịa (`items_exist`, `prices_grounded`, `cart_grounded`, `forbid_invented_items`)
đo *nguồn gốc* của dữ liệu, không đo *sự thật* của câu. Khoảng cách giữa hai thứ đó là chỗ ba lỗi
này nằm.

### 13.1 Giá khách khẳng định bị lưu thành ngân sách phiên

| | |
|---|---|
| Câu hỏi | "Phở bò tái nạm giá 45.000đ đúng không?" |
| Nhận được | danh sách các món 45.000đ |
| Vì sao | mọi con số ≥1.000 trong câu đều thành `budget_max`, kể cả khi khách đang **khẳng định giá một món**, không nêu ngân sách |
| Hậu quả thật | 45.000đ vào bộ nhớ phiên và **dính lại**: lượt sau "Món đắt nhất giá bao nhiêu?" trả lời "Cháo lòng Sài Gòn, 45.000đ" |
| Sửa | `Request.asserted_price`, đặt khi câu có **tên món** và lối nói khẳng định ("đúng không", "phải không"). Nhánh mới `price_assertion` đính chính theo thực đơn |
| Đo bằng | `O-premise-01/02/03` (cả ba chiều) và `price-premise-01` với tiêu chí `memory_budget_max: null` |

Luật này **hẹp có chủ đích**: không có tên món thì con số vẫn là ngân sách. `O-premise-03` ("Có món
nào dưới 45.000đ đúng không?") là ca chốt sự hẹp đó — cùng lối nói "đúng không", nhưng vẫn phải trả
về danh sách.

### 13.2 Câu cực trị không nói ra phạm vi của nó

"Món đắt nhất là Cháo lòng Sài Gòn, giá 45.000đ" là khẳng định **tuyệt đối**, và nó chỉ đúng trong
ngân sách đang có hiệu lực. Sửa: so số món trong phạm vi với cả thực đơn, hẹp hơn thì mở đầu bằng
"Trong phạm vi bạn nêu". Đo bằng số món chứ không dò xem ràng buộc nào đang bật, nên thêm ràng buộc
mới về sau không phải sửa lại chỗ này.

Bản sửa đầu của tôi dùng `str.capitalize()` cho chiều không thu hẹp, và nó **hạ chữ tên món**:
"tôm hùm nướng mỡ hành". Tiêu chí `must_name_item` bắt được, vì nó tra tên từ thực đơn theo mã món
thay vì so một chuỗi viết tay.

### 13.3 Câu ngoài phạm vi rơi vào nhánh hỏi lại

"Thủ đô nước Pháp là gì?", "2 cộng 2 bằng mấy?", "Giải thích thuật toán Dijkstra", "Nhà hàng bên
cạnh có ngon không?" — cả bốn nhận về câu hỏi lại "bạn muốn món ăn hay đồ uống, đi mấy người…".

**Điều quan trọng nhất của mục này:** trợ lý chưa bao giờ trả lời được những câu đó, kể cả trước khi
sửa. `service.py` trả về `reply.text`, và `reply.text` luôn do `answer.py` dựng từ thực đơn và kho
tri thức — mô hình **không có đường ghi chữ** cho khách. Bảo đảm không bịa là bảo đảm **cấu trúc**,
không phải bảo đảm bằng danh sách từ khóa.

Việc còn thiếu chỉ là **nói ra** rằng câu đó ngoài phạm vi. Hai bản sửa:

1. Nhánh hỏi lại nêu phạm vi trước: "Mình tư vấn món ăn và đồ uống của nhà hàng ạ. Để gợi ý đúng ý
   bạn…" — phục vụ cả câu mơ hồ đúng chủ đề lẫn câu ngoài phạm vi mà từ khóa không bắt được, không
   cần phân loại câu hỏi.
2. Thêm cụm cho kiến thức chung / lập trình / nơi khác, và **mẫu** cho phép tính.

Danh sách từ khóa không phủ hết kiến thức chung, và không có cách nào phủ hết. Nó được ghi ra như
vậy chứ không được trình bày như một lớp chặn đầy đủ.

### 13.4 Hai lỗi sinh ra từ chính bản sửa

**Từ chối oan.** Cụm `doi thu` (đối thủ) nằm trong "đổi thử món khác" sau khi rút dấu, nên một câu
đổi món bị từ chối. Cả 132 ca lẫn 82 lượt vẫn xanh — không tập nào nói "đổi thử". Bỏ cụm đó: mất khả
năng nhận câu hỏi về đối thủ là **giá đúng phải trả**, vì từ chối oan khách đang chọn món tệ hơn
nhiều. Test `test_khong_tu_choi_oan_cau_dung_chu_de` giữ giá đó ở trạng thái đo được.

**Cơ chế sai loại.** Cụm `cong bang may` khớp "2 cộng bằng mấy?" nhưng **không** khớp "2 cộng 2 bằng
mấy?" — có con số ở giữa. Phép thử cục bộ của tôi dùng câu không số nên nó xanh; phép thử qua backend
dùng câu có số nên nó đỏ. Cùng cơ chế, hai cách viết câu, hai kết quả — dấu hiệu **cơ chế sai loại**,
không phải thiếu cụm. Thay bằng `ARITHMETIC_RE` đòi hai con số kẹp một phép tính: 0/9 câu về món bị
bắt oan.

Mẫu **chỉ** nhận phép tính viết bằng chữ cộng `x`. `fold()` bỏ `+ - * /` nên "3+4" thành "3 4",
không phân biệt được với "gọi 3 4 món". Nên "3+4 = ?" **không** bị chặn — giới hạn có thật, và
`test_phep_tinh_viet_bang_ky_hieu_khong_chan_duoc` giữ nó ở trạng thái đo được thay vì để một nhánh
ký hiệu trông như đang chạy.

### 13.5 Ba lỗ hổng trong chính bộ đo, lộ ra khi thêm tiêu chí

| Lỗ | Hậu quả nếu để nguyên |
|---|---|
| `validate_cases.py` không chặn khóa `expect` lạ ở cấp trên | tôi viết `min_items` (khóa đúng là `require_min`) và ca sẽ lặng lẽ xanh với một tiêu chí không bao giờ chạy |
| `memory_budget_max` dùng `.get(...) is not None` | tiêu chí `memory_budget_max: null` — "bộ nhớ phải KHÔNG có ngân sách", đúng chiều cần cho lỗi 13.1 — bị **bỏ qua im lặng** |
| `extreme-scope-02` giải thích rằng nó chặn bản "luôn thêm trong phạm vi", nhưng không tiêu chí nào kiểm **sự vắng mặt** | lời giải thích nói một việc, bộ chạy làm việc khác; ca xanh với cả hai bản |

Cả ba là cùng một lớp lỗi: **tiêu chí không chạy tệ hơn không có tiêu chí**, vì nó làm bảng kết quả
trông như đã kiểm. Nay có hàng rào `EXPECT_KEYS_THE_METRIC_RUNS`, `in exp` thay cho `.get()`, và
tiêu chí `must_not_say_any`.

Và tiêu chí mới **không** được tin bằng cách đọc mã. Bốn phép đột biến, mỗi phép phá một điều:

| Đột biến | Lượt đỏ đúng chỗ |
|---|---|
| luôn thêm "Trong phạm vi bạn nêu" | `extreme-scope-02` — `must_not_say_any` |
| bỏ cụm "trong phạm vi" khỏi mọi câu | `extreme-scope-01` — `must_say_all` |
| đổi mọi số tiền thành 1đ | `extreme-scope-01` — thiếu `95.000đ` |
| xóa tên món khỏi câu trả lời | 18 lượt, gồm cả ba kịch bản mới — `must_name_item` |

Một tiêu chí thêm nữa phải sửa trước khi dùng: chốt "phải nhắc Bún đậu mắm tôm" cho ngưỡng 100.000đ
phụ thuộc **thứ tự phá hòa** — có 5 món cùng giá 95.000đ. Ca đỏ sai lý do cũng tệ như ca xanh sai lý
do. Nay bộ sinh chốt **giá** khi có hòa, chốt **món** khi giá cực trị duy nhất, và `raise SystemExit`
nếu điều kiện duy nhất đó mất.

### 13.6 Kết quả

| | trước | sau |
|---|---|---|
| ca trả lời | 132/132 | **140/140** (8 ca mới: 4 tiền đề giá, 5 ngoài phạm vi — trong đó 1 ca chống từ chối oan) |
| lượt phiên | 82/82 | **87/87** (nhóm mới `extreme_scope`, 5 lượt) |
| test `ai/app` | 244 | **249** |
| lỗi an toàn | 0 | **0** ở cả hai chế độ |
| chạy thật qua backend + mô hình | 3/8 câu sai | **8/8 đúng** trên phiên sạch |

8 ca mới **không** phải held-out: chúng được viết từ lỗi quan sát được rồi đo ngay. Tập niêm phong
đã dùng hết từ trước, và điều này không đổi kết luận đó.

**Còn một chỗ chưa đóng:** "Có món bò Wagyu A5 không?" trả về các món bò khác mà **không nói** thực
đơn không có Wagyu. Nó không xác nhận Wagyu tồn tại, nên không bịa — nhưng nó yếu hơn cách xử lý
"sushi cá hồi Na Uy", vốn trả lời "thực đơn chưa có món đó". Khác nhau vì `NOT_ON_MENU` là một **danh
sách tường minh** và Wagyu không có trong đó. Cơ chế này cố ý hẹp: cơ chế đoán tên món lạ trước đây
bắt oan bốn ca khai dị ứng. Nới nó ra cần một cách đo, không phải một danh sách dài hơn.

---

## 14. Golden test đầu-cuối — chặng mà không tập nào đi tới

Ba lỗi ở mục 13 tìm ra bằng script tạm trong thư mục nháp. Script đó **không commit được**, nên phát
hiện thì có mà khả năng lặp lại thì không. `run_golden_e2e.py` là bản đàng hoàng của nó.

Chuỗi gọi thật có 6 chặng, và mỗi tập cũ dừng ở một chặng khác nhau:

| Chặng | Ai kiểm |
|---|---|
| `understand()` + `respond()` gọi trực tiếp | 140 ca `cases.json` |
| + bộ nhớ nhiều lượt, vẫn trong tiến trình | 87 lượt `session_scripts.json` |
| + mô hình (trong tiến trình, dùng cache) | `run_with_model.py` |
| + HTTP tới dịch vụ AI | 29 test `test_service.py` (`TestClient`) |
| + backend .NET gọi dịch vụ AI | `AiContractBoundaryTests` — kiểm **hợp đồng**, provider giả |
| **QR → phiên bàn → phiên chat → backend → AI → mô hình → thẻ giỏ → giỏ hàng thật** | `run_golden_e2e.py`, job CI `golden-e2e` |

**13 hội thoại / 42 lượt** (bảng năng lực ở 14.3). Kết quả **42/42** qua backend, ở cả hai cấu
hình mô hình.

### 14.1 Bảy bất biến thẻ giỏ, áp cho MỌI lượt

Áp cho mọi lượt chứ không khai từng lượt: tiêu chí khai lẻ là chỗ sinh ra lượt không được kiểm.

1. món trong thẻ **tồn tại** trong thực đơn
2. tên trong thẻ **khớp** tên thực đơn
3. giá trong thẻ **là** giá thực đơn
4. **món trong thẻ là món câu trả lời VỪA NÊU**
5. số lượng là số dương
6. luôn đòi khách xác nhận — AI không tự đặt món
7. nhánh chưa hiểu câu hỏi thì **không** có thẻ

Bất biến 4 là bất biến đáng nhất. Ba cái đầu chỉ nói thẻ trỏ vào món có thật với giá đúng — chúng
**vẫn xanh** nếu trợ lý tư vấn món A rồi bỏ món B vào thẻ. Mà đó chính là kiểu sai khách chịu thiệt:
bấm "thêm vào giỏ" là tin rằng nó thêm đúng món vừa được gợi ý.

Và một lượt **bấm thêm vào giỏ thật**, rồi đọc lại giỏ để xác nhận món đã vào. Đây là điều không
mảng JSON nào kiểm được: thẻ giỏ có đi qua được đường xác thực và ràng buộc của backend hay không.

### 14.2 Ba lỗi của chính bộ này, cả ba do gọi thật mà lộ

| Lỗi | Vì sao |
|---|---|
| `POST /cart/items` trả 400 `CART_DELTA_INVALID` | trường là `delta`, không phải `quantity` — endpoint CỘNG THÊM vào giỏ |
| rồi trả 401 `TABLE_SESSION_TOKEN_INVALID` | header cần **token** của phiên bàn (`tableSessionToken`), không phải id phiên |
| câu tri thức bị đọc thành `list` | bản đầu đếm tên món trong văn xuôi; câu ghép đồ uống nhắc "Trà đào cam sả" và "trà sen" nên thành hai món |

Hai lỗi đầu là đúng loại lỗi bộ này tồn tại để bắt — hợp đồng thật khác hợp đồng tôi tưởng — chỉ có
điều lần này nó bắt tôi. Lỗi thứ ba sửa bằng cách đọc dạng đáp án từ **số thẻ giỏ** và cụm mở đầu,
không từ số tên món: đếm tên món không phân biệt được "đây là các món tôi gợi ý" với "tôi đang nói
VỀ các món này". Việc đếm tên món vẫn giữ ở phép kiểm an toàn, và ở đó nó đúng — một món hải sản
nhắc trong văn xuôi vẫn là món hải sản đã lọt tới mắt khách dị ứng.

### 14.3 Mở rộng lên 13 hội thoại / 42 lượt, và nó tìm ra một lỗi CHẶN PHÁT HÀNH

5 hội thoại đầu chốt lại ba lỗi ở mục 13. Chúng **không** đủ rộng để đánh giá trợ lý, nên tập được
mở lên 13 hội thoại / 42 lượt, mỗi hội thoại phủ một năng lực:

| Hội thoại | Năng lực |
|---|---|
| `khach-di-ung-hai-san` | chốt an toàn qua đủ 6 chặng, kết bằng bấm thêm vào giỏ thật |
| `khach-hoi-gia-va-tien-de-sai` | ba lỗi mục 13, trong đúng thứ tự đã xảy ra |
| `khach-hoi-ngoai-pham-vi` | kiến thức chung, phép tính, dò chỉ dẫn nội bộ, và **chống từ chối oan** |
| `khach-hoi-mon-khong-co` | chặn bịa món, hai chiều |
| `khach-hoi-tri-thuc` | đường tri thức, trả nguyên văn đoạn có thật |
| `khach-hoi-mon-an-khong-phai-do-uong` | **món ăn khác đồ uống**, và không lặp món |
| `khach-tro-vao-mon-da-neu` | tham chiếu ngược theo VỊ TRÍ, và tham chiếu chuỗi |
| `khach-siet-ngan-sach` | ràng buộc cùng nhóm GHI ĐÈ, không cộng dồn |
| `khach-so-sanh-hai-mon` | so sánh, và câu so sánh TIẾP NỐI |
| `khach-hoi-do-cay-va-an-chay` | ba vụ đụng chữ, qua đủ chuỗi gọi |
| `khach-hoi-thu-thuc-don-khong-co` | ba loại dữ liệu thực đơn không chứa |
| `khach-hoi-chinh-sach-nha-hang` | câu chính sách, và vụ đụng chữ "mở cửa" chứa "cua" |
| `khach-di-ung-qua-duong-stream` | **đường SSE** — đường CHÍNH của khách |

Lần chạy đầu: **6 lượt đỏ**.

#### Lỗi chặn phát hành: đường SSE của khách luôn trả câu xin lỗi

| | |
|---|---|
| Hiện tượng | mọi lượt qua SSE nhận "Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé." |
| Vì sao nghiêm trọng | `ChatbotPage.tsx` gọi `sendMessageStream` **trước**, chỉ lùi về `sendMessage` khi stream lỗi. Đây là đường chính, nên **mọi câu trả lời thật đi qua dịch vụ AI đều thành câu xin lỗi** |
| Nguyên nhân | dịch vụ AI phát `data: {"delta": ...}` **không kèm dòng `event:`**; `ChatAiProvider.GenerateStreamAsync` bỏ qua mọi dòng `data:` khi `eventName` còn rỗng. Toàn bộ stream bị hủy, `finalPayload` null |
| Vì sao không test nào bắt | cả hai bên **tự nhất quán với chính mình**: `test_service.py` kiểm khung tự định, `ChatAiProviderV2ContractTests` kiểm bộ đọc của backend. Hai khung khác nhau, không tập nào nối hai bên |
| Sửa ở đâu | ở **dịch vụ AI**, không ở bộ đọc backend — đúng bài học đã ghi tại `require_token`: hợp đồng do BÊN GỌI định |

Một chi tiết đáng ghi: đúng lúc đó có một lượt SSE **xanh**, và nó xanh vì backend lấy đường
`CatalogReply` fast-path nên không gọi dịch vụ AI. Nếu tập chỉ có một lượt SSE thì kết luận sẽ ngược
hẳn.

#### Ba lỗi ngữ cảnh, tất cả tái hiện được trong tiến trình

| Câu | Nhận được | Nguyên nhân | Sửa |
|---|---|---|---|
| "Cho mình món khác đi" | **y nguyên** danh sách cũ | cụm không có trong từ vựng, rơi vào nhánh lọc thường | cụm vào `similar`; loại **cả tập đã gợi trong phiên**, không chỉ lượt cuối |
| "Món thứ hai có cay không?" rồi "Món đó bao nhiêu tiền?" | trả lời về món **thứ nhất** | từ vựng gán "món đó" bằng vị trí 1 | `last_focus_id`; vị trí là cách trỏ khi khách **đếm**, "món đó" trỏ vào **tiêu điểm** |
| "Món nào cay hơn?" sau một câu so sánh | hỏi lại | mất cặp món | `last_compared_ids`; danh sách cụm **không** chứa "rẻ hơn"/"ít hơn" vì ba cụm đó là cách nói siết ngân sách |

Nhóm `no_repeat` của bộ chạy phiên vẫn **xanh 10/10** suốt thời gian lỗi thứ nhất tồn tại: tiêu chí
của nó chỉ kiểm bộ nhớ có **ghi** món đã gợi, không kiểm danh sách có **đổi** — dù `why` của nó nói
đúng điều đó. Ca đạt sai lý do, lần thứ tư trong dự án.

#### Hai hồi quy do chính bản sửa, cả hai bị bắt ngay

- Chuyển "cái đó" từ loại `reference` sang cờ làm `REFERENCE_PHRASES` hụt đi, nên "Cái đó có cay
  không?" không còn được đọc là câu hỏi về một món, và `context-reference-02` đỏ. Tập đó nay sinh từ
  **cả hai** điều kiện.
- Nhánh `item_detail` đòi `reference_index is not None`; cờ tiêu điểm cần đúng ngoại lệ đó, vì
  `require_tags` kéo từ bộ nhớ làm điều kiện "không có ràng buộc" sai.

#### Bất biến mới: thêm trường bộ nhớ là phải có đường đi vòng

`last_focus_id` và `last_compared_ids` chạy đúng trong tiến trình và **sai qua backend** — chúng
thiếu khóa trong `session_updates()["constraints"]`. 87 lượt phiên vẫn xanh, vì bộ chạy kịch bản giữ
`SessionState` trong một biến nên nó không đi qua vòng JSON.

Đây là lần **thứ hai** đúng lớp lỗi này trong cùng một tệp (lần đầu: `last_listed_ids`). Nên hàng rào
không kiểm một trường cụ thể mà kiểm **mọi trường**:
`test_MOI_truong_bo_nho_deu_song_qua_vong_JSON`. Danh sách miễn phải khai tường minh kèm lý do.

#### Ba lỗi của chính bộ golden, cả ba do gọi thật mà lộ

| Lỗi | Vì sao |
|---|---|
| 400 `CART_DELTA_INVALID` | trường là `delta`, không phải `quantity` — endpoint CỘNG THÊM vào giỏ |
| 401 `TABLE_SESSION_TOKEN_INVALID` | header cần `tableSessionToken`, không phải id phiên |
| câu tri thức bị đọc thành `list` | đếm tên món trong văn xuôi; câu ghép đồ uống nhắc hai tên trà |

Cộng một khiếm khuyết **thiết kế**: bản đầu mở phiên chat qua `tableSessionId`, mà
`CreateOrGetSession` trả lại phiên **cũ** cho cùng phiên bàn, nên mỗi hội thoại ăn một bàn sạch và
bộ **chỉ chạy được một lần trên mỗi cơ sở dữ liệu**. Không truyền `tableSessionId` thì phiên luôn
trắng. Nay chạy lại được vô hạn và chỉ cần **một** mã QR, cho bước thêm vào giỏ.

#### Chỗ hở Wagyu: đóng được

"Có món bò Wagyu A5 không?" từng trả về các món bò khác mà **không nói** thực đơn không có Wagyu —
yếu hơn hẳn cách xử lý "sushi cá hồi Na Uy", và khác biệt duy nhất là món kia nằm trong
`NOT_ON_MENU`. Nay `wagyu`, `foie gras`, `truffle`, `caviar` đã vào danh sách đó (không cụm nào nằm
trong 91 tên món, nên không tạo chỗ đụng chữ), và ca golden siết lên `no_data`.

Danh sách vẫn **cố ý hẹp**: cơ chế ĐOÁN tên món lạ đã bị bỏ vì nó bắt oan bốn ca khai dị ứng. Ca
"Có món bò nào không?" là chỗ chốt rằng thêm cụm không phá phép lọc theo nguyên liệu.

### 14.4 Golden ĐÃ vào CI

Job `golden-e2e` dựng stack thật trong runner rồi chạy 42 lượt. Nó **không cần bí mật thật**: mọi
biến đã có ở job `docker-compose-config` dưới dạng chỗ giữ chỗ, và `LLM_BASE_URL` trỏ vào một cổng
không có gì lắng nghe, nên mô hình gọi thất bại ngay và dịch vụ trả lời bằng **mã tất định**.

Đó không phải giới hạn phải chịu, đó là điều đáng kiểm: 140/140 ca đã đạt không cần mô hình, nên
đường tất định phải đi hết chuỗi gọi được. **Đo được: 42/42 ở cả hai cấu hình** — có mô hình thật và
không có mô hình.

`wait_for_stack.py` in ra `model_configured`, nên bản ghi CI nói rõ lớp mô hình có được chạy hay
không, thay vì để người đọc tưởng nó đã được kiểm.

### 14.5 Hai hạn chế phải nói ra

**Lớp mô hình không được CI kiểm.** Job `golden-e2e` chạy trên đường tất định (xem 14.4). Câu
trả lời của hai cấu hình giống nhau ở cả 42 lượt, và `run_with_model.py` cho thấy mô hình đổi 0/140
ca — nhưng "đổi 0 ca trên tập này" không phải "mô hình không thể làm sai". Muốn CI kiểm lớp đó thì
cần một khóa mô hình trong secrets, và đó là quyết định của chủ dự án.

Bù lại: **phần chấm điểm có 28 test chạy không cần stack** (`test_golden_e2e.py`). Một bộ đo mà logic
chấm sai sẽ báo xanh trên hệ thống đang sai, và đó là kiểu hỏng tệ nhất của bộ đo. Trong 28 test đó
có test phá đúng bất biến 4, đúng chiều "ca viết sai chứ không phải hệ thống sai", và bốn hàng rào
cho chính tập golden — gồm hàng rào **chặn khóa `expect` lạ**.

**Dạng đáp án phải SUY RA.** `ChatMessageResponse` chỉ có `Content` và `SuggestedCartActions` —
backend không chuyển tiếp `kind` vì nó không thuộc hợp đồng khách. `cases.json` so `kind` trực tiếp
và chính xác hơn. Đây là hạn chế thật, không phải một lựa chọn tinh tế.

**Mỗi hội thoại cần một bàn riêng, và bộ này DỪNG nếu không đủ.** Backend trả lại phiên chat CŨ cho
cùng phiên bàn — đúng thiết kế, khách quét lại QR giữa bữa thì không mất ngữ cảnh. Dùng chung một
bàn nghĩa là mọi hội thoại chia chung bộ nhớ và số đo được không nói lên điều gì. Đúng chuyện này đã
lừa tôi: tôi tạo "phiên mới" cho từng câu, thấy hệ thống trả lời sai, và mất một lượt điều tra mới
nhận ra ngân sách 45.000đ của lần chạy **trước** còn dính trong bộ nhớ. Nên bộ này không cho phép
cấu hình sai đó tồn tại — thiếu mã QR là thoát mã 2.

Mã thoát 2 ("không gọi được stack") khác mã 1 ("hệ thống sai") có chủ đích: trộn hai thứ đó lại là
cách một bộ đo tự vô hiệu hóa, vì nó sẽ xanh trên máy không có gì chạy.

---

## Chạy lại

```bash
# Golden đầu-cuối — CẦN stack đang chạy, và một mã QR cho MỖI hội thoại
docker compose -f deploy/docker-compose.yml up -d
export GOLDEN_QR_TOKENS=ma1,ma2,ma3,ma4,ma5
python ai/evaluation/run_golden_e2e.py --chi-tiet

# Không cần thư viện ngoài — BM25, và bộ so in rõ đã bỏ qua embedding
python -m unittest test_rag                       # trong ai/app
python ai/evaluation/run_retrieval_comparison.py
python ai/evaluation/analyze_failures.py
python ai/evaluation/run_session_eval.py --chi-tiet
python -m unittest discover -s ai/evaluation -p "test_golden*.py"   # chấm điểm golden, không cần stack
python ai/scripts/audit_season_tags.py            # rà nhãn mùa, hai chiều

# Phép so BA phương pháp (tải ~2–3GB)
python -m pip install -r ai/requirements-rag.txt
python ai/evaluation/run_retrieval_comparison.py --ablation
python ai/evaluation/run_retrieval_comparison.py --latency-protocol release
```

`--sealed` **không** có trong danh sách trên: tập niêm phong đã mở ngày 2026-07-30 và mở lại chỉ
cho một con số không còn nghĩa gì.
