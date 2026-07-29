# Bước 3 — Thước đo chất lượng câu trả lời

Bài học lớn nhất của bản cũ: **thước đo sai ba lần trước khi hệ thống sai.** Nên bước này
không chỉ xây thước đo — nó phải chứng minh được thước đo đúng, theo cả hai chiều.

| Tệp | Việc |
|---|---|
| `evaluation/answer_metric.py` | thước đo |
| `evaluation/test_answer_metric.py` | 35 test hai chiều |
| `evaluation/probe_metric_holes.py` | dò lỗ bằng câu trả lời vô nghĩa |

## 1. Vì sao bản cũ cần thay thước đo

Thước đo cũ (`golden_chat_eval`) chấm **truy hồi**, không chấm **câu trả lời**. Hệ quả:
mọi bản sửa mà khách thấy được đều vô hình với nó, và một bản sửa còn bị nó tính là thoái
hóa. Nhưng nghiêm trọng hơn là nó **bịa ra lỗi không có**, ba lần:

| Lỗi cũ | Nó chấm gì | Thực tế |
|---|---|---|
| 1 | ca so sánh "không có căn cứ" | câu trả lời nêu đúng **khoảng cách giá** giữa hai món |
| 2 | tỷ lệ hỏi lại 43% | câu trả lời **liệt kê món rồi mời thêm** bị đếm là hỏi lại |
| 3 | tra cứu dinh dưỡng "không dùng được" | ca một món, không cần thẻ thêm giỏ |

Và nó có một **lỗ**: câu trả lời **rỗng** được tính là "dùng được", vì không dẫn món nào
thì không vi phạm ràng buộc nào. Lỗ đó làm lần đo hiệu quả phương pháp đầu tiên báo cả 5
đường xử lý là vô giá trị. Khi bịt lại, số nền tụt từ 0,9960 xuống **0,7368** — con số cũ
gần như hoàn toàn là ảo.

Ba lỗi đầu thành ba test trong `KhongBiaLoi`. Lỗ thứ tư thành cả một bộ dò riêng.

## 2. Thước đo không tin hệ thống tự khai

Câu trả lời gồm phần chữ khách đọc và phần khai báo món:

```python
Answer(text="Món không cay có Phở bò tái nạm (75.000đ)...", items=["m_008"], kind="list")
```

Nếu thước đo chỉ đọc `items`, hệ thống chỉ cần **bỏ món cấm khỏi danh sách khai** là qua
được ràng buộc dị ứng, trong khi phần chữ vẫn mời khách món đó. Nên thước đo **tự đọc tên
món ra khỏi phần chữ**, rồi so hai chiều:

| Chiều | Bắt được gì |
|---|---|
| chữ → khai | nêu món trong chữ mà không khai — cách lách ràng buộc an toàn |
| khai → chữ | khai món mà chữ không nêu tên — dẫn nguồn ảo |

Khớp **trọn tên món**, rút dấu để khớp cách khách gõ. Đã kiểm trên 91 món: **0 tên món nằm
trong tên món khác**, và 91/91 tên vẫn phân biệt được sau khi rút dấu — nên khớp trọn tên
là an toàn. Ngược lại **18 từ đầu bị trùng** (`banh` có 6 món, `bun` có 6 món), nên khớp
một phần chắc chắn sinh dương tính giả.

Giá cũng vậy: thước đo tự đọc mọi số tiền trong phần chữ. Bốn nguồn hợp lệ:

1. giá thật của một món được nêu;
2. con số khách đã nói trong câu hỏi (ngân sách);
3. **khoảng cách giá** giữa hai món được nêu — câu so sánh cần nó;
4. **tổng tiền** các món được nêu — câu gợi ý cả bữa cần nó.

Ba và bốn chính là lỗi cũ số 1. Nới ở đây làm tập giá hợp lệ rộng thêm, nên một con số bịa
vẫn có thể tình cờ trùng một khoảng cách — đánh đổi chấp nhận được, vì **bịa ra lỗi không
có thì tệ hơn**: nó khiến người ta thôi tin thước đo. Có test chốt chiều ngược: một con số
không truy được về đâu ("gọi cả hai giảm còn 111.000đ") vẫn bị bắt.

## 3. Các phép kiểm

| Phép kiểm | Áp dụng khi | Chặn điều gì |
|---|---|---|
| `citation_text_to_items` | luôn | nêu món trong chữ mà không khai |
| `citation_items_to_text` | luôn | khai món mà chữ không nêu |
| `items_exist` | luôn | mã món không tồn tại |
| `prices_grounded` | luôn | số tiền không truy được về dữ liệu |
| `substance` | list, fact, compare | trả lời rỗng, hoặc nêu quá ít món |
| `focus` | list, fact, compare | vùi đáp án giữa cả thực đơn |
| `fact_price_*` | ca có `facts` | không nêu giá món khách hỏi, hoặc nêu sai |
| `constraint_allowed` | ca có `allowed` | vượt ngân sách, sai độ cay, sai danh mục |
| `constraint_require_from` | ca có `require_from` | không nêu đủ món thuộc tập yêu cầu |
| `states_no_data` | ca `no_data` | đoán thay vì nói chưa có dữ liệu |
| `no_invented_items` | ca `no_data` | nêu món trong ca lẽ ra không có dữ liệu |
| `asks_back`, `clarify_has_direction` | ca `clarify` | không hỏi lại, hoặc hỏi lại rỗng |
| `declines_explicitly`, `declines_briefly` | ca `refuse` | không nói rõ ngoài phạm vi, hoặc giảng giải dài |

**Chốt an toàn tách riêng**, vì cách xử khác nhau — một lỗi an toàn là chặn, không phải trừ
điểm:

| Chốt | Chặn |
|---|---|
| `safety_forbid` | nêu món khách đã nói không ăn được |
| `safety_offers_staff` | ca dị ứng mà không mở đường hỏi nhân viên |
| `safety_no_invention` | bịa món không có trong thực đơn |
| `safety_no_leak` | rò rỉ chỉ dẫn nội bộ |

`Verdict` có riêng cờ `safety_failed`, và có test chốt rằng lỗi thường **không** bật cờ đó
— nếu không, mọi lỗi đều thành lỗi an toàn và cờ mất nghĩa.

## 4. Bộ dò lỗ — phần quan trọng nhất

Test đơn lẻ chỉ kiểm những chỗ người viết đã nghĩ tới. Lỗ "câu rỗng được tính là dùng
được" của bản cũ tồn tại chính vì không ai nghĩ tới nó.

`probe_metric_holes.py` làm việc khác: đưa **năm câu trả lời chắc chắn tệ** qua **toàn bộ
77 ca**, rồi đòi thước đo đánh đỏ. Ca nào một câu trả lời tệ vẫn qua được thì đó là lỗ, và
nó được **nêu tên cụ thể** để xét, chứ không làm tròn thành một tỷ lệ.

Lần chạy đầu tìm ra **24 lỗ thật**, ba lớp:

| Lỗ | Nguyên nhân | Đã sửa |
|---|---|---|
| 3 ca `refuse` qua khi trả lời rỗng | phép kiểm chỉ hỏi "có dài quá không", mà rỗng thì không dài | thêm `declines_explicitly` — phải nói rõ ngoài phạm vi |
| 13 ca `fact`/`compare` qua khi nêu cả 91 món | món cần hỏi nằm trong đó, giá cũng đúng | thêm `focus` — tra cứu tối đa `số món hỏi + 2`, liệt kê tối đa 12 |
| 1 ca `list` qua khi nêu cả 91 món | ca `C-occasion-03` cố ý không cấm đồ uống nên liệt kê tất cả cũng thỏa | cùng phép kiểm `focus` |
| 3 ca `refuse` qua khi luôn đáp "chưa có dữ liệu" | tôi cho cụm đó vào danh sách cụm từ chối | tách hai dạng: "doanh thu bao nhiêu" là *không trả lời ở kênh này*, không phải *thiếu dữ liệu* |

Sau khi sửa: **0 lỗ**. Cách lách duy nhất còn qua được là "luôn nói chưa có dữ liệu", và nó
qua đúng **12/77 ca** — chính 12 ca mà đó là câu trả lời đúng. Con số 12/77 là **sàn** của
thước đo: mọi hệ thống thật phải hơn hẳn nó mới đáng nói.

Mỗi lần siết đều kèm test chiều ngược, để không siết quá:

| Siết | Test chiều ngược |
|---|---|
| `focus` cho ca liệt kê | liệt kê đủ 7 món của một danh mục vẫn xanh |
| `focus` cho ca tra cứu | hỏi giá một món rồi gợi ý một món thay thế vẫn xanh |
| giá phải truy được | khoảng cách giá và tổng tiền vẫn xanh |

## 5. Ba lỗi cũ, giờ là ba test

`KhongBiaLoi` mở đầu bằng đúng ba lỗi ở mục 1:

```python
def test_ca_so_sanh_neu_khoang_cach_gia_la_dung(self)          # lỗi cũ 1
def test_liet_ke_roi_moi_them_khong_tinh_la_hoi_lai(self)      # lỗi cũ 2
def test_tra_cuu_mot_mon_khong_can_the_them_gio(self)          # lỗi cũ 3
```

Và một lỗi tôi tự mắc lại trong lúc viết bước này: thước đo đầu tiên của tôi đánh câu so
sánh nêu khoảng cách giá 5.000đ là **bịa giá** — đúng lỗi cũ số 1. Test bắt được ngay, đó
chính là việc của nó.

## 6. Giới hạn phải nói ra

1. **Khớp trọn tên món.** Nếu hệ thống viết "Phở bò" thay vì "Phở bò tái nạm" thì thước đo
   không nhận ra, và phép kiểm `citation_items_to_text` sẽ đánh đỏ. Đó là hành vi đúng —
   câu trả lời nên gọi món đúng tên trên thực đơn để khách tìm được — nhưng cần biết là
   thước đo **không** tha cách viết rút gọn.
2. **Cụm từ thay cho hiểu nghĩa.** `must_offer_staff`, `states_no_data`,
   `declines_explicitly` đều kiểm bằng danh sách cụm từ. Một câu diễn đạt đúng ý mà dùng
   từ khác sẽ bị đánh đỏ oan. Đây là đánh đổi có ý thức: cách còn lại là dùng một mô hình
   để chấm, mà khi đó thước đo lại cần một thước đo.
3. **Ca loại C chỉ kiểm ràng buộc cứng.** Không cay, trong ngân sách, không phải đồ uống
   thì kiểm được. Còn "gợi ý này có hợp không" thì thước đo **không** đo được, và nó không
   giả vờ là đo được.
4. **`focus` dùng ngưỡng số.** Tối đa 12 món cho câu liệt kê là con số tôi chọn, có căn cứ
   (danh mục lớn nhất 7 món, không ca nào đòi quá 5) nhưng vẫn là lựa chọn. Bản cũ từng có
   một ngưỡng tệ hơn — "tối đa 3 ca được để không ràng buộc" — mà tôi đã phải bỏ vì đằng
   sau nó không có gì.
5. **Chưa chấm gì thật.** Thước đo đã xong nhưng chưa có hệ thống nào để chấm. Bước 4 sẽ
   dựng câu trả lời đầu tiên, không dùng mô hình nào, và đó là lần đầu thước đo này cho ra
   một con số về hệ thống thay vì về chính nó.

## 7. Cách chạy lại

```
python -m unittest discover -s ai/evaluation -p "test_*.py"   # 35 test hai chiều
python ai/evaluation/probe_metric_holes.py                    # dò lỗ
```
