# Ôn tập cho nhóm trưởng — Phạm Duy An (BIT240002)

**Phụ trách:** Dữ liệu (bộ nhãn, kho tri thức) và Hiểu câu hỏi (`understand.py`)

Tài liệu này gồm ba phần: **kiến thức phải nắm**, **giải thích chi tiết phần của bạn**, và **câu hỏi
sẽ bị hỏi** kèm câu trả lời có số.

---

# PHẦN A — KIẾN THỨC PHẢI NẮM

Bạn không cần biết mọi thứ trong dự án. Nhưng **sáu chủ đề dưới đây thì phải nắm chắc**, vì chúng là
phần bạn làm và thầy sẽ hỏi thẳng.

## A1. Vì sao dùng nhãn thay vì để mô hình đọc mô tả món

Mô tả món là câu giới thiệu, không phải dữ liệu có cấu trúc:

> *"Phở bò tái nạm — nước dùng ninh xương 8 tiếng, bánh phở tươi, thịt bò tái mềm."*

Từ câu này mô hình **có thể đoán** món không cay, có gluten, hợp bữa sáng. Nhưng *"có thể đoán"*
không dùng được cho câu *"món nào không có gluten"* — sai một món là khách dị ứng ăn nhầm.

**Nhãn biến phép đoán thành phép tra bảng.** `allergen:gluten` có hoặc không, và câu trả lời truy được
về đúng một trường dữ liệu.

## A2. Không gian tên của khoá nhãn — và vì sao nó bắt buộc

```
spice:none    thay vì    none
```

**Hai lý do, và lý do thứ hai mới là lý do thật:**

1. Rút dấu tiếng Việt làm `hot` của `serving:hot` (nóng) và `hot` của `spice:hot` (cay đậm) thành
   **cùng một chuỗi**.
2. Khoá có nhóm cho phép **ghi đè theo NHÓM** ở bộ nhớ phiên. Khách nói *"không cay"* thì `spice:none`
   phải **đẩy** `spice:hot` ra, chứ không nằm cạnh nó. Không có nhóm thì **không viết được luật đó**.

## A3. Nguyên tắc độ phủ — quyết định nhãn dùng vào việc gì

| Độ phủ | "Thiếu nhãn" nghĩa là | Nhãn dùng để |
|---|---|---|
| **91/91** | **lỗi dữ liệu** | **lọc** — loại món không thoả |
| một phần | **chưa ghi nhận**, không phải *không có* | **sắp thứ tự** — không loại món |

Năm họ phủ đủ: `party`, `meal`, `season`, `spice`, `price`. Hai họ cuối là **độc quyền** — một món chỉ
mang đúng một giá trị.

## A4. Rút dấu tiếng Việt là phép MẤT thông tin

`fold()` cho phép khớp `"mo cua"` với `"mở cửa"` — người Việt gõ không dấu rất thường. Nhưng phần bị
mất **có ý nghĩa phân biệt**: sau khi rút dấu, `"bò"` và `"bơ"` cùng thành `"bo"`.

Cách chặn **không phải** vá từng lỗi, mà là một luật: **khớp cụm dài trước, rồi ăn hết đoạn đã khớp**.

## A5. Ràng buộc khác ngữ cảnh

| Loại | Ví dụ | Hệ quả |
|---|---|---|
| **Ràng buộc** | *"không cay"*, *"dưới 200 nghìn"* | món không thoả bị **LOẠI** |
| **Ngữ cảnh** | *"đi hẹn hò"*, *"trời nóng"* | món hợp chỉ **XẾP LÊN TRƯỚC** |

Nhầm hai thứ này gây một trong hai lỗi: **lọc mất món đúng**, hoặc **để lọt món khách không ăn được**.

## A6. Một kho, hai chế độ trả lời

| Chế độ | Tài liệu | Vào chỉ mục | Mô hình chạm chữ? |
|---|---:|---|---|
| `verbatim` | 24 | **không** | **0%** |
| `synthesize` | 36 | **182 đoạn** | không — chỉ trình bày lại |

Câu *"mấy giờ đóng cửa?"* có **một đáp án đúng duy nhất**. Đưa nó qua mô hình là tạo cơ hội sai ở chỗ
chỉ cần đọc ra một chuỗi.

---

# PHẦN B — GIẢI THÍCH CHI TIẾT PHẦN CỦA BẠN

## B1. Số liệu bạn phải thuộc

| | |
|---|---|
| Thực đơn | **91 món**, 13 danh mục |
| Bộ nhãn | **85 nhãn / 16 họ**, 2 họ độc quyền (`spice`, `price`) |
| Nhãn trên mỗi món | 9–21 |
| Kho tri thức | **60 tài liệu / 213 đoạn**, **182 đoạn** vào chỉ mục |
| Từ vựng | **629 cụm** |
| Cụm có nguy cơ đụng chữ | **107** |
| `allergen` phủ | **44/91 món** |

## B2. Quy trình gán nhãn — bốn bước

| Bước | Việc | Kết quả |
|---|---|---|
| 1 | Kiểm kê thuộc tính có sẵn trong thực đơn gốc | giá, tên, mô tả, nhóm món |
| 2 | Rút thuộc tính **ngầm** từ mô tả món | cay/không cay, chay/mặn, vùng miền, cách chế biến |
| 3 | Hợp nhất **hai nguồn** — JSON của AI và CSDL backend | 85 nhãn, khớp **91/91 món** |
| 4 | Sinh migration để CSDL production đổi theo | chuỗi migration có phiên bản |

**Bước 3 là bước quan trọng nhất.** Thực đơn tồn tại ở hai nơi và chúng **không khớp** lúc đầu. Nếu để
hai nguồn tự do thì **mọi con số của bốn chặng sau đều đo trên dữ liệu sai**.

## B3. Cấu trúc 629 cụm từ vựng

| Loại đích | Số cụm | Ví dụ |
|---|---:|---|
| `require` — thêm nhãn lọc | **214** | *"không cay"* → `spice:none` |
| `policy` — chủ đề chính sách | **146** | *"mấy giờ đóng cửa"* → `hours` |
| `flag` — bật một cờ trong `Request` | **122** | *"món nào rẻ nhất"* → `asks_extreme` |
| `knowledge` — chủ đề tri thức | **36** | *"bốn mức cay"* → `spice_ladder` |
| `category` — danh mục món | **35** | *"đồ uống"* → `cat_drink` |
| `allergen_topic` — chủ đề dị nguyên | **31** | phân biệt HỎI với KHAI |
| `wants` — loại đang muốn | **17** | món ăn / đồ uống |
| `reference` — tham chiếu ngược | **15** | *"món đầu tiên"* |

Trong đó **34 cụm** trỏ tới nhãn `allergen:*` — đây là nhóm nguy hiểm nhất, và cũng là nhóm bạn sẽ bị
hỏi nhiều nhất.

## B4. Luật khớp — dài trước, rồi ăn hết đoạn

Đây là **cơ chế**, không phải danh sách ngoại lệ. Ba va chạm thật:

| Cụm | Va với | Hậu quả | Cách xử |
|---|---|---|---|
| `mi` (mì → gluten) | `mì chính` | *"dị ứng mì chính"* bật nhãn gluten | **thêm cụm `mi chinh`** — luật tự lo phần còn lại |
| `so` (sò → hải sản) | `số`, `sợ` | *"món số 2"* bật nhãn hải sản | **bỏ cụm** — đo 627 câu, **0 câu đổi** |
| `ca` (cá → hải sản) | `cả` | *"có cả ông bà"* bật nhãn hải sản | **GIỮ** — bỏ thì mất hàng rào cho *"dị ứng cá"* |

Dòng thứ nhất là kiểu sửa đúng: **thêm một cụm dài hơn**, luật khớp-dài-trước tự giải quyết.

Dòng thứ ba là **hạn chế còn tồn**, và bạn nên nói thẳng: phân biệt `cả` với `cá` cần ngữ cảnh mà lớp
khớp cụm không có. Đo được: bỏ cụm `ca` làm **1 ca đổi**, và đúng ca quan trọng nhất.

## B5. Bài học đo lường của khâu bạn

**Phải chạy `understand()` thật, không phân tích chuỗi con.**

Một lần phân tích chuỗi thay cho việc chạy hàm cho **17/19 dương tính giả** — vì nó không biết về luật
ăn-hết-đoạn. Nó thấy `mi` nằm trong `mi chinh` và báo va chạm, trong khi hệ thống thật đã khớp
`mi chinh` trước và ăn hết đoạn đó.

## B6. Ba bộ rà nhãn, và giới hạn của chúng

| Bộ rà | Tìm gì | Đã tìm ra |
|---|---|---|
| `audit_allergen_tags.py` | món có nguyên liệu gây dị ứng trong **mô tả** mà thiếu nhãn | **7 lỗ thật**, đã lấp hết |
| `audit_season_tags.py` | mô tả nói "giải nhiệt" mà thiếu `season:cooling` | lỗ dữ liệu |
| `audit_method_tags.py` | tên món tự nói cách chế biến | chạy `--check`, tức **chặn** |

**Giới hạn phải nói rõ:** mô tả món **không phải bảng thành phần**. Bộ rà tìm được chỗ mô tả *có nhắc*
mà nhãn *thiếu*; nó **không** tìm được món có dị nguyên mà mô tả cũng không nhắc.

## B7. Đóng góp lớn nhất của bạn — xoá 49 tài liệu khỏi kho

Kho từng có thêm 49 tài liệu sinh theo nhãn, chiếm **51% chỉ mục**. Bạn bỏ chúng sau một chuỗi đo:

| Bước | Phát hiện |
|---|---|
| 1 | Không đường nào tới chúng ngoài truy hồi — nhánh lọc không đọc kho, và **0/49** khoá chủ đề có trong từ vựng |
| 2 | Câu chúng phục vụ là câu **chọn món** — sau khi bổ sung từ vựng, **99,1%** đi thẳng nhánh lọc |
| 3 | Chúng **làm hỏng** phần truy hồi còn lại — tài liệu điển hình có **0 từ riêng** (văn xuôi viết tay: 2, nhiều nhất 18) |
| 4 | Ba cách chữa đều hoà — reranker p = 0,8238 · gộp p = 0,5488 · cắt mục đưa 0 lên 1 |

**Kết quả:** chỉ mục còn 182 đoạn văn xuôi đồng nhất, nhóm `written` lên Hit@2 **0,879**, `cấm@5` giảm
từ 9 xuống 6.

**Câu chốt khi trình bày:** *"Nội dung mất đi không mất thật — mọi thứ 49 tài liệu ấy nói đều tính được
từ nhãn, và nhánh lọc làm việc đó chính xác 100,00%."*

---

# PHẦN C — CÂU HỎI SẼ BỊ HỎI

Xếp theo **xác suất bị hỏi**, cao xuống thấp.

## C1. *"Em gán 85 nhãn cho 91 món dựa vào cái gì? Có chủ quan không?"*

**Có, và em nói rõ chỗ chủ quan.**

Ba nguồn khác nhau, độ tin khác nhau:

| Nguồn | Nhóm nhãn | Chủ quan? |
|---|---|---|
| trường có sẵn trong thực đơn | `price`, danh mục | **không** |
| tên món tự nói ra | `method` (Gà **nướng** muối ớt), `region` (Phở **Hà Nội**) | rất ít |
| mô tả món | `flavour`, `health`, `allergen` | **có** |

Nhóm thứ ba là nhóm chủ quan, và em xử hai cách:

1. **Bộ rà tự động** đối chiếu nhãn với mô tả — tìm ra 7 lỗ thật ở nhóm `allergen`
2. **Nói ra giới hạn trong chính câu trả lời** — tài liệu `reading_labels` viết thẳng rằng nhãn
   `health:*` là đánh giá cảm quan của người nhập liệu, không phải kết quả phân tích dinh dưỡng

## C2. *"Nhãn dị nguyên chỉ phủ 44/91 món. Vậy hệ thống có an toàn không?"*

**Đây là câu hỏi khó nhất, và câu trả lời phải bắt đầu bằng "không".**

Hệ thống **không** bảo đảm an toàn. Nó bảo đảm ba điều khác:

1. Món **đã ghi nhận** dị nguyên khách nêu thì **tuyệt đối không bao giờ** được nêu — fail-closed
2. Câu trả lời **nói ra giới hạn** — mời khách nhắc nhân viên để bếp xác nhận
3. Có phép kiểm **bắt buộc** câu đó phải có mặt — phép kiểm thứ 8, và nó là **chốt an toàn**

Con số 44/91 nghĩa là **47 món chưa được ghi nhận dị nguyên nào**, không phải *không có*. Danh sách lọc
ra **không phải một kết luận về an toàn** — và hệ thống nói điều đó với khách thay vì im lặng.

**Ví dụ em dùng để chứng minh giới hạn là thật:** *Bún đậu mắm tôm* và *Bún bò Huế* mang
`allergen:seafood` nhưng **không** mang `ingredient:shrimp`, dù chứa tôm — vì mắm tôm và mắm ruốc là
**gia vị**, không được ghi vào nhãn nguyên liệu. Nên hệ thống **chặn rộng ở mức nhóm** thay vì lọc hẹp
theo nguyên liệu.

## C3. *"Vì sao không để mô hình AI đọc câu hỏi luôn, cần gì 629 cụm viết tay?"*

**Ba lý do, và lý do thứ ba mới là lý do thật:**

1. Dịch vụ phải trả lời được **khi mô hình hỏng**
2. Mỗi lần gọi tốn ~8 giây, còn *"xin chào"* thì không đáng chờ 8 giây
3. **Cụm chào hỏi tiếng Việt là tập ĐÓNG và NHỎ** — dùng mô hình cho việc mà một danh sách giải quyết
   trọn là chọn sai công cụ, và làm phép đo phụ thuộc một thứ không tất định

**Bằng chứng cụ thể:** khi thử để mô hình gán nhãn, nó trả `prefer: health:low_calorie` cho câu
*"Nhãn 'ít calo' dựa trên gì?"* — đẩy một **câu hỏi về nhãn** sang **nhánh lọc món**. Khách hỏi định
nghĩa, nhận về danh sách món.

Mô hình **vẫn được dùng**, nhưng chỉ khi mã tất định không chắc, và nó **chỉ trả nhãn** — không chọn
món, không viết câu.

## C4. *"Rút dấu tiếng Việt gây lỗi gì? Em xử thế nào?"*

Rút dấu là phép **mất thông tin**: `"bò"` và `"bơ"` cùng thành `"bo"`.

Ba va chạm thật, và **ba cách xử khác nhau** — đó mới là điểm đáng nói:

```
"dị ứng MÌ CHÍNH"       cụm `mi` khớp giữa   →  THÊM cụm `mi chinh`, luật khớp-dài-trước tự lo
"không ăn được món SỐ 2" cụm `so` khớp        →  BỎ cụm, đo 627 câu → 0 câu đổi
"có CẢ ông bà"          cụm `ca` khớp        →  GIỮ, vì bỏ thì mất hàng rào cho "dị ứng cá"
```

Cách chặn chung **không phải vá từng lỗi** mà là một luật: **khớp cụm dài trước, rồi ăn hết đoạn đã
khớp**. Kiểm kê: **629 cụm, 107 cụm có nguy cơ**, luật này bảo vệ tất cả.

**Nếu thầy hỏi tiếp "còn lỗi nào chưa sửa không":** có — trường hợp `cả`/`cá`. Phân biệt chúng cần ngữ
cảnh mà lớp khớp cụm không có. Em ghi nó vào mục hạn chế thay vì giấu.

## C5. *"Vì sao kho tri thức chia làm hai chế độ? Một chế độ không được sao?"*

Được, nhưng sẽ **thêm rủi ro ở chỗ không cần rủi ro nào**.

Câu *"mấy giờ đóng cửa?"* có một đáp án đúng duy nhất, và **một chữ số lệch là nói sai sự thật về nhà
hàng**. Đưa nó qua mô hình để diễn đạt lại là tạo cơ hội sai cho việc chỉ cần đọc ra một chuỗi.

Hệ quả kiến trúc: **tài liệu `verbatim` KHÔNG nằm trong chỉ mục truy hồi**. Nếu để chúng trong đó thì
có **hai đường tới cùng một nội dung**, và đường xếp hạng có thể trích một câu chính sách ra giữa câu
tư vấn món. Có test chốt điều này.

## C6. *"Em nói xoá 49 tài liệu. Sao lại xoá dữ liệu đi mà bảo là cải thiện?"*

Vì em đo được **chúng không phục vụ đường nào**, và **làm hỏng phần còn lại**.

Bốn bước đo, theo thứ tự:

1. **Không đường nào tới chúng** ngoài truy hồi — nhánh lọc không đọc kho, và 0/49 khoá chủ đề có
   trong từ vựng
2. **Câu chúng phục vụ là câu chọn món** — sau khi bổ sung từ vựng, 99,1% đi thẳng nhánh lọc
3. **Chúng làm loãng chỉ mục** — tài liệu điển hình có **0 từ chỉ xuất hiện ở riêng nó**, vì 49 tài
   liệu dùng chung một khuôn
4. **Ba cách chữa độc lập đều hoà** — reranker p = 0,8238, gộp p = 0,5488, cắt mục đưa 0 lên 1

Khi ba cách chữa độc lập cùng hoà, vấn đề **không nằm ở cách chữa mà ở chẩn đoán**. Thứ trùng lặp là
**chính cái khuôn**, nên cách còn lại là bỏ hẳn.

**Kết quả đo được:** Hit@2 lên **0,879**, `cấm@5` giảm **9 → 6**.

## C7. *"Nếu một nhãn bị gán sai thì chuyện gì xảy ra?"*

Tuỳ nhãn, và đó là lý do em phân ba mức:

| Nhãn sai | Hậu quả |
|---|---|
| `allergen:*` **thiếu** | **lỗi an toàn** — món có dị nguyên lọt vào danh sách |
| `allergen:*` **thừa** | món an toàn bị ẩn — khách mất lựa chọn, không nguy hiểm |
| `spice`, `price` (họ độc quyền, phủ đủ) | lọc sai — câu trả lời sai nhưng không nguy hiểm |
| họ phủ mỏng (`occasion`, `flavour`) | chỉ đổi **thứ tự**, không loại món |

Chiều nguy hiểm là **thiếu nhãn dị nguyên**, và đó là chiều bộ rà nhắm vào.

## C8. *"Em kiểm tra 629 cụm bằng cách nào? Chạy tay từng cụm à?"*

Không. Ba lớp:

1. **Kiểm kê đụng chữ** — quét mọi cặp cụm, đếm cụm nằm trong cụm khác hoặc nằm trong tên món. Con số
   hiện tại: **107/629**. Nó chạy trong CI, nên thêm cụm mới là phải chạy lại.
2. **Ablation** — tắt luật ăn-hết-đoạn rồi đo lại. Mất **4 ca**.
3. **Chạy `understand()` thật trên toàn bộ tập đánh giá** — đây là lớp quan trọng nhất, vì hai lớp trên
   đều là suy luận về mã, còn lớp này là hành vi thật.

**Điểm em phải nói thêm:** con số ablation *"mất 4 ca"* là **chặn dưới**, không phải giá trị thật của
cơ chế — vì tập đánh giá chỉ có ca cho một phần nhỏ trong 107 cụm nguy cơ. Nhóm lấp bằng **chín test
riêng** thay vì để con số nói sai.

## C9. *"Tại sao 8 tài liệu chính sách lại do máy sinh mà không viết tay?"*

Vì **văn xuôi kể lại dữ liệu thì luôn trôi khỏi dữ liệu**.

Một tài liệu viết tay ghi *"hơn 90 món"* trong khi thực đơn có đúng **91** — sai ngay từ lúc viết, và
không ai canh.

Tám tài liệu chứa con số (`menu_size`, `price_range`, `children`, `vegetarian`, …) được sinh lại từ
thực đơn mỗi lần, kèm cổng `--check` trong CI. Nên chúng **không thể lệch**.

Mười sáu tài liệu còn lại là chính sách thật của nhà hàng, không suy được từ thực đơn nên phải viết
tay.

## C10. *"Phần của em phụ thuộc ai, và ai phụ thuộc em?"*

**Em không phụ thuộc ai** — khâu dữ liệu là khâu đầu chuỗi.

**Ba người phụ thuộc em**, và theo thứ tự:

```
em giao BỘ NHÃN + KHO      →  người làm đánh giá viết được toàn bộ tập ca NGAY
em giao Request            →  người làm chọn món và người làm phiên mới bắt đầu được
```

**Chi tiết bàn giao dễ bỏ sót:** phải giao **dữ liệu trước, lớp hiểu câu hỏi sau**. Người làm đánh giá
chỉ cần dữ liệu để viết tập ca — họ không dùng `understand.py`. Giao ngược thứ tự thì họ ngồi chờ
2.417 dòng mã mà mình không cần.

**Và một bất biến chạy vắt qua em với người làm phiên:** mọi `topic_keys` trong kho phải có cụm từ vựng
nhận ra được, và ngược lại — `test_understand.KhoTriThucVaTuVungPhaiKhopNhau`. Em thêm một trường ràng
buộc mới thì **phải báo người làm phiên** nó thuộc nhóm nào trong ba nhóm hợp nhất; thiếu bước đó thì
trường mới **im lặng không được nhớ**.

---

## Ba câu hỏi bẫy, và cách trả lời

### *"Vậy hệ thống của em có dùng AI không, hay chỉ là if-else?"*

Có, và em nói rõ **dùng ở đâu**: trong bảy chặng runtime, **năm chặng là mã tất định**, hai chặng có mô
hình — truy hồi ngữ nghĩa (`bge-m3`, 1024 chiều) và sinh câu trả lời.

Việc phần lớn hệ thống tất định **là kết quả của phép đo**, không phải vì nhóm ngại dùng AI. Đo được:
trên bài toán chọn món, lọc theo nhãn đúng **100,00%** còn ba bộ xếp hạng nêu món vi phạm ở **35–42
trong 50 câu**.

### *"Em có chắc 100% là con số thật không? Nghe hơi đẹp."*

Chắc, và em nói kèm **sàn để so**: cách lách *"luôn nói chưa có dữ liệu"* qua được **8/147** ca. Con số
100% chỉ có nghĩa khi đặt cạnh sàn đó.

Thêm nữa, tập đánh giá có **bộ dò lỗ** kiểm xem một câu trả lời vô nghĩa có qua được ca nào không. Khi
bịt một lỗ, con số nền tụt từ **0,9960 xuống 0,7368** — tức 99,6% kia gần như hoàn toàn ảo.

### *"Nếu bây giờ nhà hàng thêm 50 món nữa thì phải làm lại từ đầu à?"*

Không. Đây là chỗ thiết kế dữ liệu trả công:

| Thứ | Có phải sửa tay không |
|---|---|
| 8 tài liệu chính sách có số | **không** — sinh lại, có `--check` canh |
| khoá đáp án của mọi tập đánh giá | **không** — chúng là **điều kiện**, không phải danh sách |
| bộ nhãn cho 50 món mới | **có** — đây là việc thật, và bộ rà kiểm lại |
| từ vựng | chỉ khi món mới có cách gọi chưa phủ |

Việc phải làm tay là **gán nhãn cho 50 món mới**. Mọi thứ khác tự theo.

---

## Bốn con số phải thuộc lòng

```
91 món · 85 nhãn / 16 họ · 60 tài liệu / 213 đoạn (182 vào chỉ mục) · 629 cụm
allergen phủ 44/91         ← con số quan trọng nhất, vì nó là giới hạn an toàn
107/629 cụm có nguy cơ     ← con số chứng minh em có kiểm, không đoán
7 lỗ nhãn bộ rà tìm ra     ← con số chứng minh bộ rà có tác dụng
0 từ riêng của tài liệu sinh theo nhãn  ← con số dẫn tới quyết định xoá 49 tài liệu
```
