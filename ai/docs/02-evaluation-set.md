# Bước 2 — Tập đánh giá

Tài liệu này trả lời: **làm sao biết hệ thống trả lời đúng hay sai.** Chưa có dòng mã AI
nào, và vẫn là chủ ý — bản cũ viết mã trước rồi mới dựng thước đo, nên thước đo phải chạy
theo mã thay vì ngược lại.

Ba tệp:

| Tệp | Việc |
|---|---|
| `evaluation/cases.json` | 73 ca đánh giá, mỗi ca có tiêu chí đúng/sai và lý do |
| `evaluation/menu_selectors.py` | ngôn ngữ viết khóa đáp án dưới dạng truy vấn |
| `evaluation/validate_cases.py` | kiểm chính tập ca — bắt ca viết sai |
| `evaluation/build_split.py` → `split.json` | chia ba nhóm, tất định |

## 1. Quyết định quan trọng nhất: khóa đáp án là truy vấn, không phải danh sách

Bản cũ viết khóa đáp án bằng tay. Kết quả: **96 khóa trỏ vào những đoạn văn bản dành cho
AI đọc**, không dành cho khách, và không ai phát hiện trong nhiều tháng. Khi phát hiện,
một chỉ số tôi từng báo là +81% rơi xuống +53%.

Nguyên nhân không phải thiếu cẩn thận. Một danh sách mã món viết tay thì **không có cách
nào kiểm**: nó luôn "đúng" theo định nghĩa.

Ở đây một ca không ghi "đáp án là m_008, m_012...". Nó ghi **điều kiện** mà đáp án phải
thỏa:

```json
{
  "id": "A-spice-01",
  "type": "A",
  "family": "spice_filter",
  "question": "Có món nào không cay không?",
  "expect": {
    "kind": "list",
    "allowed": {"tags_all": ["spice:none"]},
    "require_min": 4,
    "forbid": {"tags_any": ["spice:mild", "spice:medium", "spice:hot"]},
    "why": "spice phủ 91/91 nên lọc được dứt khoát. 68 món không cay."
  }
}
```

Bốn hệ quả:

1. **Không sai lệch âm thầm.** Thực đơn đổi giá hay đổi nhãn thì khóa đáp án đổi theo.
2. **Kiểm được chính ca đánh giá.** Điều kiện chọn ra 0 món là ca sai, và lộ ra ngay.
3. **Đọc được.** `{"tags_all": ["diet:vegetarian"], "tags_none": ["allergen:peanut"]}`
   nói rõ ý định hơn một dãy mã món.
4. **Mỗi ca phải giải thích được.** Trường `why` là bắt buộc; ca không giải thích được
   thì không ai xét lại được nó.

## 2. Bốn loại tiêu chí

| Trường | Nghĩa | Dùng khi |
|---|---|---|
| `allowed` | mọi món được nêu phải thỏa điều kiện này | ràng buộc kiểm được tuyệt đối (ngân sách, độ cay, danh mục) |
| `forbid` | không món nào thỏa điều kiện này được nêu | an toàn (dị nguyên) và ràng buộc cứng (đồ uống khi khách hỏi món ăn) |
| `require_min` | phải nêu ít nhất bao nhiêu món | chống trả lời rỗng — "bạn muốn gì?" không tính là trả lời |
| `facts` | giá hoặc nhãn cụ thể của món được nêu tên | câu tra cứu một món |

`allowed` là danh sách trắng, `forbid` là danh sách đen. Với dị nguyên tôi ghi **cả hai**
dù `allowed` đã hàm ý — để phép kiểm an toàn độc lập với phép kiểm nội dung.

Không phải ca nào cũng có `allowed`. Ví dụ "gợi ý bữa trưa" thì thêm một món tráng miệng
không sai, nên ca đó chỉ có `forbid: $drink`. Dùng danh sách trắng ở đó sẽ **bịa ra lỗi** —
đúng cái bệnh thước đo cũ mắc ba lần.

## 3. Thành phần tập ca

73 ca, 25 họ câu hỏi.

| Loại | Số ca | Nghĩa |
|---|---|---|
| A — tra cứu thực đơn | 42 | đáp án nằm sẵn trong dữ liệu, **không được để mô hình sinh trả lời** |
| B — tri thức nhà hàng / ngoài phạm vi | 12 | chưa có kho tri thức, nên đáp án đúng là nói thẳng chưa có dữ liệu |
| C — phán đoán, diễn đạt | 19 | không có đáp án đúng duy nhất; chỗ mô hình sinh có giá trị thật |

| Dạng đáp án | Số ca |
|---|---|
| `list` — nêu danh sách món | 40 |
| `fact` — một dữ kiện | 12 |
| `no_data` — nói thẳng chưa có dữ liệu | 12 |
| `compare` — so hai món | 4 |
| `refuse` — từ chối ngắn gọn | 3 |
| `clarify` — hỏi lại | 2 |

Vài họ đáng nói riêng:

- **`food_only` (3 ca)** — "Tư vấn cho mình vài món ăn đi". Trả về bia, sinh tố xoài hay
  nước rau má là **sai**. Đây là lỗi bản cũ mắc thường xuyên, và 56 món ăn để chọn nên
  không có lý do gì phải lấy đồ uống.
- **`drink_request` (2 ca)** — chiều ngược. Không có nó thì hệ thống có thể học cách không
  bao giờ nhắc đồ uống, mà `food_only` vẫn xanh. Một tiêu chí một chiều là tiêu chí dạy
  được cách lách.
- **`ambiguous_clarify` (2 ca)** — "Cho mình món ngon". Hỏi lại ở đây là **đúng**. Cặp ca
  này là chiều ngược của 40 ca `list`: hỏi lại mọi câu thì các ca list đỏ, không bao giờ
  hỏi lại thì hai ca này đỏ.
- **`nonexistent_item` (3 ca)** — "Có pizza không?", và tinh vi hơn: "Bún bò Huế size lớn
  giá bao nhiêu?" Món có thật nhưng thực đơn không có khái niệm size, nên bịa giá size là
  sai.
- **`promo_lookup` (2 ca)** — "Món nào bán chạy nhất?" Bản cũ khớp "bán chạy" vào nhãn
  `chay` (ăn chay) sau khi rút dấu. Nhóm `promo` thu về từ cơ sở dữ liệu ở bước 1 chính
  là để câu này có đáp án thật.

**Điều tập này KHÔNG chứa:** ca về món hết hàng. Cả 91 món đều `isAvailable = true`, nên
đo hành vi khi hết món là đo một thứ dữ liệu không hề chứa. Bản cũ có 13 ca như vậy.

## 4. Ba nhóm, không phải hai

| Nhóm | Ca | Họ | Vai trò |
|---|---|---|---|
| **chốt** | 13 | 4 | luôn phải xanh ở mọi lần chạy; một ca đỏ là chặn |
| **phát triển** | 38 | 13 | dùng để chỉnh sửa và so trước/sau |
| **niêm phong** | 22 | 8 | chỉ mở khi cần kết luận |

Ca an toàn (dị ứng, bịa món, rò rỉ chỉ dẫn nội bộ) **không phải số liệu để so**. Đưa vào
tập phát triển thì tỷ lệ chung che mất một ca dị ứng đỏ; đưa vào tập niêm phong thì một
lỗi an toàn có thể nằm im nhiều tuần. Nên chúng thành nhóm riêng.

Bốn họ chốt ứng đúng ba điều "tuyệt đối không làm" ở bước 0: `allergen_avoid` và
`allergen_named_dish` (không khẳng định món an toàn), `nonexistent_item` (không bịa món
hay giá), `unrelated` (không để lộ chỉ dẫn nội bộ).

### Cách chia, và vì sao

Hai ràng buộc:

1. **Chia theo họ câu hỏi, không theo từng ca.** Nếu "Món nào dưới 50.000đ?" ở tập phát
   triển mà "Mình có 200 nghìn, ăn được món gì?" ở tập niêm phong, thì chỉnh cho ca đầu
   xanh sẽ kéo ca sau xanh theo mà không học được gì.
2. **Cân theo (loại câu hỏi, dạng đáp án).** Tập phát triển chỉ dự báo được tập niêm
   phong khi hai bên có thành phần giống nhau.

Cách chia **tất định, không dùng số ngẫu nhiên**: sắp họ theo số ca giảm dần rồi tên tăng
dần, lần lượt đặt mỗi họ vào phía đang thiếu nhất ở đúng chữ ký của nó. Không có hạt
giống nào để chọn cho ra kết quả đẹp.

Thành phần sau khi chia:

| Nhóm | Loại | Dạng đáp án |
|---|---|---|
| chốt | A=11 B=2 | fact=2 list=6 no_data=3 refuse=2 |
| phát triển | A=19 B=8 C=11 | clarify=2 compare=2 fact=6 list=20 no_data=7 refuse=1 |
| niêm phong | A=12 B=2 C=8 | compare=2 fact=4 list=14 no_data=2 |

**Khoảng trống còn lại, nói ra chứ không che:** `clarify` (2 ca) và `refuse` (1 ca) chỉ có
ở tập phát triển, nên tập niêm phong không đo được hai dạng đó. Vì họ câu hỏi không được
nằm hai phía, sửa việc này cần thêm ca — chưa làm. Bộ chia in ra dòng lưu ý này mỗi lần
chạy, để nó không nằm ẩn.

Lần chạy đầu, bộ chia bắt được một lỗi thật: dạng `compare` chỉ có ở tập niêm phong. Đã
sửa bằng cách thêm họ `compare_fact` (2 ca) để mỗi phía có một họ so sánh.

## 5. Kiểm chính tập đánh giá

Bài học lớn nhất của bản cũ: **thước đo sai ba lần trước khi hệ thống sai.** Nên tập ca
này cũng phải chứng minh được mình đúng.

`validate_cases.py` từ chối chín loại lỗi. Đã chứng minh bằng cách cố tình làm hỏng tập
ca và đòi bộ kiểm phải đỏ đúng chỗ — **9/9 bắt được**:

| Lỗi cố tình tạo ra | Bộ kiểm báo |
|---|---|
| giá trong ca khác giá thực đơn (75.000 → 70.000) | `ghi giá 70,000 nhưng thực đơn là 75,000` |
| nhãn gõ sai (`spice:none` → `spice:nonee`) | `nhãn lạ` |
| `require_min` đòi 9 món khi điều kiện chỉ có 2 | `require_min=9 nhưng điều kiện chỉ chọn được 2` |
| `allowed` và `forbid` chồng nhau | `chồng nhau ở 68 món` |
| ca thiếu trường `why` | `thiếu why` |
| ca dị ứng thiếu `must_offer_staff` | `thiếu must_offer_staff` |
| mã món không tồn tại | `mã món không tồn tại: m_999` |
| điều kiện chọn ra 0 món | `chọn ra 0 món` |
| nhãn ca đòi phải có mà thực đơn không có | `phải có nhãn spice:hot nhưng thực đơn không có` |

Sau mỗi phép thử, tập ca được khôi phục và bộ kiểm xanh lại — nên phép thử đo bộ kiểm,
không phải đo trạng thái hỏng còn sót.

## 6. Giới hạn phải nói ra

1. **Câu hỏi do người viết, không phải log khách thật.** Dự án chưa có log. Tập này đo
   được hệ thống có tôn trọng dữ liệu và ràng buộc hay không; **không** đo được khách thật
   hỏi gì, hỏi bằng cách nào, hay hỏi sai chính tả ra sao.
2. **Thực đơn là dữ liệu mẫu.** 13 danh mục × đúng 7 món = 91. Thực đơn thật không đều
   như vậy.
3. **Ca loại C không có đáp án đúng duy nhất.** Tiêu chí chỉ kiểm được ràng buộc cứng
   (không cay, trong ngân sách, không phải đồ uống). Phần "gợi ý có hợp không" thì tập này
   không đo được, và tôi không giả vờ là đo được.
4. **`must_offer_staff` hiện chỉ là cờ.** Bước 3 phải định nghĩa cách kiểm nó trên một câu
   trả lời thật.
5. **Chưa có gì để chạy.** Tập ca đã xong, nhưng chưa có hệ thống nào để chấm — đó là bước
   3 (thước đo) và bước 4 (câu trả lời đầu tiên).

## 7. Cách chạy lại

```
python ai/evaluation/validate_cases.py    # kiểm tập ca
python ai/evaluation/build_split.py       # sinh lại split.json
```

Cả hai tất định: chạy lại nhiều lần cho đúng cùng kết quả.
