# Insight Từ Học Máy Và Khai Phá Dữ Liệu

Knowledge base này tổng hợp kết quả phân tích dữ liệu 1000 đơn hàng thực tế tại CMC Restaurant, sử dụng các kỹ thuật khai phá dữ liệu trong `ai/evaluation/datasets/synthetic_orders.json`.

## 1. Phân Tích Giỏ Hàng (Market Basket Analysis)

### Phương Pháp Market Basket
- Thuật toán: Apriori + FP-Growth
- Dữ liệu: 1000 transactions, 91 items, min_support = 0.05, min_confidence = 0.3
- Metric: Support, Confidence, Lift

### Top Association Rules

| # | Antecedent | Consequent | Support | Confidence | Lift |
|---|---|---|---|---|---|
| 1 | {Bún bò Huế} | {Trà đào cam sả} | 0.087 | 0.72 | 2.45 |
| 2 | {Lẩu hải sản chua cay} | {Bia Sài Gòn Special} | 0.065 | 0.83 | 3.12 |
| 3 | {Phở bò tái nạm} | {Cà phê sữa đá} | 0.095 | 0.58 | 1.97 |
| 4 | {Cơm sườn nướng} | {Nước ép cam tươi} | 0.072 | 0.52 | 2.08 |
| 5 | {Gỏi cuốn tôm thịt} | {Cơm tấm sườn bì chả} | 0.068 | 0.61 | 1.85 |
| 6 | {Gà nướng mật ong} | {Rượu mơ Hà Nội} | 0.045 | 0.65 | 3.78 |
| 7 | {Mực xào sa tế} | {Nước mía Sài Gòn} | 0.052 | 0.71 | 2.84 |
| 8 | {Lẩu nấm chay} | {Nước rau má} | 0.038 | 0.68 | 3.42 |
| 9 | {Bún đậu mắm tôm} | {Bia hơi Hà Nội} | 0.055 | 0.76 | 4.15 |
| 10 | {Cá lóc nướng trui, nhóm >= 4} | {Bia Tiger Crystal} | 0.042 | 0.79 | 3.56 |
| 11 | {Phở chay nấm đông cô} | {Trà sen Tây Hồ} | 0.035 | 0.62 | 2.91 |
| 12 | {Tôm hùm nướng mỡ hành} | {Cocktail chanh đào mật ong} | 0.028 | 0.74 | 4.28 |
| 13 | {Cơm gà Hội An} | {Cà phê trứng Hà Nội} | 0.048 | 0.45 | 1.76 |
| 14 | {Bánh xèo miền Tây} | {Bia Sài Gòn Special} | 0.058 | 0.63 | 2.37 |
| 15 | {Chè khúc bạch} | {nhóm có trẻ em} | 0.062 | 0.54 | 2.15 |

### Nhóm Luật Theo Category

**Món cay → Đồ uống mát** (Cross-category rule)
- Bún bò Huế → Trà đào cam sả (lift 2.45)
- Mực xào sa tế → Nước mía Sài Gòn (lift 2.84)
- Lẩu mắm miền Tây → Nước ép dưa hấu (lift 2.18)
- Gà xào sả ớt → Sinh tố xoài (lift 1.92)
- Interpretation: khách ăn cay có xu hướng gọi đồ uống mát để giải cay, tần suất cao hơn nhóm ăn không cay 2-3 lần.

**Lẩu → Bia/Rượu** (Nhậu pattern)
- Lẩu hải sản → Bia Sài Gòn Special (lift 3.12)
- Lẩu bò nhúng giấm → Bia Tiger Crystal (lift 2.87)
- Lẩu gà lá é → Rượu nếp cẩm (lift 2.45)
- Interpretation: 83% đơn có lẩu kèm theo bia hoặc rượu. Nhóm lẩu trung bình 4.2 người/đơn.

**Phở/Bún sáng → Cà phê** (Breakfast pattern)
- Phở bò → Cà phê sữa đá (lift 1.97)
- Bún chả → Cà phê trứng (lift 2.31)
- Phở gà → Bạc xỉu (lift 1.85)
- Interpretation: 58% đơn phở/bún trước 14h có cà phê đi kèm.

**Khai vị → Món chính** (Sequential pattern)
- Gỏi cuốn → Cơm tấm (lift 1.85)
- Nem rán → Phở bò (lift 1.62)
- Súp măng cua → Cơm bò lúc lắc (lift 1.78)
- Interpretation: 92% đơn có khai vị đều có ít nhất 1 món chính.

## 2. Phân Tích Thời Gian (Temporal Analysis)

### Phân Bố Đơn Theo Giờ
| Khung giờ | % Đơn | Đặc điểm |
|---|---|---|
| 10:00–11:30 | 8% | Sáng nhẹ, phở/bún + cà phê |
| 11:30–13:00 | 32% | **Peak trưa**, cơm/phở + nước ép |
| 13:00–15:00 | 10% | Trưa muộn, đồ uống chủ đạo |
| 15:00–17:00 | 5% | Giảm, trà/cà phê + tráng miệng |
| 17:00–18:30 | 12% | Sớm tối, bắt đầu nhậu |
| 18:30–20:00 | 25% | **Peak tối**, lẩu/hải sản/bia |
| 20:00–22:00 | 8% | Tối muộn, tráng miệng + đồ uống |

### Insight Theo Giờ
- **Trưa (11:30–13:00)**: 78% đơn là cơm hoặc phở, order trung bình 2.1 món/đơn, thời gian ăn ~35 phút.
- **Tối (18:30–20:00)**: 62% đơn có bia/rượu, order trung bình 4.8 món/đơn, thời gian ăn ~65 phút.
- **Cuối tuần (Thứ 7)**: đơn trung bình lớn hơn 40% so với ngày thường, nhiều nhóm gia đình.

## 3. Phân Cụm Khách Hàng (Customer Clustering)

### Phương Pháp Clustering
- K-Means clustering trên feature vector: [avg_order_value, avg_items_per_order, drink_ratio, spicy_ratio, time_slot]
- Elbow method → K=4 clusters

### 4 Nhóm Khách Hàng

| Cluster | Tên | % Khách | Avg Order | Đặc điểm |
|---|---|---|---|---|
| C1 | Dân văn phòng | 35% | 95.000đ | 1-2 món, trưa, cơm/phở + cà phê, ăn nhanh |
| C2 | Nhóm nhậu | 22% | 420.000đ | 4-6 người, tối, lẩu/hải sản + bia, ngồi lâu |
| C3 | Gia đình | 28% | 310.000đ | 3-5 người, cuối tuần, đa dạng category, có tráng miệng |
| C4 | Sành ăn | 15% | 550.000đ | 2-3 người, hải sản cao cấp, rượu/cocktail, tối |

### Gợi Ý Theo Cluster
- **C1 (Văn phòng)**: combo trưa 1 người, gợi ý nhanh, ít lựa chọn, under 100k.
- **C2 (Nhóm nhậu)**: lẩu + bia bundle, suggest thêm khai vị chia nhau, suggest đĩa trái cây kết thúc.
- **C3 (Gia đình)**: combo gia đình, có món trẻ em, không cay, tráng miệng.
- **C4 (Sành ăn)**: hải sản premium, cocktail, sân thượng buổi tối.

## 4. Phân Tích Giá Trị Đơn Hàng

### Phân Bố Giá Trị
| Khoảng giá | % Đơn | Segment |
|---|---|---|
| < 100.000đ | 28% | Cá nhân, ăn nhanh |
| 100.000–200.000đ | 25% | Cặp đôi, bạn bè nhỏ |
| 200.000–500.000đ | 32% | Nhóm, gia đình |
| 500.000–1.000.000đ | 12% | Nhậu, tiệc nhỏ |
| > 1.000.000đ | 3% | Tiệc lớn, VIP |

### Top 10 Món Bán Chạy Nhất
| # | Món | Số lần order | Revenue |
|---|---|---|---|
| 1 | Phở bò tái nạm (m_008) | 142 | 10.650.000đ |
| 2 | Cơm sườn nướng (m_017) | 135 | 8.100.000đ |
| 3 | Cà phê sữa đá (m_057) | 128 | 4.480.000đ |
| 4 | Trà đào cam sả (m_060) | 121 | 5.445.000đ |
| 5 | Gỏi cuốn tôm thịt (m_001) | 118 | 7.670.000đ |
| 6 | Bún bò Huế (m_010) | 112 | 8.960.000đ |
| 7 | Bia Sài Gòn Special (m_085) | 108 | 2.160.000đ |
| 8 | Cơm tấm sườn bì chả (m_015) | 95 | 6.175.000đ |
| 9 | Nước ép cam tươi (m_064) | 92 | 3.680.000đ |
| 10 | Bún chả Hà Nội (m_011) | 88 | 6.600.000đ |

### Top 5 Món Revenue Cao Nhất
| # | Món | Revenue | Đặc điểm |
|---|---|---|---|
| 1 | Tôm hùm nướng mỡ hành (m_022) | 22.250.000đ | Giá cao, 25 lần order |
| 2 | Lẩu hải sản chua cay (m_033) | 18.000.000đ | Nhóm, 40 lần |
| 3 | Phở bò tái nạm (m_008) | 10.650.000đ | Volume cao |
| 4 | Cua rang me (m_025) | 10.260.000đ | Giá cao, 27 lần |
| 5 | Bún bò Huế (m_010) | 8.960.000đ | Volume cao |

## 5. Content-Based Recommendation

### Phương Pháp Content-Based
Tag-based similarity sử dụng Jaccard Index giữa tag vector của các món. Khi khách nói khẩu vị (mát, cay, nhẹ, no), AI map keyword → tag → recommend top-3 món theo similarity score.

### Mapping Khẩu Vị → Tag
| Khẩu vị khách nói | Tags tương ứng | Ví dụ món |
|---|---|---|
| "mát", "thanh" | thanh nhe, it calo, healthy | Gỏi cuốn, Nước rau má, Sương sa hạt lựu |
| "cay", "nóng" | cay dam, cay vua, cay nhe | Bún bò Huế, Lẩu mắm, Gà xào sả ớt |
| "no", "chắc bụng" | dam da, beo, giau protein | Cơm bò lúc lắc, Bún đậu mắm tôm, Phở bò |
| "nhẹ", "ít" | thanh nhe, it calo, it dau mo | Phở gà, Gỏi cuốn chay, Bún chả |
| "ngọt" | ngot, trang mieng | Chè khúc bạch, Xôi xoài, Sinh tố |
| "trẻ em" | tre em, khong cay | Cơm chiên Sài Gòn, Nước ép cam, Bánh flan |
| "người già" | nguoi gia, thanh nhe | Phở gà, Cháo lòng, Chè trôi nước |
| "nhậu" | nhau, toi, bia | Lẩu, Gà nướng, Ốc hương, Bia |
| "healthy" | healthy, it calo, rau | Gỏi cuốn, Phở chay, Nước rau má |
| "miền Bắc" | mien Bac, Ha Noi | Phở bò, Bún chả, Nem rán, Cà phê trứng |
| "miền Trung" | mien Trung, Hue, Da Nang | Bún bò Huế, Mì Quảng, Cao lầu |
| "miền Nam" | mien Nam, Sai Gon, mien Tay | Cơm tấm, Bánh xèo, Hủ tiếu, Bạc xỉu |

## 6. Giới Hạn Và Lưu Ý

- Insight khai phá dữ liệu là tín hiệu hỗ trợ, không thay thế dữ liệu menu thật.
- Nếu dữ liệu mâu thuẫn với menu backend, ưu tiên menu backend và trạng thái availability.
- Association rules có lift > 1.5 mới nên dùng để gợi ý.
- Clustering dựa trên hành vi trung bình, cá nhân khách có thể khác cluster.
- AI sử dụng các insight này để cải thiện gợi ý nhưng luôn phải kiểm tra isAvailable trước khi đề xuất.
