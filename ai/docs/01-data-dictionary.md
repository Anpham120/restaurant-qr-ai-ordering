# Bước 1 — Từ điển dữ liệu thực đơn

Bản cũ **không có** tài liệu này, và đó là nguyên nhân trực tiếp của bảy lỗi. Tài liệu
này trả lời: mỗi trường trong thực đơn nghĩa là gì, mỗi nhãn nghĩa là gì, và — quan
trọng nhất — **khi một nhãn không có mặt thì kết luận được điều gì**.

Nguồn máy đọc: `backend/data/menu-tags.json`, sinh bởi `ai/scripts/build_tag_dictionary.py`.

## 1. Phát hiện phải nói trước: có hai nguồn thực đơn, và chúng khác nhau

Ở bước 0 tôi viết "chỉ có một nguồn: `menu-dataset.json`". **Điều đó sai.** Kiểm tra
`/api/menu` cho thấy nó đọc `db.MenuItems`, tức cơ sở dữ liệu, không phải tệp JSON.

| | Cơ sở dữ liệu (khách thấy) | `menu-dataset.json` (AI dùng) |
|---|---|---|
| Nguồn | `RestaurantMenuSeed.cs`, migration `20260707233442` | tệp trong repo |
| Số món | 91 | 91 — **cùng tên, cùng mã** |
| Số nhãn khác nhau | 54 | 80 |
| Lần gán nhãn | 154 | 1.369 |
| Trung bình mỗi món | **1,7 nhãn** | **15,0 nhãn** |

Không migration nào sau `20260707` chạm vào `Tags`, nên khoảng cách này là trạng thái
hiện hành, không phải tạm thời.

**Hệ quả:** bản AI cũ suy luận trên tập nhãn dày gấp gần chín lần thứ mà ứng dụng thật
phục vụ khách. Mọi con số đánh giá của nó đo trên dữ liệu giàu hơn thực tế. Đây là lỗ
hổng về giá trị của kết quả, không phải lỗi mã, và không có test nào bắt được vì hai
nguồn chưa từng được so với nhau.

**Chưa quyết:** hợp nhất theo hướng nào. Hai lựa chọn, và đây là việc cần chủ dự án chọn
vì nó đụng dữ liệu production:

- **Làm giàu cơ sở dữ liệu** theo tệp JSON (một migration cập nhật `Tags` cho 91 món).
  AI và khách nhìn cùng một thứ; khách được lợi vì thẻ nhãn trên món đầy đủ hơn.
- **Giữ nguyên**, và AI chỉ được dùng 54 nhãn mà DB thật có. Trung thực với production
  nhưng bỏ mất phần lớn thông tin đã có sẵn.

Tôi nghiêng về phương án thứ nhất, nhưng chưa làm: viết migration sửa dữ liệu production
vượt quá phạm vi "gán nhãn lại".

## 2. Các trường của một món

| Trường | Loại | Là sự thật hay nhãn suy ra | Ghi chú |
|---|---|---|---|
| `id` | chuỗi `m_001`…`m_091` | sự thật | khóa ổn định, dùng để tham chiếu |
| `name` | chuỗi | sự thật | tên hiển thị, có dấu |
| `description` | chuỗi | sự thật, nhưng **là câu giới thiệu** | không phải danh sách thành phần đầy đủ |
| `price` | số nguyên (đồng) | sự thật | 12.000 – 890.000, trung vị 65.000 |
| `categoryId` / `categoryName` | chuỗi | sự thật | 13 danh mục, mỗi danh mục đúng 7 món |
| `imageUrl` | chuỗi | sự thật | |
| `isAvailable` | bool | sự thật *về lý thuyết* | **cả 91 món đều `true`** → không kiểm chứng được hành vi khi hết món |
| `tags` | danh sách khóa | **nhãn do người gán** | phần còn lại của tài liệu này nói về nó |

Điểm dễ nhầm nhất: `description` **không** phải bảng thành phần. Nó là câu quảng cáo có
kèm vài chi tiết. Dùng nó để khẳng định "món này không có X" là sai — xem mục 5.

## 3. Vì sao nhãn được gán lại thành khóa có không gian tên

Nhãn cũ là từ tiếng Việt trần: `toi`, `ca`, `nam`, `cua`, `chay`. Để khớp với cách khách
gõ (thường không dấu), bản cũ rút dấu rồi so chuỗi — và cả bảy lỗi đều sinh ra ở đây:

| Nhãn | Nghĩa thật | Đụng từ | Hậu quả đã xảy ra |
|---|---|---|---|
| `cua` | con cua | của, cửa | câu hỏi giờ mở cửa bị gán dị ứng hải sản |
| `chay` | ăn chay | chạy | "món bán chạy" khớp vào món chay |
| `trung` | trứng | miền Trung | dị ứng trứng loại 43/91 món, chỉ 7 món đúng |
| `bo` | bơ (nguồn sữa) | bò | dị ứng sữa loại cả phở bò |
| `muc` | mực | mức | "chọn mức đường" khớp vào mực |
| `lac` | đậu lạc | lắc | "bò lúc lắc" khớp vào đậu phộng |
| `tra` | trà | tráng | "tráng miệng menu" trả về bốn loại trà |

Khớp theo biên từ cũng không cứu được, vì **ba nhãn có token nằm trong nhãn khác**:
`nam` (nấm) nằm trong `quanh nam` và `mien Nam`; `ca` (cá) nằm trong `ca nhan`.

Và nhãn nhập nhằng nhất là `toi`, có trên 64/91 món: "tối" (bữa tối) hay "tỏi" (gia vị)?
Bản cũ đoán là "tỏi".

**Câu trả lời đã có sẵn trong repo suốt thời gian đó.**
`frontend/src/components/menu/MenuItemCard.tsx` chứa từ điển 80 nhãn → nhãn tiếng Việt
do người làm giao diện viết, phủ đúng 80/80 nhãn, và ghi rõ `"toi": "Tối"`. Bốn phép thử
độc lập trên dữ liệu cũng cho cùng kết luận: Tráng miệng 7/7, Trái cây tươi 7/7 và
Bia & Rượu 7/7 đều mang nhãn `toi`, mà không món nào trong đó có tỏi.

Bài học không phải "cần cẩn thận hơn" mà là: **tri thức này nằm ở ba nơi tách biệt và
không có gì canh chúng khỏi trôi khỏi nhau.** Nay chỉ còn một nguồn, và có test canh.

Khóa mới xóa cả lớp lỗi này về mặt cấu trúc, chứ không vá từng ca: khách không bao giờ
gõ chuỗi `meal:dinner`, nên không còn gì để trùng.

## 4. Mười lăm nhóm nhãn

Mọi khóa có dạng `nhóm:giá_trị`. Cột "Số món" đếm số món mang **ít nhất một** nhãn của
nhóm đó — con số quan trọng nhất trong bảng, vì nó quyết định có được suy luận từ việc
thiếu nhãn hay không (mục 5).

| Nhóm | Số nhãn | Loại trừ | Số món | Giá trị |
|---|---|---|---|---|
| `meal` | 4 | — | **91/91** | `breakfast`, `lunch`, `dinner`, `late_night` |
| `party` | 6 | — | **91/91** | `solo`, `two_three`, `three_five`, `share`, `friends`, `family` |
| `price` | 4 | **có** | **91/91** | `budget`, `mid`, `high`, `premium` |
| `season` | 4 | — | **91/91** | `all_year`, `hot_season`, `cold_season`, `cooling` |
| `spice` | 4 | **có** | **91/91** | `none`, `mild`, `medium`, `hot` |
| `occasion` | 6 | — | 78/91 | `everyday`, `banquet`, `birthday`, `business`, `date`, `drinking` |
| `flavour` | 6 | — | 72/91 | `rich`, `fatty`, `sour`, `sweet`, `salty`, `smoky` |
| `health` | 6 | — | 67/91 | `healthy`, `light`, `low_calorie`, `low_fat`, `high_protein`, `no_msg` |
| `region` | 9 | — | 65/91 | `north`, `central`, `south`, `mekong`, `hanoi`, `hue`, `saigon`, `danang`, `highlands` |
| `ingredient` | 10 | — | 57/91 | `beef`, `pork`, `chicken`, `fish`, `shrimp`, `squid`, `crab`, `tofu`, `mushroom`, `vegetable` |
| `method` | 10 | — | 57/91 | `grilled`, `fried`, `steamed`, `stir_fried`, `braised`, `boiled`, `roasted`, `stewed`, `simmered`, `rolled` |
| `audience` | 2 | — | 51/91 | `child`, `elderly` |
| `allergen` | 5 | — | 44/91 | `seafood`, `peanut`, `egg`, `dairy`, `gluten` |
| `serving` | 2 | — | 23/91 | `preorder`, `takeaway` |
| `diet` | 2 | — | 17/91 | `vegetarian`, `vegan` |

**Loại trừ** nghĩa là một món chỉ được mang đúng một giá trị của nhóm. Nếu một món vừa
`spice:none` vừa `spice:hot` thì không câu trả lời nào về độ cay của nó đúng được. Đã
kiểm: 0/91 món vi phạm, và có test canh.

Mỗi nhãn có ba dạng, trong `menu-tags.json`:

```
"meal:dinner": { "group": "meal", "value": "dinner",
                 "label_vi": "Tối", "label_en": "Dinner",
                 "legacy_key": "toi", "exclusive": false }
```

- `meal:dinner` — khóa AI khớp chính xác.
- `label_vi` / `label_en` — chữ khách đọc.
- `legacy_key` — tên cũ, giữ lại vì `/api/menu` vẫn trả về dạng đó (mục 1).

## 5. Điều quan trọng nhất: thiếu nhãn nghĩa là gì

Đây là chỗ bản cũ sai nguy hiểm nhất, và là lý do tài liệu này tồn tại.

Năm nhóm phủ **91/91** — `meal`, `party`, `price`, `season`, `spice`. Với chúng, thiếu
nhãn là **bất thường về dữ liệu**, không phải thông tin. Có thể lọc thẳng.

Mười nhóm còn lại **không phủ hết**. Với chúng, thiếu nhãn nghĩa là *chưa ghi nhận*,
**không** phải *không có*. `allergen` chỉ phủ 44/91: bốn mươi bảy món không mang nhãn dị
nguyên nào — và điều đó không cho phép nói chúng không chứa dị nguyên.

**Bằng chứng, không phải suy đoán.** Đối chiếu nhãn với mô tả món tìm ra bảy lỗ nhãn thật:

| Món | Nhãn thiếu | Căn cứ trong mô tả |
|---|---|---|
| Bún đậu mắm tôm | `allergen:seafood` | "Chấm mắm tôm pha chanh đường ớt" |
| Cơm cá kho tộ | `allergen:seafood` | "Cá basa phi lê kho tộ" |
| Cá lóc nướng trui | `allergen:seafood` | "Cá lóc đồng nướng", "chấm mắm nêm" |
| Lẩu chua cá lăng | `allergen:seafood` | "Cá lăng cắt khúc (~800g)" |
| Bánh tráng cuốn thịt heo | `allergen:seafood` | "chấm mắm nêm tỏi ớt" |
| Bê thui Cầu Mống | `allergen:seafood` | "chấm mắm nêm cay" |
| Cua rang me | `allergen:gluten` | "Ăn kèm bánh mì nóng" |

Bảy nhãn này đã được bổ sung (`allergen:seafood` 20→26, `gluten` 6→7, số món có nhãn dị
nguyên 39→44). Chỉ bổ sung theo chiều **làm chặt hơn**, không bao giờ bớt nhãn, vì căn cứ
là mô tả trên thực đơn — **không phải kiểm tra bếp**.

**Ba kết luận bắt buộc cho thiết kế:**

1. Lọc dị nguyên phải **fail-closed**: loại món khi có nhãn, và loại cả khi mô tả nêu
   thành phần đó. Không suy ra "an toàn" từ việc thiếu nhãn.
2. AI **không được** nói một món an toàn với người dị ứng. Chỉ được nói thực đơn *ghi
   nhận* hoặc *không ghi nhận*, và luôn mở đường hỏi nhân viên.
3. Với nhóm không phủ hết như `spice` thì ngược lại: `spice` phủ 91/91 nên lọc "không
   cay" là kết luận được. Nhưng `diet` chỉ phủ 17/91, nên thiếu `diet:vegetarian`
   **không** nghĩa là món có thịt.

Bảng phân tuyến:

| Nhóm | Phủ | Thiếu nhãn thì kết luận gì | Cách lọc |
|---|---|---|---|
| `meal`, `party`, `price`, `season`, `spice` | 91/91 | lỗi dữ liệu | lọc thẳng |
| `allergen` | 44/91 | **chưa ghi nhận** — không kết luận | fail-closed + đối chiếu mô tả + luôn nhắc hỏi nhân viên |
| `diet`, `audience`, `serving`, `health` | 17–67/91 | chưa ghi nhận | chỉ dùng theo chiều khẳng định |
| `ingredient`, `method`, `region`, `flavour`, `occasion` | 57–78/91 | chưa ghi nhận | dùng để gợi ý, không dùng để loại trừ |

## 6. Cách kiểm chứng

Từ điển và dữ liệu sinh lại được, và chạy lại nhiều lần cho cùng kết quả:

```
python ai/scripts/build_tag_dictionary.py --check   # chỉ kiểm, không ghi
python ai/scripts/build_tag_dictionary.py           # ghi từ điển + gán nhãn lại
```

`frontend/src/components/menu/menuTagDictionary.test.ts` canh phần dễ trôi nhất — bảy ca,
và đã được chứng minh bắt được lỗi thật, không chỉ xanh:

| Ca | Chặn điều gì |
|---|---|
| phủ mọi nhãn trong thực đơn | nhãn dùng mà thiếu định nghĩa |
| nhãn tiếng Việt cho mọi khóa | đã thử đổi `"Tối"`→`"Tỏi"`, test đỏ đúng chỗ |
| nhãn tiếng Anh cho mọi khóa | bản viết tay cũ chỉ phủ 54/80 |
| tên nhãn cũ vẫn hiển thị đúng | đã thử xóa alias `binh dan`, test đỏ |
| nhãn lạ trả về nguyên văn | chiều ngược: chứng minh hàm thật sự tra bảng |
| khóa không lồng vào nhau | chính lỗi `nam` ⊂ `quanh nam` của bản cũ |
| nhóm loại trừ chỉ một giá trị | món có hai mức cay |

Trạng thái: 107 test frontend cũ vẫn xanh, typecheck sạch cả 12 workspace.

## 7. Còn lại chưa giải quyết

1. **Hai nguồn thực đơn lệch nhau** (mục 1) — cần quyết định hợp nhất.
2. **Nhãn dị nguyên vẫn có thể còn thiếu.** Bảy lỗ tìm được bằng cách đọc mô tả; mô tả
   không phải bảng thành phần, nên còn thiếu bao nhiêu thì **không biết được từ dữ liệu
   này**. Chỉ nhà hàng trả lời được.
3. **`isAvailable` toàn `true`** — hành vi khi hết món không kiểm chứng được.
4. **Nhãn là do người gán, không phải đo.** `health:healthy`, `flavour:rich` là đánh giá
   cảm quan của người nhập liệu. Dùng để gợi ý được, dùng để khẳng định thì không.
