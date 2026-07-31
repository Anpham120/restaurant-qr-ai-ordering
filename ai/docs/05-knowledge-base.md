# Bước 5 — Kho tri thức nhà hàng

Câu hỏi mở đầu bước này là "có phải xây lại kho tri thức không". Đo trước khi trả lời:

| | Con số |
|---|---|
| Ca cần kho tri thức | 6/94 khi bắt đầu |
| Chủ đề phần hiểu câu hỏi đã nhận diện đúng | **6/6 (100%)** từ bước 4 |
| Kho tri thức bản cũ | 26 tài liệu, 213 đoạn, so 7 phương pháp truy hồi, ~3GB RAM |
| Thư viện nặng bản dựng lại đang dùng | **0** |

Nên câu trả lời là: **cần nội dung, không cần hệ truy hồi.** Phần truy hồi đã xong từ bước
4 — thiếu duy nhất là câu trả lời cho các chủ đề đã nhận ra.

| Tệp | Việc |
|---|---|
| `ai/knowledge/policy/` | 24 tài liệu `verbatim` — chính sách, trả nguyên văn |
| `ai/knowledge/derived/` | 48 tài liệu `synthesize` — sinh từ nhãn thực đơn |
| `ai/knowledge/written/` | 12 tài liệu `synthesize` — người viết |
| `ai/scripts/build_knowledge.py` | sinh 56 tài liệu `derived`, kiểm cả kho |
| `ai/app/rag/chunker.py` | nạp, chia đoạn, ép `audience` và `answer_mode` |
| `app/answer.py` → `load_facts()` | tra khóa trên tài liệu `verbatim` |

**Trạng thái hiện tại: 108 tài liệu / 449 đoạn** — 24 `verbatim` + 84 `synthesize`; theo nguồn
56 `derived` + 52 `demo`. Bộ truy hồi chỉ xếp hạng **425 đoạn `synthesize`**.

> Cập nhật 2026-07-30: thêm 24 tài liệu `written` có cấu trúc RIÊNG. Nút cổ chai trước đó là 45/60
> tài liệu dùng chung MỘT khuôn, nên mọi tập đánh giá về chọn đoạn đều bị trần bởi kho chứ không
> bởi công sức. Số MỤC có cấu trúc riêng: 62 -> 184.

## 0. MỘT kho, HAI chế độ trả lời

Kho này từng nằm ở **hai chỗ**, và tôi từng biện minh việc tách bằng lý do *"tra khóa vs truy
hồi xếp hạng"*. Lý do đó **sai**: cả 60 tài liệu markdown đều có đúng một `topic_keys` nên
chúng cũng tra khóa được. Cách lấy không phân biệt được gì.

Ranh giới thật luôn là **chế độ trả lời** — mô hình được tin bao nhiêu:

| `answer_mode` | Nội dung tới khách | Dùng cho | Số tài liệu |
|---|---|---|---|
| `verbatim` | **nguyên văn**, mô hình không chạm vào chữ | giờ mở cửa, thanh toán, phụ phí, cách khai dị ứng | 24 |
| `synthesize` | **đầu vào** cho mô hình viết câu trả lời | "đặc sản miền Trung có gì", "gọi bao nhiêu món cho 6 người" | 60 |

Và ranh giới đó **không cần hai kho**. Gộp về một kho được ba thứ:

1. **Xóa một lớp lỗi bằng cấu trúc.** Khi còn hai kho, `answer.py` tra kho thứ nhất trước, nên
   một chủ đề có ở cả hai thì tài liệu kho thứ hai **không bao giờ tới lượt** mà vẫn chiếm chỗ
   trong chỉ mục — im lặng, không lỗi. Một kho thì điều đó *không thể xảy ra*.
2. **Xóa một lỗi đóng gói.** `ai/knowledge/` nằm trong `ai/`, tức trong phạm vi `COPY` của
   Dockerfile. Kho cũ ở `backend/data/` thì không — và trong container cả 24 chủ đề chính sách
   trả "chưa có dữ liệu", im lặng. Xem `ai/app/test_packaging.py`.
3. Một bộ nạp, một bộ kiểm, một bước CI, một chỗ để thêm tri thức.

Điều **không** được gộp là số chế độ trả lời. Cả hai chiều gộp đều mất thật:

- Về `synthesize` → "mấy giờ đóng cửa" do mô hình viết, và nó **có thể** viết 22h30.
- Về `verbatim` → phải nén danh sách nhiều món kèm ghi chú dị nguyên vào một câu viết tay.

Nói gọn: **số kho là chuyện gọn gàng, số chế độ trả lời là chuyện an toàn.**

## 1. Với tài liệu `verbatim`, truy hồi là tra khóa, không phải xếp hạng

Chủ đề đã được nhận diện ở bước hiểu câu hỏi, nên nó **chính là khóa**. Không có embedding,
không có xếp hạng, không có ngưỡng tương đồng — nên không có chỗ nào để chệch.

Bản cũ dựng cả một hệ so sánh 7 phương pháp truy hồi cho bài toán tra 24 khóa. Và nó có
giá thật: 47/221 đoạn tri thức là hướng dẫn dành cho AI đọc, nhưng lại được trích cho
khách, nhiều tháng không ai thấy.

## 2. Hai loại tri thức, hai mức độ tin được

Một kho tri thức trộn "sự thật tính được từ dữ liệu" với "chính sách do người viết" là kho
tri thức không ai biết tin phần nào. Nên mỗi mục khai rõ nguồn:

| Nguồn | Số tài liệu | Tin được đến đâu |
|---|---|---|
| `derived` | 56 | tính từ `menu-dataset.json` mỗi lần sinh lại, **không thể lệch khỏi thực đơn** |
| `demo` | 28 | chính sách nhà hàng và lời khuyên, giá trị mẫu cho dự án demo |

Phần `derived` là chỗ đáng giá nhất, vì nó **không thể sai**: nó *là* thực đơn được diễn
đạt lại. Trong 56 tài liệu `derived` thì 48 là tài liệu nhóm nhãn (`synthesize`), còn **8 là
tài liệu chính sách `verbatim`** — chúng chứa con số nên tuyệt đối không được viết tay:

`menu_size` (91 món / 13 nhóm) · `price_range` (12.000–890.000đ) · `preorder` (12 món) ·
`takeaway_items` (11 món) · `children` (43 món trẻ em, 29 món người lớn tuổi) ·
`vegetarian` (17 món) · `spice_levels` (68 món không cay) · `allergen_labelling`

Mục cuối là mục quan trọng nhất cả kho, và là mục duy nhất nói về **giới hạn của dữ liệu**:

> Hiện 44/91 món có ghi nhận dị nguyên, nghĩa là món KHÔNG có ghi nhận thì chỉ có nghĩa
> thực đơn chưa ghi, chứ không có nghĩa món đó không chứa.

Đó là sự thật khó nói nhưng phải nói, và nó tính từ dữ liệu nên con số luôn đúng.

Cùng nhóm đó là `kitchen_allergy` — bếp xử lý dị ứng thế nào. Câu trả lời cố ý viết theo
hướng **thận trọng**: bếp dùng chung khu chế biến nên không loại bỏ hoàn toàn nguy cơ. Trả
lời lạc quan ở đây là nguy hiểm thật, không phải chuyện diễn đạt.

## 3. Để trống thì an toàn — đã chứng minh, không chỉ khẳng định

Bất biến quan trọng nhất của tệp dữ liệu này. Mục để trống bị **bỏ qua**, không phải trả về
chuỗi rỗng. Chứng minh hai chiều:

| Thử | Kết quả |
|---|---|
| tệp để trống hoàn toàn | **y hệt** kết quả trước khi có tệp (83/94 ở thời điểm đo); hệ thống vẫn nói "chưa có dữ liệu" và chuyển nhân viên |
| điền thử một mục (`hours`) | trả lời đúng nội dung đã điền; `parking` còn trống thì vẫn nói chưa có dữ liệu |
| tệp hỏng (JSON sai) | coi như chưa có — không làm sập luồng trả lời khách |

## 4. Chỗ khó nhất: câu hỏi META khác câu lọc món

Mở rộng từ vựng cho 24 chủ đề có một cái bẫy:

| Câu khách | Phải làm gì |
|---|---|
| "Món nào không cay?" | **lọc thực đơn**, trả danh sách món |
| "Có mấy mức cay?" | **trả lời tri thức**, vì khách hỏi về cách thực đơn tổ chức |
| "Có món chay nào không?" | lọc thực đơn |
| "Có bao nhiêu món chay?" | trả lời tri thức |

Gộp hai loại thì câu lọc sẽ trả về một đoạn văn thay vì danh sách món — tức mở rộng tri
thức làm hệ thống **tệ đi**. Nên các chủ đề meta chỉ dùng cụm hỏi *về* thực đơn.

Có hai ca chốt chiều ngược (`K-meta-03`, `K-meta-05`): nếu việc mở rộng từ vựng âm thầm
biến câu lọc thành câu tri thức thì chúng đỏ. Không có chúng thì tập đánh giá vẫn xanh
trong khi khách nhận đoạn văn thay cho món.

## 5. An toàn không được phụ thuộc mô hình sinh

Đây là phát hiện quan trọng nhất của bước này, và nó lộ ra từ mã thoát của CI.

Sau khi thêm 14 ca cách nói lạ ở bước 6, mã tất định một mình còn **2 lỗi an toàn**:

- "Mình không ăn được **đồ tanh**" — không hiểu "đồ tanh" là cá/hải sản
- "Bé nhà mình **uống sữa là bị đau bụng**, có món nào **không sữa** không?" — không hiểu

Mô hình sinh sửa được cả hai, và tôi đã ghi nhận đó là giá trị của nó ở bước 6. Nhưng nghĩ
lại thì điều đó nghĩa là **an toàn của hệ thống phụ thuộc một thành phần không tất định**:
proxy chết, mô hình trả lời sai, hay hết hạn mức là **mất bảo vệ dị ứng**.

Không chấp nhận được. Nên hai lớp nhận diện được đưa về mã tất định:

1. **Cách nói dân dã cho dị nguyên**: `đồ tanh`, `mùi tanh` → `allergen:seafood`.
2. **Mẫu "không ⟨chủ đề⟩"** bắt bằng biểu thức chính quy thay vì liệt kê từng tổ hợp:
   `không sữa`, `không trứng`, `không hải sản`, `không đậu phộng`, `không gluten`.
3. **Triệu chứng cũng là cách khai dị ứng**: `bị đau bụng`, `bị ngứa`, `bị nổi mề đay`,
   `ăn vào là bị`.

Kết quả: **lỗi an toàn 0 ở cả hai chế độ**. Mô hình vẫn có giá trị (+11 ca về hương vị, sức
khỏe, ngân sách, dịp ăn) nhưng **không còn nằm trên đường an toàn** — proxy chết thì khách
mất phần gợi ý tinh, không mất bảo vệ dị ứng.

Có ba test chốt điều này, gồm một test chiều ngược: ngoại lệ gọi mô hình khi gặp hạn chế
chưa hiểu **vẫn cần thiết** — ví dụ "đồ có vỏ" thì mã tất định vẫn không hiểu.

## 6. Kết quả

| | Qua | Lỗi an toàn |
|---|---|---|
| chỉ mã tất định | **101/112 (90,2%)** | **0** |
| có mô hình | **112/112 (100%)** | **0** |

Tập ca lên 112 (thêm 13 ca tri thức và 5 ca lấp khoảng trống, 6 họ mới). Sàn của thước
đo: 8/112, và nay được **tính** thay vì viết cứng — bản đầu ghi "12/80" và con số đó lạc
hậu ngay khi tập ca đổi.

## 7. Tập đánh giá và dữ liệu ràng buộc nhau — nói ra trước khi bị bất ngờ

Khi tôi điền nội dung cho `hours`, ca `B-policy-01` **chuyển đỏ**. Không phải lỗi: 6 ca
chính sách trước đây *mã hoá việc chưa có dữ liệu* (`kind: no_data`). Có nội dung rồi thì
kỳ vọng phải thành `fact`.

Cách sửa giữ đúng nguyên tắc của bước 2 — **khóa đáp án là tra dữ liệu, không phải chuỗi
viết tay**. Thêm tiêu chí `knowledge_topic`: thước đo đọc nội dung từ chính tệp tri thức và
đòi câu trả lời chứa nguyên văn. Nên sửa nội dung tri thức thì tiêu chí đổi theo, không
phải sửa tay 6 ca.

Tiêu chí này còn **chặt hơn** phép kiểm nó thay thế: hệ thống không thể tự viết ra nội dung
đúng. Có test hai chiều — đọc nguyên văn thì xanh, tự viết "mở từ 8h sáng đến nửa đêm" dù
nghe hợp lý vẫn đỏ.

Câu tri thức được **miễn** ba phép kiểm dành cho câu tra cứu món (`focus`, `substance`,
`citation_text_to_items`), vì câu tri thức về món cần đặt trước có nêu tên 4 món làm ví dụ
— đó không phải "vùi đáp án giữa cả thực đơn". Miễn không mở lỗ: chốt an toàn vẫn đếm trên
mọi món được nhắc, và tiêu chí thay thế chặt hơn.

## 8. Giới hạn phải nói ra

1. **16/24 chủ đề là giá trị mẫu.** Dự án này là demo nên điều đó ổn, nhưng nếu đưa vào
   dùng thật thì chủ nhà hàng phải thay — và đổi `source` thành `restaurant` để nó không
   còn bị đếm là mẫu.
2. **`diet:vegan` và `diet:vegetarian` gắn trên đúng cùng 17 món**, nên một trong hai nhãn
   không phân biệt được gì trong bộ dữ liệu này. Câu trả lời nói ra điều đó thay vì để khách
   tự đoán, và `audit_allergen_tags.py` nay kiểm ba bất biến để chỗ này không âm thầm hỏng:
   món thuần chay không được mang nhãn sữa hay trứng; thuần chay phải kéo theo chay; và nếu
   hai nhãn trùng hoàn toàn thì in cảnh báo — vì khi có món chay dùng sữa mà vẫn bị gắn thuần
   chay thì cảnh báo đó biến mất và không ai để ý.
3. **Không có tri thức nào về thời gian**, và đó là điều hệ thống nay **nói thẳng** thay vì
   hỏi lại. Chủ đề `time_or_availability` nhận diện "Hôm nay có món gì đặc biệt?" và "Giờ
   này còn món gì?" rồi trả lời chưa có dữ liệu — vì thực đơn không có trường thời gian, và
   cả 91 món đều `isAvailable = true` nên trả về danh sách món là ngầm khẳng định chúng còn
   hàng.
4. **Bốn nhóm cố tình không trả lời** — dinh dưỡng, nội bộ, nhân sự, ngoài bài toán. Lý do ghi
   ở mục 10 dưới đây, để chúng không bị hiểu là chỗ trống cần bổ sung sau.
5. ~~Dạng `no_data` vắng ở tập niêm phong~~ — **đã lấp** bằng họ `time_based_no_data`:
   "Hôm nay có món gì đặc biệt?" và "Giờ này còn món gì?". Hai câu đó lấp đúng giới hạn số 3
   ở trên, và phải xử lý **tất định** chứ không để rơi xuống nhánh hỏi lại: hỏi lại thì khách
   tưởng câu hỏi chưa đủ rõ, còn trả về danh sách món thì ngầm khẳng định chúng còn hàng.

## 9. Cách chạy lại

```
python ai/scripts/build_knowledge.py --check   # kiểm tài liệu derived khớp kết quả sinh lại
python ai/scripts/build_knowledge.py           # sinh lại 56 tài liệu derived
python ai/evaluation/run_baseline.py --all            # chỉ mã tất định
python ai/evaluation/run_with_model.py               # có mô hình
```

## 10. Bốn nhóm KHÔNG BAO GIỜ trả lời, và vì sao

Bốn nhóm dưới đây **không thuộc kho tri thức** và cố tình không có chỗ điền. Chúng ghi ở đây để
giải thích **vì sao**, không phải để bổ sung sau. Ai thấy chúng trống mà đi điền vào là đang mở
đường cho AI bịa.

| Nhóm | Nội dung | Vì sao không trả lời |
|---|---|---|
| **Dinh dưỡng** | số calo, natri, thành phần định lượng | Thực đơn chỉ có mô tả bằng chữ. Nhãn `health:high_protein` là **đánh giá cảm quan của người nhập liệu**, không phải kết quả phân tích — dùng nó để trả lời calo là bịa |
| **Nội bộ** | doanh thu, lợi nhuận, lương nhân viên | Không có dữ liệu, và cũng không nên có trong kênh chat khách hàng |
| **Nhân sự** | tên bếp trưởng, ai nấu món nào | Không có dữ liệu nhân sự |
| **Ngoài bài toán** | thời tiết, gọi taxi, dịch thuật, prompt hệ thống | Ngoài phạm vi — AI từ chối ngắn gọn rồi mời về chuyện ăn uống |

Năm chủ đề ứng với chúng (`nutrition`, `internal`, `staff_identity`, `no_size`,
`time_or_availability`) **nhận diện được** ở bước hiểu câu hỏi nhưng **không có tài liệu**, nên
hệ thống nói thẳng chưa có dữ liệu rồi chuyển nhân viên. Đó là hành vi đúng, không phải thiếu
sót — và `test_understand.KhoTriThucVaTuVungPhaiKhopNhau` ép danh sách này phải **nêu tên**, chứ
không được bỏ qua bằng một ngưỡng số.

## 11. Thêm tri thức mới thế nào

1. **Nội dung không suy được từ thực đơn** (chính sách, lời khuyên) → tệp tay trong
   `ai/knowledge/policy/` (`verbatim`) hoặc `ai/knowledge/written/` (`synthesize`).
2. **Nội dung có số tính từ thực đơn** → thêm vào `build_knowledge.py`, đừng viết tay. Văn xuôi
   kể lại dữ liệu thì luôn trôi khỏi dữ liệu.
3. Frontmatter bắt buộc đủ **5 khóa**: `id`, `title`, `topic_keys`, `source`, `audience`,
   `answer_mode`. Bộ nạp **từ chối** tệp thiếu, không bỏ qua im lặng.
4. Thêm cụm nhận diện cho `topic_keys` mới vào `understand.py` — không có cụm thì nội dung
   **không bao giờ tới tay khách**, và test bất biến sẽ đỏ để nhắc.
5. Chạy `build_knowledge.py`, rồi `run_baseline.py --all` xác nhận 112 ca không tụt.
