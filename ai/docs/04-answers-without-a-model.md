# Bước 4 — Trả lời không cần mô hình

Bước này dựng câu trả lời đầu tiên, và **không dùng mô hình sinh nào**. Lý do: bản cũ chỉ
có 33% câu trả lời do mã tất định sinh ra, phần còn lại phụ thuộc mô hình — và không ai
nói được đường nào phụ trách việc gì. Ở đây làm ngược lại: dựng phần tra bảng trước, đo
xem nó trả lời được bao nhiêu, rồi mới biết mô hình còn phải làm gì.

| Tệp | Việc |
|---|---|
| `app/understand.py` | đọc câu khách thành ràng buộc có cấu trúc |
| `app/answer.py` | tra thực đơn rồi viết câu trả lời |
| `app/test_understand.py` | 39 test, tập trung vào các chỗ đụng chữ |
| `evaluation/run_baseline.py` | chấm bằng thước đo bước 3 |
| `evaluation/run_ablation.py` | tắt từng cơ chế để đo giá trị của nó |

## 1. Kết quả, và cách đọc nó cho đúng

| Nhóm | Kết quả | Ý nghĩa |
|---|---|---|
| chốt an toàn | **14/14** | không ca an toàn nào đỏ |
| phát triển | **39/39** | nhưng tôi đã chỉnh sửa dựa trên chính tập này |
| **niêm phong — lần mở đầu tiên** | **23/27 (85,2%)** | **đây là con số held-out thật duy nhất** |
| niêm phong — sau khi sửa 3 lỗi nó chỉ ra | 27/27 | **không còn là held-out** |
| toàn bộ | 80/80 | cùng lý do |

Sàn để so: cách lách "luôn nói chưa có dữ liệu" qua được 12/80. Nên **85,2% là con số đáng
tin**, và 100% thì không nói được gì về khả năng tổng quát hóa.

Phải nói thẳng: **tập niêm phong giờ đã bị dùng hết.** Tôi mở nó để chốt bước 4, thấy 4 ca
đỏ, và sửa theo chúng. Đó là việc đúng — ba lỗi nó chỉ ra đều là thiếu sót thật — nhưng hệ
quả là mọi con số đo trên nó từ giờ đều là số đo trên dữ liệu đã thấy. Muốn có kết luận
held-out lần nữa thì phải viết ca **mới**, chưa từng dùng.

Bốn ca mà tập niêm phong bắt được:

| Ca | Lỗi thật | Đã sửa thành |
|---|---|---|
| `A-budget-04` "rẻ hơn 20 nghìn" | trả về Bia Sài Gòn Special đúng 20.000đ — **lỗi an toàn** | phân biệt "rẻ hơn X" (nghiêm ngặt, `<`) với "tầm X trở xuống" (bao gồm, `≤`) |
| `C-party-02` "Hai người ăn thì gọi gì" | hỏi lại thay vì gợi ý | nhận số người thành nhãn `party:*`, và số người ngầm định là bữa ăn |
| `C-party-03` "Đi một mình" | như trên | như trên |
| `C-compare-02` "Lẩu gà lá é với lẩu nấm chay" | chỉ nhận một món, vì tên đầy đủ là "Lẩu gà lá é **Đà Lạt**" | nhận **tiền tố duy nhất** của tên món |

## 2. Ba quy tắc cho phần đọc câu hỏi

Đây là cơ chế duy nhất đọc chữ của khách, và là nơi bản cũ chết.

**Quy tắc 1 — khớp cụm dài trước, rồi ăn hết đoạn đã khớp.** Bản cũ so từng nhãn với câu
hỏi một cách độc lập. Ở đây cụm nào khớp thì đoạn văn bản đó bị thay bằng khoảng trắng, nên
cụm ngắn hơn không còn thấy nó nữa.

**Quy tắc 2 — rút dấu để khớp cách khách gõ, không để quyết định nội dung.** Khách gõ
"mon nao khong cay k" thì phải hiểu; nhưng chữ đã rút dấu chỉ dùng để *tìm* ràng buộc, còn
nội dung câu trả lời luôn lấy từ thực đơn có dấu.

**Quy tắc 3 — mỗi cụm khai rõ nó suy ra ràng buộc gì.** `"khong cay" -> spice:none` viết ra
được, kiểm được.

### Ràng buộc, ngữ cảnh, và sự khác nhau giữa chúng

Phân biệt này sinh ra từ một ca đỏ, và nó là điều quan trọng nhất tôi học ở bước này.

"Tôi ăn chay" là **ràng buộc**: món không chay thì không được nêu. "Tôi đi hẹn hò" là
**ngữ cảnh**: món không mang nhãn `occasion:date` vẫn có thể phù hợp.

Bản đầu của tôi coi cả hai là ràng buộc, nên câu "Mình đi hẹn hò, nên gọi món gì?" chỉ còn
đúng **một** món (Tôm hùm 890.000đ) — vì `occasion:date` chỉ có trên vài món. Chính ca đánh
giá đã ghi trước điều này trong phần `why`: *"occasion chỉ phủ 79/91 nên thiếu nhãn không có
nghĩa món không phù hợp — vì thế không dùng nhãn này để loại trừ."*

Nay dịp ăn dùng để **sắp thứ tự**, không để lọc. Đây đúng là nguyên tắc ở bước 1: nhóm nhãn
không phủ hết 91 món thì thiếu nhãn nghĩa là *chưa ghi nhận*, không phải *không phù hợp*.

## 3. Sáu nhánh trả lời, không nhánh nào chồng nhánh nào

| Nhánh | Số ca | Việc |
|---|---|---|
| `filter` | 42 | lọc thực đơn theo ràng buộc |
| `clarify` | 8 | khách chưa nói gì đủ để lọc → hỏi lại, và đó là đúng |
| `item_detail` | 6 | nêu dữ kiện một món đã nêu tên |
| `price_lookup` | 4 | nêu giá |
| `compare` | 4 | so hai món |
| `policy:*` | 7 | chưa có dữ liệu (giờ mở cửa, thanh toán, đỗ xe, wifi, đặt bàn, giao hàng, dinh dưỡng) |
| `unknown_item` | 2 | món nhà hàng không bán |
| `off_topic`, `internal`, `no_size`, `extreme:*` | 7 | các trường hợp còn lại |

Bản cũ có 8 đường **chồng nhau** và 2 đường bị tắt mà vẫn chạy đúng. Ở đây thứ tự là thứ
tự loại trừ, và bảng trên đếm được nhánh nào phụ trách bao nhiêu ca.

## 4. Mỗi cơ chế phải tự chứng minh

Tắt từng cơ chế, chạy lại 80 ca:

| Cơ chế bị tắt | Qua | Mất | Lỗi an toàn |
|---|---|---|---|
| phân biệt món ăn với đồ uống | 68/80 | −12 | **6** |
| bỏ dấu câu khi chuẩn hóa | 67/80 | −13 | **5** |
| lọc theo dị nguyên (fail-closed) | 77/80 | −3 | **3** |
| phân biệt chủ đề dị nguyên với cách hỏi | 78/80 | −2 | **2** |
| phân biệt "rẻ hơn X" với "tầm X" | 79/80 | −1 | **1** |
| danh sách món nhà hàng không bán | 78/80 | −2 | 0 |
| ăn hết đoạn đã khớp | 79/80 | −1 | 0 |
| nhận tên món rút gọn | 79/80 | −1 | 0 |
| dịp ăn là ngữ cảnh | 79/80 | −1 | 0 |

**Cả 9 cơ chế đều có ít nhất một ca chứng minh giá trị**, và 5 trong đó ngăn được lỗi an
toàn. Cột lỗi an toàn quan trọng hơn cột "mất": một cơ chế chỉ cứu một ca nhưng ngăn được
lỗi dị ứng thì vẫn phải giữ.

Hai điều bất ngờ đáng ghi lại:

- **"Bỏ dấu câu" là cơ chế giá trị thứ hai.** Nghe như chuyện làm sạch chữ, nhưng thiếu nó
  thì "mấy giờ mở cửa**?**" không khớp cụm `mo cua`, và 13 ca đổ — trong đó 5 ca an toàn.
  Sáu test đầu của `test_understand.py` đã đỏ đúng vì lý do này.
- **Con số của "ăn hết đoạn đã khớp" là chặn dưới, không phải giá trị thật.** Kiểm kê trên
  323 cụm từ vựng và 91 tên món: **53 cụm bị chứa trong cụm từ vựng khác** (ví dụ khác nghĩa:
  `trung`⊂`mien trung`, `nam`⊂`mien nam`, `nam`⊂`nam nguoi`, `tra`⊂`tra tien`,
  `trung`⊂`dac trung`, `ga`⊂`mon ga`), **40 cụm nằm trong tên món** (`lac`⊂"Cơm bò lúc lắc",
  `bo`⊂"Sinh tố bơ Đắk Lắk", `sua`⊂"Cà phê sữa đá"), và hợp lại là **72 cụm có nguy cơ** — 21
  cụm thuộc cả hai. Tập đánh giá chỉ có ca cho **một** trong 72 chỗ đó. **Đây là phát hiện về
  tập đánh giá, không phải về cơ chế** — và tôi đã lấp bằng 9 test riêng thay vì để con số
  ablation nói sai.

  Ba con số trên **được tính lại mỗi lần chạy test**, không viết tay. Bản trước của mục này ghi
  "32 cụm" và "90 cụm"; hai số đó đúng lúc đo rồi từ vựng lớn dần lên mà không ai tính
  lại, tới lúc kiểm thì không cách đếm nào cho ra 32 hay 90 nữa. Nay
  `test_understand.collision_census()` tính, và `test_kiem_ke_dung_chu_khop_con_so_da_ghi` biến
  việc trôi thành **test đỏ** thay vì một dòng tài liệu sai âm thầm.

Cũng phải sửa một điều tôi nói trước đó: tôi từng bảo cơ chế ăn đoạn là thứ chặn lỗi
"bán chạy → món chay". Kiểm lại thì **không phải**: từ vựng không có cụm `chay` đứng một
mình (tôi tách thành `an chay` và `mon chay`), nên thứ chặn ca đó là **thiết kế từ vựng**.
Cơ chế ăn đoạn chặn 72 chỗ khác.

## 5. Một cơ chế bị bỏ vì nó gây hại

Tôi từng thêm heuristic đoán "khách đang hỏi một món cụ thể mà thực đơn không có": nếu sau
khi ăn hết từ vựng còn lại chữ không thuộc nhóm từ chung chung thì coi là món lạ.

Nó **bắt oan bốn ca dị ứng**. Câu "Mình dị ứng hải sản mà muốn ăn lẩu" còn lại chữ "mà", và
chữ đó bị coi là tên món lạ — nên hệ thống trả lời "thực đơn chưa có món đó" cho một lời
khai dị ứng. Số nền lúc đó là 46/53.

Mở rộng danh sách từ chung chung là trò đánh chuột vô tận, nên tôi **bỏ hẳn** cơ chế và chỉ
giữ một danh sách tường minh các món nhà hàng không bán (pizza, sushi, burger...). Số nền
lên **51/53**. Hẹp hơn nhưng nói được điều gì thì nói chắc điều đó.

Đây là ví dụ đúng cho nguyên tắc "ít cơ chế, mỗi cơ chế một việc": một cơ chế đoán mò làm
hệ thống tệ đi, không phải tốt lên.

## 6. Giới hạn phải nói ra

1. **Tập niêm phong đã bị dùng hết.** Con số held-out duy nhất là 23/27 (85,2%). Muốn kết
   luận lần nữa thì cần ca mới.
2. **80 ca do người viết, không phải log khách thật.** 100% trên tập này **không** có nghĩa
   100% với khách thật. Nó có nghĩa: trong phạm vi đã định nghĩa, hệ thống không vi phạm
   ràng buộc nào và không bịa dữ liệu.
3. **Từ vựng là danh sách viết tay.** Khách nói cách khác — "đồ chua chua", "món nào nhẹ
   bụng" — thì hệ thống không hiểu và sẽ hỏi lại. Hỏi lại tốt hơn đoán, nhưng vẫn là giới
   hạn.
4. **Chưa có kho tri thức.** 7 loại câu chính sách đều trả lời "chưa có dữ liệu". Đó là câu
   trả lời đúng hiện tại, nhưng không phải câu trả lời khách muốn. Bước 5.
5. **Chưa dùng mô hình sinh nào**, nên câu trả lời đúng nhưng khô. Ví dụ ca so sánh nêu
   đúng hai giá và khoảng cách, nhưng không nói được vị của từng món khác nhau ra sao. Bước
   6 sẽ đo xem mô hình thêm được gì mà **không** làm hỏng những gì đang đúng.
6. **`isAvailable` toàn `true`**, nên hành vi khi hết món vẫn không kiểm chứng được.

## 7. Cách chạy lại

```
python -m unittest discover -s ai/app -p "test_*.py"     # 39 test
python ai/evaluation/run_baseline.py                     # chốt + phát triển
python ai/evaluation/run_baseline.py --all --failures     # cả tập niêm phong
python ai/evaluation/run_ablation.py                     # giá trị từng cơ chế
```

Tất cả tất định: chạy lại nhiều lần cho đúng cùng kết quả.
