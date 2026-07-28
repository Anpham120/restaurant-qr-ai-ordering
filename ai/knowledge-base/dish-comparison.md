---
id: kb.guide.dish-comparison.v1
title: Hướng Dẫn So Sánh Món
domain: guidance
tags: [comparison, decision-support, menu]
language: vi
source: restaurant_ops_manual
reviewed_by: restaurant_manager
reviewed_at: 2026-07-28
expires_at: 2027-01-28
safety_level: medium
---

# Hướng Dẫn So Sánh Món

Khách thường không hỏi "món X là gì" mà hỏi "nên chọn X hay Y". Tài liệu này quy định cách trả
lời nhóm câu hỏi so sánh: dùng trục nào, lấy số liệu ở đâu, và tuyệt đối không được làm gì.

## Nguyên Tắc Chung Khi So Sánh
<!-- question_variants: so sanh, so sanh mon, nen chon mon nao, khac nhau the nao, khac gi nhau, mon nao ngon hon, chon cai nao -->

- So sánh phải dựa trên **dữ liệu có thật trong thực đơn và tài liệu dinh dưỡng**: giá, nguyên
  liệu, lượng calo, độ cay, nhóm món, tình trạng còn hàng.
- **Không xếp hạng theo "ngon hơn".** Độ ngon là chủ quan; trợ lý chỉ nêu khác biệt khách quan rồi
  để khách tự quyết.
- Khi khách nêu tiêu chí riêng (ít calo, không cay, tiết kiệm, cho trẻ em), **ưu tiên trục đó**
  thay vì liệt kê mọi trục.
- Chỉ so sánh các món **đang còn phục vụ**. Món hết hàng phải nói rõ là hết, không so sánh tiếp.
- Nếu một trong hai món không có trong thực đơn, nói rõ món nào không có thay vì so sánh phần còn
  lại như thể đủ cả hai.

## Sáu Trục So Sánh Chuẩn
<!-- question_variants: tieu chi so sanh, so sanh theo gi, dua vao dau de so sanh -->

| Trục | Nguồn dữ liệu | Dùng khi nào |
|---|---|---|
| Giá | Thực đơn trực tiếp | Khách nêu ngân sách hoặc hỏi món nào rẻ hơn |
| Nguyên liệu chính | `ingredient-nutrition.md` | Khách hỏi món làm từ gì, hoặc có kiêng thành phần nào |
| Lượng calo & đạm | `ingredient-nutrition.md` | Khách ăn kiêng, tập luyện, hỏi món nào nhẹ hơn |
| Độ cay | `spice-flavor-scale.md` | Khách sợ cay hoặc thích cay |
| Cách chế biến | `cooking-methods.md` | Khách hỏi món nào ít dầu, hấp hay chiên |
| Phù hợp đối tượng | `kids-elderly.md` | Đi cùng trẻ nhỏ hoặc người cao tuổi |

## Cách Trình Bày Câu Trả Lời So Sánh
<!-- question_variants: trinh bay so sanh, tra loi so sanh the nao -->

Cấu trúc ba phần, theo đúng thứ tự:

1. **Nêu khác biệt cốt lõi** — một hoặc hai câu, tập trung vào trục mà khách quan tâm nhất.
2. **Liệt kê số liệu đối chiếu** — chỉ các trục có dữ liệu thật, mỗi trục một dòng.
3. **Gợi ý theo tình huống** — "nếu bạn muốn nhẹ thì chọn A, muốn đậm đà thì chọn B", kèm thẻ gợi
   ý cho **cả hai** món để khách tự bấm.

Không kết luận thay khách. Không nói "món A ngon hơn món B".

## Ví Dụ So Sánh Phở Bò Và Phở Gà
<!-- question_variants: pho bo hay pho ga, so sanh pho bo pho ga, pho bo khac pho ga -->

- **Khác biệt cốt lõi:** phở bò đậm đà và nhiều đạm hơn; phở gà nhẹ hơn, dễ ăn.
- **Đối chiếu:** phở bò tái nạm khoảng 450 kcal, 28g đạm, nước dùng xương bò hầm lâu; phở gà ta
  khoảng 380 kcal, 24g đạm, nước dùng gà nhẹ hơn. Cả hai đều không cay.
- **Gợi ý:** ăn sáng hoặc muốn nhẹ bụng thì phở gà; muốn đậm đà, no lâu thì phở bò.

## Ví Dụ So Sánh Món Chiên Và Món Hấp
<!-- question_variants: chien hay hap, mon nao it dau, so sanh chien hap -->

- **Khác biệt cốt lõi:** món hấp ít dầu mỡ hơn rõ rệt so với món chiên.
- **Đối chiếu:** gỏi cuốn tôm thịt (không chiên) khoảng 180 kcal; nem rán Hà Nội (chiên giòn)
  khoảng 350 kcal; bánh cuốn Thanh Trì (hấp) khoảng 320 kcal nhưng ít dầu.
- **Gợi ý:** ưu tiên sức khoẻ hoặc người cao tuổi thì chọn món hấp/cuốn; muốn giòn, đậm vị thì
  chọn món chiên.

## Khi Khách So Sánh Nhiều Hơn Hai Món
<!-- question_variants: so sanh nhieu mon, so sanh ba mon -->

- Tối đa so sánh **bốn món** trong một lượt để câu trả lời còn đọc được.
- Nếu khách nêu quá nhiều món, hỏi lại xem trục nào quan trọng nhất với khách rồi lọc theo trục
  đó, thay vì cố liệt kê tất cả.

## Lưu Ý Cho AI
<!-- question_variants: luu y so sanh, gioi han so sanh -->

- Mọi con số nêu ra (giá, calo, đạm) **phải trích từ dữ liệu**, không được ước lượng. Nếu thiếu số
  liệu cho một món, nói rõ là chưa có thay vì đoán.
- Khi khách đã khai dị ứng, món chứa dị nguyên **không được đưa vào so sánh**, kể cả khi khách
  chủ động nhắc tên món đó — nêu rõ lý do loại.
- So sánh không phải lúc để bán thêm: không chèn món thứ ba khách không hỏi, trừ khi khách xin
  gợi ý thêm.
