"""Generate synthetic order data for data mining experiments.

Generates 1000 realistic restaurant orders with patterns:
- Spicy food -> cold drinks (support ~0.7)
- Hot pot -> beer (support ~0.8)
- Coffee -> morning/after meal (support ~0.6)
- Appetizer -> main course (support ~0.9)
- Dessert -> after heavy main (support ~0.5)
- Beer/wine -> evening (support ~0.75)
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

random.seed(20260714)

# Menu items by category
MENU = {
    "khai_vi": [
        {"id": "m_004", "name": "Bánh cuốn Thanh Trì", "price": 55000, "tags": ["khong cay", "sang"]},
        {"id": "m_006", "name": "Bánh mì pate Sài Gòn", "price": 35000, "tags": ["cay nhe", "sang"]},
        {"id": "m_003", "name": "Bánh xèo miền Tây", "price": 85000, "tags": ["khong cay"]},
        {"id": "m_001", "name": "Gỏi cuốn tôm thịt", "price": 65000, "tags": ["khong cay", "it calo"]},
        {"id": "m_005", "name": "Gỏi xoài tôm sú", "price": 85000, "tags": ["cay nhe"]},
        {"id": "m_002", "name": "Nem rán Hà Nội", "price": 75000, "tags": ["khong cay"]},
        {"id": "m_007", "name": "Súp măng cua", "price": 65000, "tags": ["khong cay"]},
    ],
    "pho_bun": [
        {"id": "m_010", "name": "Bún bò Huế", "price": 80000, "tags": ["cay dam"]},
        {"id": "m_011", "name": "Bún chả Hà Nội", "price": 75000, "tags": ["khong cay"]},
        {"id": "m_013", "name": "Bún mắm miền Tây", "price": 85000, "tags": ["cay nhe"]},
        {"id": "m_012", "name": "Bún riêu cua đồng", "price": 70000, "tags": ["khong cay"]},
        {"id": "m_014", "name": "Bún đậu mắm tôm", "price": 95000, "tags": ["cay vua"]},
        {"id": "m_008", "name": "Phở bò tái nạm", "price": 75000, "tags": ["khong cay"]},
        {"id": "m_009", "name": "Phở gà ta", "price": 70000, "tags": ["khong cay"]},
    ],
    "com_viet": [
        {"id": "m_021", "name": "Cơm bò lúc lắc", "price": 95000, "tags": ["khong cay"]},
        {"id": "m_019", "name": "Cơm chiên Sài Gòn", "price": 55000, "tags": ["khong cay"]},
        {"id": "m_018", "name": "Cơm cá kho tộ", "price": 65000, "tags": ["cay nhe"]},
        {"id": "m_016", "name": "Cơm gà Hội An", "price": 70000, "tags": ["khong cay"]},
        {"id": "m_020", "name": "Cơm hến Huế", "price": 55000, "tags": ["cay vua"]},
        {"id": "m_017", "name": "Cơm sườn nướng", "price": 60000, "tags": ["cay nhe"]},
        {"id": "m_015", "name": "Cơm tấm sườn bì chả", "price": 65000, "tags": ["khong cay"]},
    ],
    "hai_san": [
        {"id": "m_025", "name": "Cua rang me", "price": 380000, "tags": ["khong cay"]},
        {"id": "m_023", "name": "Cá lóc nướng trui", "price": 195000, "tags": ["cay nhe"]},
        {"id": "m_026", "name": "Mực xào sa tế", "price": 135000, "tags": ["cay dam"]},
        {"id": "m_027", "name": "Nghêu hấp sả", "price": 95000, "tags": ["cay nhe"]},
        {"id": "m_022", "name": "Tôm hùm nướng mỡ hành", "price": 890000, "tags": ["khong cay"]},
        {"id": "m_024", "name": "Tôm rang muối Tây Ninh", "price": 185000, "tags": ["cay nhe"]},
        {"id": "m_028", "name": "Ốc hương rang bơ tỏi", "price": 165000, "tags": ["khong cay"]},
    ],
    "lau": [
        {"id": "m_030", "name": "Lẩu bò nhúng giấm", "price": 350000, "tags": ["khong cay"]},
        {"id": "m_029", "name": "Lẩu chua cá lăng", "price": 320000, "tags": ["khong cay"]},
        {"id": "m_034", "name": "Lẩu dê thuốc bắc", "price": 380000, "tags": ["cay nhe"]},
        {"id": "m_032", "name": "Lẩu gà lá é Đà Lạt", "price": 280000, "tags": ["khong cay"]},
        {"id": "m_033", "name": "Lẩu hải sản chua cay", "price": 450000, "tags": ["cay dam"]},
        {"id": "m_035", "name": "Lẩu mắm miền Tây", "price": 320000, "tags": ["cay vua"]},
        {"id": "m_031", "name": "Lẩu nấm chay", "price": 250000, "tags": ["khong cay"]},
    ],
    "mon_ga": [
        {"id": "m_038", "name": "Cánh gà chiên nước mắm", "price": 95000, "tags": ["cay nhe"]},
        {"id": "m_037", "name": "Gà hấp lá chanh", "price": 280000, "tags": ["khong cay"]},
        {"id": "m_040", "name": "Gà nướng muối ớt xanh", "price": 195000, "tags": ["cay vua"]},
        {"id": "m_036", "name": "Gà nướng mật ong", "price": 185000, "tags": ["khong cay"]},
        {"id": "m_042", "name": "Gà rô ti kiểu Việt", "price": 320000, "tags": ["khong cay"]},
        {"id": "m_041", "name": "Gà tiềm thuốc bắc", "price": 250000, "tags": ["khong cay"]},
        {"id": "m_039", "name": "Gà xào sả ớt", "price": 95000, "tags": ["cay vua"]},
    ],
    "dac_san": [
        {"id": "m_047", "name": "Bánh tráng cuốn thịt heo", "price": 85000, "tags": ["cay nhe"]},
        {"id": "m_045", "name": "Bê thui Cầu Mống", "price": 350000, "tags": ["cay nhe"]},
        {"id": "m_044", "name": "Cao lầu Hội An", "price": 80000, "tags": ["khong cay"]},
        {"id": "m_048", "name": "Cháo lòng Sài Gòn", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_046", "name": "Hủ tiếu Nam Vang", "price": 65000, "tags": ["khong cay"]},
        {"id": "m_043", "name": "Mì Quảng tôm thịt", "price": 70000, "tags": ["cay nhe"]},
        {"id": "m_049", "name": "Xôi gà Hà Nội", "price": 50000, "tags": ["khong cay"]},
    ],
    "chay": [
        {"id": "m_056", "name": "Bún chay Huế", "price": 55000, "tags": ["cay vua"]},
        {"id": "m_053", "name": "Canh khổ qua nhồi nấm", "price": 55000, "tags": ["khong cay"]},
        {"id": "m_051", "name": "Cơm chiên chay ngũ sắc", "price": 50000, "tags": ["khong cay"]},
        {"id": "m_052", "name": "Gỏi cuốn chay", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_055", "name": "Mì Quảng chay", "price": 55000, "tags": ["cay nhe"]},
        {"id": "m_050", "name": "Phở chay nấm đông cô", "price": 60000, "tags": ["khong cay"]},
        {"id": "m_054", "name": "Đậu hũ sốt cà chua", "price": 45000, "tags": ["khong cay"]},
    ],
    "ca_phe_tra": [
        {"id": "m_059", "name": "Bạc xỉu Sài Gòn", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_063", "name": "Cà phê dừa", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_057", "name": "Cà phê sữa đá", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_058", "name": "Cà phê trứng Hà Nội", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_061", "name": "Trà sen Tây Hồ", "price": 55000, "tags": ["khong cay"]},
        {"id": "m_062", "name": "Trà sữa trân châu", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_060", "name": "Trà đào cam sả", "price": 45000, "tags": ["khong cay"]},
    ],
    "nuoc_ep": [
        {"id": "m_070", "name": "Nước mía Sài Gòn", "price": 25000, "tags": ["khong cay"]},
        {"id": "m_068", "name": "Nước rau má", "price": 30000, "tags": ["khong cay"]},
        {"id": "m_064", "name": "Nước ép cam tươi", "price": 40000, "tags": ["khong cay"]},
        {"id": "m_066", "name": "Nước ép dưa hấu", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_065", "name": "Sinh tố bơ Đắk Lắk", "price": 50000, "tags": ["khong cay"]},
        {"id": "m_069", "name": "Sinh tố dâu tây Đà Lạt", "price": 50000, "tags": ["khong cay"]},
        {"id": "m_067", "name": "Sinh tố xoài Hòa Lộc", "price": 45000, "tags": ["khong cay"]},
    ],
    "trang_mieng": [
        {"id": "m_076", "name": "Bánh chuối nướng", "price": 30000, "tags": ["khong cay"]},
        {"id": "m_072", "name": "Bánh flan caramel", "price": 30000, "tags": ["khong cay"]},
        {"id": "m_073", "name": "Chè bưởi", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_071", "name": "Chè khúc bạch", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_075", "name": "Chè trôi nước", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_074", "name": "Sương sa hạt lựu", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_077", "name": "Xôi xoài", "price": 45000, "tags": ["khong cay"]},
    ],
    "trai_cay": [
        {"id": "m_082", "name": "Bưởi da xanh Bến Tre", "price": 55000, "tags": ["khong cay"]},
        {"id": "m_081", "name": "Dưa hấu lạnh", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_080", "name": "Sầu riêng Ri6", "price": 120000, "tags": ["khong cay"]},
        {"id": "m_083", "name": "Thanh long Bình Thuận", "price": 45000, "tags": ["khong cay"]},
        {"id": "m_079", "name": "Xoài cát Hòa Lộc", "price": 65000, "tags": ["khong cay"]},
        {"id": "m_084", "name": "Đu đủ chín mật ong", "price": 40000, "tags": ["khong cay"]},
        {"id": "m_078", "name": "Đĩa trái cây theo mùa", "price": 75000, "tags": ["khong cay"]},
    ],
    "bia_ruou": [
        {"id": "m_085", "name": "Bia Sài Gòn Special", "price": 20000, "tags": ["khong cay"]},
        {"id": "m_086", "name": "Bia Hà Nội", "price": 18000, "tags": ["khong cay"]},
        {"id": "m_087", "name": "Bia Tiger Crystal", "price": 22000, "tags": ["khong cay"]},
        {"id": "m_088", "name": "Bia hơi Hà Nội", "price": 12000, "tags": ["khong cay"]},
        {"id": "m_089", "name": "Rượu nếp cẩm", "price": 35000, "tags": ["khong cay"]},
        {"id": "m_090", "name": "Rượu mơ Hà Nội", "price": 40000, "tags": ["khong cay"]},
        {"id": "m_091", "name": "Cocktail chanh đào mật ong", "price": 65000, "tags": ["khong cay"]},
    ],
}

COLD_DRINKS = MENU["nuoc_ep"] + [m for m in MENU["ca_phe_tra"] if m["id"] in ("m_060", "m_070")]
BEER = [m for m in MENU["bia_ruou"] if "Bia" in m["name"]]
COFFEE = [m for m in MENU["ca_phe_tra"] if "phê" in m["name"] or "xỉu" in m["name"]]
DESSERT = MENU["trang_mieng"]
APPETIZER = MENU["khai_vi"]
MAIN_COURSES = MENU["pho_bun"] + MENU["com_viet"]

TABLES = [f"T{i:02d}" for i in range(1, 26)]
PAYMENT_METHODS = ["cash", "vietqr"]
BASE_DATE = datetime(2026, 6, 1)


def is_spicy(item):
    return any(t in item.get("tags", []) for t in ["cay dam", "cay vua", "cay nhe"])


def gen_timestamp(day_offset, hour):
    minute = random.randint(0, 59)
    return (BASE_DATE + timedelta(days=day_offset, hours=hour, minutes=minute)).isoformat() + "+07:00"


def gen_order(order_id, day_offset):
    # Time slot distribution
    r = random.random()
    if r < 0.08:
        hour = random.choice([10, 11])
        slot = "morning"
    elif r < 0.40:
        hour = random.choice([11, 12, 12, 12, 13])
        slot = "lunch"
    elif r < 0.50:
        hour = random.choice([13, 14])
        slot = "afternoon_early"
    elif r < 0.55:
        hour = random.choice([15, 16])
        slot = "afternoon_late"
    elif r < 0.67:
        hour = random.choice([17, 18])
        slot = "evening_early"
    elif r < 0.92:
        hour = random.choice([18, 19, 19, 19, 20])
        slot = "dinner"
    else:
        hour = random.choice([20, 21])
        slot = "late_night"

    # Customer segment
    seg_r = random.random()
    if seg_r < 0.35:
        segment = "office"
        group_size = random.choice([1, 1, 1, 2])
    elif seg_r < 0.57:
        segment = "drinking"
        group_size = random.choice([3, 4, 4, 5, 6])
    elif seg_r < 0.85:
        segment = "family"
        group_size = random.choice([3, 3, 4, 4, 5])
    else:
        segment = "gourmet"
        group_size = random.choice([2, 2, 3])

    items = []

    if segment == "office":
        # 1-2 main + 1 drink
        main = random.choice(MAIN_COURSES)
        items.append({"menu_item_id": main["id"], "name": main["name"], "price": main["price"], "quantity": 1})
        if group_size == 2:
            main2 = random.choice(MAIN_COURSES)
            items.append({"menu_item_id": main2["id"], "name": main2["name"], "price": main2["price"], "quantity": 1})
        # Coffee or juice
        if slot in ("morning", "lunch") and random.random() < 0.58:
            drink = random.choice(COFFEE)
        else:
            drink = random.choice(COLD_DRINKS + COFFEE)
        items.append({"menu_item_id": drink["id"], "name": drink["name"], "price": drink["price"], "quantity": group_size})
        # Occasionally dessert
        if random.random() < 0.15:
            d = random.choice(DESSERT)
            items.append({"menu_item_id": d["id"], "name": d["name"], "price": d["price"], "quantity": 1})

    elif segment == "drinking":
        # Hot pot or seafood + beer
        if random.random() < 0.55:
            lau = random.choice(MENU["lau"])
            items.append({"menu_item_id": lau["id"], "name": lau["name"], "price": lau["price"], "quantity": 1})
        else:
            for _ in range(random.randint(2, 3)):
                sea = random.choice(MENU["hai_san"] + MENU["mon_ga"])
                items.append({"menu_item_id": sea["id"], "name": sea["name"], "price": sea["price"], "quantity": 1})
        # Appetizer
        if random.random() < 0.7:
            app = random.choice(APPETIZER)
            items.append({"menu_item_id": app["id"], "name": app["name"], "price": app["price"], "quantity": random.choice([1, 2])})
        # Beer (high probability)
        if random.random() < 0.83:
            beer = random.choice(BEER)
            items.append({"menu_item_id": beer["id"], "name": beer["name"], "price": beer["price"], "quantity": random.randint(2, group_size * 2)})
        else:
            wine = random.choice(MENU["bia_ruou"][4:])
            items.append({"menu_item_id": wine["id"], "name": wine["name"], "price": wine["price"], "quantity": random.randint(1, 3)})
        # Spicy -> cold drink
        spicy_items = [i for i in items if is_spicy(i)]
        if spicy_items and random.random() < 0.72:
            cd = random.choice(COLD_DRINKS)
            items.append({"menu_item_id": cd["id"], "name": cd["name"], "price": cd["price"], "quantity": random.randint(1, 2)})
        # Fruit plate to end
        if random.random() < 0.35:
            fruit = random.choice(MENU["trai_cay"])
            items.append({"menu_item_id": fruit["id"], "name": fruit["name"], "price": fruit["price"], "quantity": 1})

    elif segment == "family":
        # Mix of categories
        # Appetizer
        app = random.choice(APPETIZER)
        items.append({"menu_item_id": app["id"], "name": app["name"], "price": app["price"], "quantity": 1})
        # Main courses (multiple)
        for _ in range(random.randint(2, 3)):
            main = random.choice(MAIN_COURSES + MENU["dac_san"])
            items.append({"menu_item_id": main["id"], "name": main["name"], "price": main["price"], "quantity": 1})
        # Drinks
        drink = random.choice(COLD_DRINKS + MENU["ca_phe_tra"])
        items.append({"menu_item_id": drink["id"], "name": drink["name"], "price": drink["price"], "quantity": group_size})
        # Dessert (higher prob with family)
        if random.random() < 0.55:
            d = random.choice(DESSERT)
            items.append({"menu_item_id": d["id"], "name": d["name"], "price": d["price"], "quantity": random.randint(1, 3)})
        # Spicy -> cold drink
        spicy_items = [i for i in items if is_spicy(i)]
        if spicy_items and random.random() < 0.68:
            cd = random.choice(COLD_DRINKS)
            items.append({"menu_item_id": cd["id"], "name": cd["name"], "price": cd["price"], "quantity": 1})

    elif segment == "gourmet":
        # Premium items
        if random.random() < 0.6:
            sea = random.choice([m for m in MENU["hai_san"] if m["price"] >= 165000])
            items.append({"menu_item_id": sea["id"], "name": sea["name"], "price": sea["price"], "quantity": 1})
        ga = random.choice([m for m in MENU["mon_ga"] if m["price"] >= 185000])
        items.append({"menu_item_id": ga["id"], "name": ga["name"], "price": ga["price"], "quantity": 1})
        # Wine/cocktail
        wine = random.choice(MENU["bia_ruou"][4:])
        items.append({"menu_item_id": wine["id"], "name": wine["name"], "price": wine["price"], "quantity": group_size})
        # Appetizer
        app = random.choice(APPETIZER[:4])
        items.append({"menu_item_id": app["id"], "name": app["name"], "price": app["price"], "quantity": 1})
        # Dessert
        d = random.choice(DESSERT)
        items.append({"menu_item_id": d["id"], "name": d["name"], "price": d["price"], "quantity": group_size})

    # Deduplicate items (merge same items)
    merged = {}
    for item in items:
        key = item["menu_item_id"]
        if key in merged:
            merged[key]["quantity"] += item["quantity"]
        else:
            merged[key] = dict(item)
    items = list(merged.values())

    total = sum(i["price"] * i["quantity"] for i in items)

    return {
        "order_id": f"ORD-{order_id:04d}",
        "timestamp": gen_timestamp(day_offset, hour),
        "table_code": random.choice(TABLES),
        "group_size": group_size,
        "segment": segment,
        "items": items,
        "item_count": sum(i["quantity"] for i in items),
        "total_vnd": total,
        "payment_method": random.choices(PAYMENT_METHODS, weights=[0.4, 0.6])[0],
    }


orders = []
order_id = 1
# Generate across 30 days (Mon-Sat, skip Sunday)
for day in range(42):  # 6 weeks
    weekday = (BASE_DATE + timedelta(days=day)).weekday()
    if weekday == 6:  # Sunday
        continue
    # More orders on Saturday
    daily_count = random.randint(28, 38) if weekday == 5 else random.randint(22, 32)
    for _ in range(daily_count):
        orders.append(gen_order(order_id, day))
        order_id += 1
        if order_id > 1000:
            break
    if order_id > 1000:
        break

orders = orders[:1000]

output = {
    "version": "2026-07-14",
    "description": "Synthetic order data for data mining experiments. 1000 orders across 30 business days.",
    "generation": {
        "seed": 20260714,
        "method": "rule-based-synthetic",
        "patterns": [
            "spicy_food -> cold_drinks (p=0.70)",
            "hot_pot -> beer (p=0.83)",
            "morning_noodles -> coffee (p=0.58)",
            "appetizer -> main_course (p=0.92)",
            "heavy_main -> dessert (p=0.50)",
            "drinking_group -> beer (p=0.83)",
            "family -> dessert (p=0.55)",
            "gourmet -> wine_cocktail (p=0.60)",
        ],
        "segments": {"office": 0.35, "drinking": 0.22, "family": 0.28, "gourmet": 0.15},
    },
    "statistics": {
        "total_orders": len(orders),
        "total_revenue": sum(o["total_vnd"] for o in orders),
        "avg_order_value": round(sum(o["total_vnd"] for o in orders) / len(orders)),
        "avg_items_per_order": round(sum(o["item_count"] for o in orders) / len(orders), 1),
    },
    "orders": orders,
}

out_path = Path("ai/evaluation/datasets/synthetic_orders.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Generated {len(orders)} orders")
print(f"Total revenue: {output['statistics']['total_revenue']:,} VND")
print(f"Avg order value: {output['statistics']['avg_order_value']:,} VND")
print(f"Avg items/order: {output['statistics']['avg_items_per_order']}")
