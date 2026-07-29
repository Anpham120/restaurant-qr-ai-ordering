# Bước 6 — Mô hình sinh, và chỗ duy nhất nó chứng minh được giá trị

Bước 4 đạt 80/80 trong phạm vi từ vựng viết tay. Nên câu hỏi cho bước này không phải "mô
hình có làm câu trả lời hay hơn không" — thước đo không đo được sự hay — mà là: **có việc
gì mô hình làm được mà mã tất định không làm được, và đo được không?**

Có. Đó chính là giới hạn số 3 tôi đã nêu ở bước 4.

| Tệp | Việc |
|---|---|
| `app/llm_understand.py` | gọi mô hình để đọc câu hỏi thành ràng buộc |
| `app/test_llm_understand.py` | 17 test, chủ yếu là bất biến an toàn |
| `evaluation/run_with_model.py` | đo trước/sau, và bắt ca bị làm tụt |
| `app/llm_cache.json` | cache để phép đo tái lập được |

## 1. Mô hình chỉ HIỂU, không CHỌN

Đây là quyết định kiến trúc quan trọng nhất của bước này.

Bản cũ để mô hình quyết định **nội dung** câu trả lời, nên nó có thể mời khách một món gây
dị ứng hoặc bịa ra một giá. Ở đây mô hình làm đúng một việc: đọc câu khách thành **ràng
buộc có cấu trúc**. Chọn món vẫn do mã tất định làm, trên đúng thực đơn.

```
câu khách  ──▶  mã tất định đọc  ──▶  [chưa hiểu đủ?]  ──▶  mô hình đọc thành ràng buộc
                                                                      │
                                                          hợp vào ràng buộc đã có
                                                                      │
                                        lọc thực đơn (TẤT ĐỊNH)  ◀────┘
                                                    │
                                             viết câu trả lời
```

Ba hệ quả, và cả ba là điều kiện để tin được kiến trúc này:

1. **Mô hình không thể mời món gây dị ứng** — nó không chọn món.
2. **Mô hình không thể bịa giá** — giá lấy từ thực đơn.
3. **Mô hình không thể nới ràng buộc** — kết quả của nó được **hợp** vào ràng buộc mã tất
   định đã tìm ra, không thay thế.

Điểm 3 có test riêng, và là bất biến quan trọng nhất của tệp: nếu mã đã thấy "dị ứng hải
sản" thì mô hình trả về gì cũng không xóa được ràng buộc đó.

Mô hình còn bị chặn thêm hai lớp:

- **Chỉ được dùng khóa nhãn có trong từ điển.** Khóa lạ bị **bỏ**, không phải bị tin. Mô
  hình bịa `flavour:umami` thì khóa đó rơi vào hư không.
- **Nhóm nhãn quyết định vai, không phải mô hình.** Nhóm phủ 91/91 món (`spice`, `price`,
  `diet`, `party`, `season`) được dùng làm bộ lọc cứng; nhóm không phủ hết (`flavour`,
  `health`, `occasion`...) chỉ dùng để sắp thứ tự. Mô hình xếp sai vai thì hệ thống **chuyển
  vai** theo nhóm chứ không bỏ — vì bản thân nhãn vẫn là thông tin thật.

## 2. Chỉ gọi mô hình khi cần, và con số cho thấy điều đó

Mã tất định trả lời được phần lớn câu hỏi. Gọi mô hình cho những câu đó là thêm độ trễ,
thêm chi phí, thêm một nguồn **không tất định** — mà không được gì.

Thực tế: mô hình chỉ được gọi ở **15/94 ca (16%)**. 84% câu hỏi không chạm tới mô hình.

## 3. Kết quả

| | Qua | Lỗi an toàn |
|---|---|---|
| chỉ mã tất định | 83/94 (88,3%) | **2** |
| có mô hình | **92/94 (97,9%)** | **0** |
| chênh | **+9 ca** | **−2** |

**0 ca bị làm tụt.** Đây là cột tôi quan tâm nhất, vì bản cũ chính là ví dụ thêm cơ chế mà
không đo phần bị phá.

Chín ca mô hình cứu được, tất cả đều là cách nói ngoài từ vựng viết tay:

| Ca | Câu khách | Mô hình đọc thành |
|---|---|---|
| `P-allergy-01` | "Mình không ăn được **đồ tanh**" | `allergen:seafood` |
| `P-allergy-02` | "Bé nhà mình **uống sữa là bị đau bụng**" | `allergen:dairy` |
| `P-flavour-01` | "gì đó **chua chua** ăn cho đỡ ngán" | `flavour:sour` |
| `P-flavour-02` | "món nào **đậm đà đưa cơm**" | `flavour:rich` |
| `P-health-01` | "Mình **đang giảm cân**" | `health:low_calorie` |
| `P-health-02` | "Mình **tập gym**, cần món **nhiều đạm**" | `health:high_protein` |
| `P-health-03` | "gì đó **thanh thanh** dễ ăn, **đừng dầu mỡ**" | `health:light`, `health:low_fat` |
| `P-budget-01` | "**Sinh viên** nên mình hơi **ít tiền**" | `price:budget` |
| `P-budget-02` | "muốn **ăn sang** một bữa" | `price:high` |

Hai ca đầu là quan trọng nhất: chúng là **lỗi an toàn**. Mã tất định gặp "đồ tanh" thì
không hiểu, nên nó hỏi lại hoặc trả lời như thể khách không nêu hạn chế nào. Mô hình đọc
được, và ràng buộc dị nguyên được áp fail-closed như mọi ca khác.

## 4. Ba lần tôi tự làm tụt kết quả, và mỗi lần học được gì

Phép đo trước/sau bắt được cả ba, và đó là lý do nó tồn tại.

**Lần 1 — điều kiện chặn thiếu tín hiệu.** Câu "Món đắt nhất menu là món nào?" bị gọi mô
hình dù mã tất định trả lời đúng, và kết quả tụt. Nguyên nhân: điều kiện "mã đã hiểu đủ"
của tôi chỉ kiểm ràng buộc và tên món, bỏ sót `asks_extreme`, `asks_price`, `is_comparison`.
→ *Bài học: danh sách tín hiệu "đã hiểu" phải đầy đủ, thiếu một cái là mở cửa cho mô hình
vào chỗ không cần.*

**Lần 2 — sửa quá tay thì chặn cả chỗ cần.** Sau khi bổ sung, câu "Mình không ăn được đồ
tanh, gợi ý **món ăn** giúp mình" bị coi là đã hiểu (vì thấy "món ăn") nên mô hình không
được gọi — để lại đúng lỗi an toàn mà mô hình đã sửa được ở lần đo trước.
→ *Bài học: câu hỏi đúng không phải "mã có hiểu gì không" mà **"khách có nêu hạn chế mà mình
không hiểu hạn chế gì không"** — đó mới là trạng thái nguy hiểm.* Nay có cờ riêng
`unparsed_restriction`, và nó là ngoại lệ duy nhất được vượt điều kiện chặn.

**Lần 3 — cờ mới báo động sai.** Câu "Bốn người, ngân sách 500 nghìn, **không ăn được cay**"
bị cờ đó bắt, dù hạn chế ĐÃ được hiểu thành `spice:none`. Nguyên nhân: tôi kiểm cụm "không
ăn được" trên chữ **gốc** thay vì chữ **còn lại** sau khi khớp.
→ *Bài học: nguyên tắc ăn đoạn ở bước 4 áp cho cả chỗ này. Cụm `khong an duoc cay` đã ăn
trọn phần đó, nên "khong an duoc" không còn nữa.*

Cả ba lần đều là lỗi của tôi, không phải của mô hình. Và cả ba đều bị bắt bởi cùng một cột
số: "ca mô hình làm tụt".

## 5. Test bắt hai lỗi thật trong chính mã của tôi

`test_llm_understand.py` không gọi mô hình thật — nó thay `call_model` bằng đáp án cố định
và hỏi: *nếu mô hình trả về thứ tệ nhất có thể, hệ thống có còn an toàn không?*

Hai lỗi nó bắt được ngay lần chạy đầu:

1. **Mô hình trả về `"avoid": 42` làm sập dịch vụ** (`'int' object is not iterable`).
2. **Khóa bịa trong `avoid` bị bỏ im lặng**, không ghi lại.

Cùng một gốc: tôi dùng hàm kiểm có phòng vệ cho `require`/`prefer` nhưng viết list
comprehension trần cho `avoid`. Nay **mọi** dữ liệu từ mô hình đi qua một cửa duy nhất.

Đây đúng là giá trị của việc thử đầu vào tệ nhất: một mô hình thật hiếm khi trả về `42`,
nhưng "hiếm khi" trong một hệ thống chạy thật là "sẽ xảy ra".

## 6. Phép đo phải tái lập được, nên có cache

Mô hình sinh **không tất định**, mà cả dự án này dựa trên tính chất "chạy lại cho cùng kết
quả". Nên mỗi câu hỏi có kết quả lưu trên đĩa (`llm_cache.json`, 24 mục). Xóa tệp đó là đo
lại từ đầu; `--no-cache` gọi mô hình thật.

CI chạy trên cache đã commit và **không** gọi mô hình thật — CI không có proxy, và một bước
CI phụ thuộc mạng ngoài thì đỏ vì lý do không liên quan gì đến mã.

Bù lại phải nói rõ: **con số 92/94 đo trên 24 câu trả lời mô hình đã lưu**, không phải trên
mọi lần mô hình có thể trả lời. Mô hình khác, hoặc cùng mô hình ở lần gọi khác, có thể cho
kết quả khác.

## 7. Giới hạn phải nói ra

1. **Cache làm phép đo tái lập được, nhưng cũng làm nó hẹp lại.** Xem mục 6.
2. **Độ trễ thật ~6 giây mỗi lần gọi** (đo ở lần chạy đầu, trước khi có cache). Với 16% câu
   hỏi thì trung bình mỗi câu tăng khoảng 1 giây — nhưng câu nào bị gọi thì khách chờ đủ 6
   giây. Chưa đo trên mạng thật của khách.
3. **Chưa có fallback khi proxy chết.** Hiện nếu gọi thất bại thì hệ thống giữ nguyên câu
   trả lời tất định — đúng hướng, nhưng nghĩa là những ca ở mục 3 sẽ tụt lại về hỏi lại.
   Đó là suy giảm êm, không phải sập, và đã có test.
4. **2 ca vẫn đỏ** ở cả hai chế độ. Chúng là khoảng trống của mã tất định, không phải của
   mô hình.
5. **Mô hình chưa được dùng để VIẾT câu trả lời.** Câu trả lời hiện do mã sinh ra nên đúng
   nhưng khô. Cho mô hình viết sẽ hay hơn, nhưng khi đó nó lại có thể bịa — và thước đo
   hiện tại chỉ chặn được việc bịa **món** và bịa **giá**, chưa chặn được việc bịa một lời
   khẳng định về món. Chưa làm, và chưa nên làm cho tới khi đo được.

## 8. Cách chạy lại

```
python -m unittest discover -s ai/app -p "test_*.py"    # 56 test
python ai/evaluation/run_with_model.py                  # trước/sau, dùng cache
python ai/evaluation/run_with_model.py --no-cache       # gọi mô hình thật
```

Cần proxy 9router chạy ở `localhost:20128` cho chế độ `--no-cache`:

```
9router --port 20128 --no-browser --skip-update
```
