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
| 82 lượt phiên (30 kịch bản / 6 nhóm) | **82/82 (100%)**, 0 khoảng cách | 0 lỗi |
| 138 ca truy hồi | xem bảng dưới | nhóm chốt 8/8 abstain |
| ablation trả lời | 9/9 cơ chế có ít nhất một ca chứng minh | 5 là hàng rào an toàn |
| giỏ hàng gợi ý | 6 bất biến áp cho **cả 122 ca**, 217 thẻ sinh ra | `safety_cart_no_allergen` |

**Mô hình sinh đổi 0 ca.** Trước bước này nó đổi +11 ca, và con số đó từng được ghi là giá trị đo
được của mô hình. Đọc lại 11 ca đỏ thì cả 11 đỏ vì **bảng từ vựng thiếu cụm khách thật sự dùng**.
Thêm 23 cụm đã đo thì cả 11 về mã tất định. Nên "+11 ca nhờ mô hình" **không đo mô hình** — nó đo
độ thiếu của bảng từ vựng. Xem mục 5.1.

---

## 2. Truy hồi tri thức — BM25 vs embedding vs hybrid

Kho: **303 đoạn** `answer_mode: synthesize` (84 tài liệu). Đoạn `verbatim` không vào chỉ mục vì
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
   khóa** trên 24 chủ đề `verbatim` — chính xác tuyệt đối, 0 ms. 303 đoạn `synthesize` là đầu vào
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

## 8. Hạn chế của bước này

1. **Tập niêm phong truy hồi đã dùng hết** (2026-07-30). Câu hỏi tiếp theo cần tập MỚI.
2. **CI chỉ chạy BM25.** `sentence-transformers` + torch ≈ 2–3GB mỗi lần chạy. Con số của embedding
   đo tại máy, ghi ở mục 2 kèm ngày. Bỏ qua **không âm thầm**: bộ so in rõ đã bỏ qua và vì sao, và
   nó vẫn CHẶN nếu BM25 phạm nhóm chốt.
3. ~~**`last_listed_ids` không đi qua backend.**~~ **Đã sửa** — xem mục 9.4. Nó đi vòng tròn qua
   `constraints`, không cần đổi hợp đồng backend và không cần migration. Đã xác nhận qua backend
   thật, có 3 test chốt gồm một chiều nghịch.
4. ~~**`season:cooling` chỉ gắn cho 2/56 món ăn.**~~ **Đã sửa** — xem mục 10.
5. **Kho tri thức: 28/84 tài liệu là `demo`.** Chúng không thể sai về **con số** (số lấy từ thực
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

## Chạy lại

```bash
# Không cần thư viện ngoài — BM25, và bộ so in rõ đã bỏ qua embedding
python -m unittest test_rag                       # trong ai/app
python ai/evaluation/run_retrieval_comparison.py
python ai/evaluation/analyze_failures.py
python ai/evaluation/run_session_eval.py --chi-tiet
python ai/scripts/audit_season_tags.py            # rà nhãn mùa, hai chiều

# Phép so BA phương pháp (tải ~2–3GB)
python -m pip install -r ai/requirements-rag.txt
python ai/evaluation/run_retrieval_comparison.py --ablation
python ai/evaluation/run_retrieval_comparison.py --latency-protocol release
```

`--sealed` **không** có trong danh sách trên: tập niêm phong đã mở ngày 2026-07-30 và mở lại chỉ
cho một con số không còn nghĩa gì.
