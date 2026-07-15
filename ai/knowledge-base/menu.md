---
id: kb.menu.descriptive.v1
title: Thực Đơn Mô Tả
domain: menu
tags: [menu, categories, descriptive]
language: vi
source: restaurant_ops_manual
reviewed_by: restaurant_manager
reviewed_at: 2026-07-13
expires_at: 2027-01-13
safety_level: medium
---

# Thực Đơn CMC Restaurant

## Tổng Quan Menu

CMC Restaurant phục vụ hơn 90 món ẩm thực Việt Nam đa vùng miền, chia thành 13 nhóm. Giá và trạng thái còn hàng lấy từ menu runtime (API), không lưu trong kho tri thức tĩnh.

## Khai Vị

Nhóm khai vị gồm các món nhẹ ăn đầu bữa hoặc ăn vặt:
- **Gỏi cuốn tôm thịt** (menu_item_id: m_001): cuốn tươi không chiên, thanh nhẹ, ít calo.
- **Nem rán Hà Nội** (menu_item_id: m_002): nem chiên giòn đặc trưng Bắc.
- **Bánh xèo miền Tây** (menu_item_id: m_003): giòn, nhân tôm thịt, ăn kèm rau sống.
- **Bánh cuốn Thanh Trì** (menu_item_id: m_004): tráng mỏng, nhẹ.
- **Gỏi xoài tôm sú** (menu_item_id: m_005): tươi mát, cay nhẹ.
- **Bánh mì pate Sài Gòn** (menu_item_id: m_006): ăn nhanh.
- **Súp măng cua** (menu_item_id: m_007): nóng, thanh.

## Phở & Bún

- **Phở bò tái nạm** (menu_item_id: m_008): nước dùng xương bò ninh lâu.
- **Phở gà ta** (menu_item_id: m_009): nhẹ hơn phở bò.
- **Bún bò Huế** (menu_item_id: m_010): cay đậm miền Trung.
- **Bún chả Hà Nội** (menu_item_id: m_011): thịt nướng than.
- **Bún riêu cua đồng** (menu_item_id: m_012): cua đồng, cà chua.
- **Bún mắm miền Tây** (menu_item_id: m_013): đa topping.
- **Bún đậu mắm tôm** (menu_item_id: m_014): đậu chiên, thịt luộc.

## Cơm Việt

- **Cơm tấm sườn bì chả** (menu_item_id: m_015)
- **Cơm gà Hội An** (menu_item_id: m_016)
- **Cơm sườn nướng** (menu_item_id: m_017)
- **Cơm cá kho tộ** (menu_item_id: m_018)
- **Cơm chiên Sài Gòn** (menu_item_id: m_019)
- **Cơm hến Huế** (menu_item_id: m_020)
- **Cơm bò lúc lắc** (menu_item_id: m_021)

## Hải Sản, Lẩu, Món Gà, Đặc Sản, Món Chay

Tham chiếu menu_item_id m_022–m_056 cho các nhóm hải sản, lẩu, gà, đặc sản vùng miền và món chay. Mô tả chi tiết thành phần nằm ở ingredient-nutrition và allergy-dietary.

## Đồ Uống & Tráng Miệng

- Cà phê & trà: menu_item_id m_057–m_063
- Nước ép & sinh tố: menu_item_id m_064–m_070
- Tráng miệng: menu_item_id m_071–m_077
- Trái cây tươi: menu_item_id m_078–m_084
- Bia & rượu: menu_item_id m_085–m_091 (18+)

## Quy Tắc Gợi Ý Món

1. AI chỉ gợi ý từ món đang còn hàng trong menu runtime.
2. Mặc định gợi ý 3 món, tối đa 8 món nếu khách yêu cầu.
3. Ưu tiên đa dạng category.
4. Không gợi ý lại món đã đề xuất/bị từ chối trong cùng session.
5. Không bịa món hoặc giá ngoài menu runtime.
