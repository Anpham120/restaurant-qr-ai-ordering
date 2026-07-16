#!/usr/bin/env node
/**
 * seed-menu.mjs — Vietnamese Restaurant Menu Dataset v3
 * 13 danh mục × 7 món = 91 món Việt Nam
 * Hệ thống 12 nhóm tag chuẩn hóa (~50 tags) cho AI training
 *
 * TAG SYSTEM:
 * 1. Mức cay:      khong cay | cay nhe | cay vua | cay dam
 * 2. Nguyên liệu:  bo | heo | ga | ca | tom | muc | cua | dau hu | nam | rau
 * 3. Chế biến:     nuong | chien | hap | xao | kho | luoc | rang | tiem | nau | cuon
 * 4. Vùng miền:    mien Bac | mien Trung | mien Nam | Ha Noi | Hue | Sai Gon | Da Nang | mien Tay | Tay Nguyen
 * 5. Dịp/Bữa:     sang | trua | toi | an khuya | tiec | hen ho | sinh nhat | nhau | hang ngay
 * 6. Đối tượng:    tre em | nguoi gia | gia dinh | nhom ban | tiep khach
 * 7. Chế độ ăn:    chay | vegan | healthy | it calo | giau protein | it dau mo | khong MSG
 * 8. Hương vị:     dam da | thanh nhe | beo | chua | ngot | man | thom khoi
 * 9. Dị ứng:       co hai san | co dau phong | co trung | co sua | co gluten
 * 10. Giá:         binh dan | tam trung | cao cap | premium
 * 11. Phục vụ:     ca nhan | share | 2-3 nguoi | 3-5 nguoi | dat truoc | mang di
 * 12. Mùa:         mua nong | mua lanh | quanh nam | giai nhiet
 *
 * Usage: node scripts/seed-menu.mjs
 */

const API = process.env.API_BASE ?? "http://localhost:5084/api";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL ?? "admin@restaurant.local";
const ADMIN_PASS = process.env.ADMIN_PASS ?? "Admin@1234";

async function login() {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASS }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  return (await res.json()).accessToken;
}

async function api(token, method, path, body) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${method} ${path} → ${res.status}: ${txt.slice(0, 150)}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

const CATEGORIES = [
  { name: "Khai vị", displayOrder: 1 },
  { name: "Phở & Bún", displayOrder: 2 },
  { name: "Cơm Việt", displayOrder: 3 },
  { name: "Hải sản", displayOrder: 4 },
  { name: "Lẩu", displayOrder: 5 },
  { name: "Món gà", displayOrder: 6 },
  { name: "Đặc sản vùng miền", displayOrder: 7 },
  { name: "Món chay", displayOrder: 8 },
  { name: "Cà phê & Trà", displayOrder: 9 },
  { name: "Nước ép & Sinh tố", displayOrder: 10 },
  { name: "Tráng miệng", displayOrder: 11 },
  { name: "Trái cây tươi", displayOrder: 12 },
  { name: "Bia & Rượu", displayOrder: 13 },
];

/* ================================================================
   91 MÓN — mỗi món 10-15 tags từ 12 nhóm chuẩn
   ================================================================ */
const ITEMS = [
  // ══════════════ 1. KHAI VỊ (7) ══════════════
  {
    cat: "Khai vị", name: "Gỏi cuốn tôm thịt",
    desc: "Cuốn tươi mát gồm tôm hấp, thịt heo luộc, bún, rau thơm (húng quế, tía tô) và lá xà lách cuốn trong bánh tráng mỏng. Chấm kèm tương đậu phộng sánh mịn. Món ăn nhẹ, ít dầu mỡ, không cay. Phù hợp người ăn kiêng, trẻ em. Đặc sản miền Nam Việt Nam.",
    price: 65000, img: "/menu-images/01-goi-cuon-tom-thit.png",
    tags: ["khong cay", "tom", "heo", "cuon", "mien Nam", "trua", "hang ngay", "tre em", "gia dinh", "healthy", "it calo", "it dau mo", "thanh nhe", "co hai san", "co dau phong", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Khai vị", name: "Nem rán Hà Nội",
    desc: "Nem giòn rụm nhân tôm, thịt heo xay, miến, mộc nhĩ, cà rốt bào sợi, cuốn trong bánh đa nem và chiên vàng giòn. Ăn kèm bún tươi, rau sống và nước mắm chua ngọt. Món khai vị cổ điển miền Bắc. Không cay. Phù hợp nhóm 2-4 người.",
    price: 75000, img: "/menu-images/02-nem-ran-ha-noi.png",
    tags: ["khong cay", "tom", "heo", "chien", "mien Bac", "Ha Noi", "trua", "toi", "tiec", "tre em", "gia dinh", "nhom ban", "dam da", "co hai san", "co gluten", "binh dan", "share", "quanh nam"],
  },
  {
    cat: "Khai vị", name: "Bánh xèo miền Tây",
    desc: "Bánh xèo giòn vàng từ bột gạo pha nghệ, nhân tôm sú, thịt heo, giá đỗ, nấm mèo. Cuốn cùng rau sống trong bánh tráng, chấm nước mắm chua ngọt. Đặc sản miền Tây. Không cay. Phù hợp gia đình, trẻ em thích lắm.",
    price: 85000, img: "/menu-images/03-banh-xeo-mien-tay.png",
    tags: ["khong cay", "tom", "heo", "chien", "mien Tay", "mien Nam", "trua", "toi", "tre em", "gia dinh", "ngot", "co hai san", "tam trung", "share", "2-3 nguoi", "quanh nam"],
  },
  {
    cat: "Khai vị", name: "Bánh cuốn Thanh Trì",
    desc: "Bánh cuốn nóng tráng mỏng nhân thịt heo xay, mộc nhĩ, hành khô. Rắc hành phi giòn, ăn kèm chả quế và nước mắm chua ngọt. Đặc sản Hà Nội. Không cay. Phù hợp bữa sáng hoặc khai vị nhẹ.",
    price: 55000, img: "/menu-images/04-banh-cuon-thanh-tri.png",
    tags: ["khong cay", "heo", "hap", "mien Bac", "Ha Noi", "sang", "hang ngay", "tre em", "nguoi gia", "it dau mo", "thanh nhe", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Khai vị", name: "Gỏi xoài tôm sú",
    desc: "Xoài xanh thái sợi giòn trộn cùng tôm sú hấp, rau thơm, hành phi, đậu phộng rang giã dập. Nước trộn mắm chanh đường ớt. Gỏi đặc trưng miền Nam. Cay nhẹ. Phù hợp mùa nóng, ăn kèm cơm.",
    price: 85000, img: "/menu-images/05-goi-xoai-tom-su.png",
    tags: ["cay nhe", "tom", "cuon", "mien Nam", "trua", "toi", "nhom ban", "healthy", "it calo", "chua", "co hai san", "co dau phong", "tam trung", "share", "mua nong", "giai nhiet"],
  },
  {
    cat: "Khai vị", name: "Bánh mì pate Sài Gòn",
    desc: "Ổ bánh mì giòn nóng kẹp pate gan, chả lụa, jambon, dưa leo, đồ chua, rau mùi và ớt tươi. Món ăn đường phố Sài Gòn nổi tiếng thế giới. Cay nhẹ (ớt tùy chọn). Phù hợp ăn nhanh, mang đi.",
    price: 35000, img: "/menu-images/06-banh-mi-pate-sai-gon.png",
    tags: ["cay nhe", "heo", "nuong", "mien Nam", "Sai Gon", "sang", "trua", "an khuya", "hang ngay", "tre em", "dam da", "co gluten", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Khai vị", name: "Súp măng cua",
    desc: "Súp nóng hổi với thịt cua biển, măng tây, trứng cút, nấm đông cô, bắp non. Nêm gia vị nhẹ, sánh mịn. Không cay, vị ngọt tự nhiên từ cua. Phù hợp mọi lứa tuổi, trẻ em và người lớn tuổi rất thích.",
    price: 65000, img: "/menu-images/07-sup-mang-cua.png",
    tags: ["khong cay", "cua", "nam", "nau", "mien Nam", "toi", "hang ngay", "tre em", "nguoi gia", "gia dinh", "it dau mo", "thanh nhe", "beo", "co hai san", "co trung", "tam trung", "ca nhan", "mua lanh"],
  },

  // ══════════════ 2. PHỞ & BÚN (7) ══════════════
  {
    cat: "Phở & Bún", name: "Phở bò tái nạm",
    desc: "Phở Hà Nội chính gốc với nước dùng xương bò ninh 12 tiếng cùng quế, hồi, thảo quả, gừng nướng. Bò tái và nạm mềm. Bánh phở tươi dai. Ăn kèm giá, chanh, ớt, tương đen. Không cay. Món quốc hồn quốc túy Việt Nam.",
    price: 75000, img: "/menu-images/08-pho-bo-tai-nam.png",
    tags: ["khong cay", "bo", "nau", "mien Bac", "Ha Noi", "sang", "trua", "hang ngay", "tre em", "nguoi gia", "gia dinh", "giau protein", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Phở & Bún", name: "Phở gà ta",
    desc: "Nước dùng trong vắt từ gà ta thả vườn, vị ngọt tự nhiên. Thịt gà xé sợi mềm, da giòn. Bánh phở tươi, hành phi giòn. Phở gà nhẹ bụng, phù hợp buổi sáng hoặc khi mệt. Không cay. Phù hợp trẻ em và người lớn tuổi.",
    price: 70000, img: "/menu-images/09-pho-ga-ta.png",
    tags: ["khong cay", "ga", "nau", "mien Bac", "Ha Noi", "sang", "hang ngay", "tre em", "nguoi gia", "gia dinh", "it dau mo", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Phở & Bún", name: "Bún bò Huế",
    desc: "Đặc sản Huế với nước dùng ninh xương heo và bò, sả, mắm ruốc, ớt sa tế cay nồng. Bún sợi to, thịt bò bắp, giò heo, chả cua Huế. Ăn kèm rau muống chẻ, giá, bắp chuối. Cay đậm đặc trưng. Không phù hợp trẻ nhỏ.",
    price: 80000, img: "/menu-images/10-bun-bo-hue.png",
    tags: ["cay dam", "bo", "heo", "nau", "mien Trung", "Hue", "sang", "trua", "hang ngay", "nhom ban", "giau protein", "dam da", "man", "co hai san", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Phở & Bún", name: "Bún chả Hà Nội",
    desc: "Chả thịt heo nướng than hoa gồm chả miếng và chả băm viên. Ăn kèm bún tươi, rau sống và nước chấm chua ngọt có đu đủ xanh. Từng được Tổng thống Obama thưởng thức. Không cay. Đặc sản Hà Nội.",
    price: 75000, img: "/menu-images/11-bun-cha-ha-noi.png",
    tags: ["khong cay", "heo", "nuong", "mien Bac", "Ha Noi", "trua", "hang ngay", "tre em", "gia dinh", "nhom ban", "tiep khach", "giau protein", "thom khoi", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Phở & Bún", name: "Bún riêu cua đồng",
    desc: "Nước dùng chua thanh từ cà chua, me, riêu cua đồng đánh bông. Bún sợi nhỏ, đậu hũ chiên, ốc bươu, huyết heo. Ăn kèm rau muống, giá, bắp chuối, mắm tôm tùy chọn. Không cay. Đặc trưng miền Bắc.",
    price: 70000, img: "/menu-images/12-bun-rieu-cua-dong.png",
    tags: ["khong cay", "cua", "heo", "nau", "mien Bac", "sang", "trua", "hang ngay", "tre em", "nguoi gia", "chua", "thanh nhe", "co hai san", "binh dan", "ca nhan", "mua nong"],
  },
  {
    cat: "Phở & Bún", name: "Bún mắm miền Tây",
    desc: "Nước dùng mắm cá linh đậm đà đặc trưng sông nước miền Tây. Bún sợi to, tôm sú, mực, cá lóc phi lê, heo quay giòn da. Rau đồng: bông bí, rau nhút, bắp chuối. Cay nhẹ. Phù hợp người yêu ẩm thực Nam Bộ.",
    price: 85000, img: "/menu-images/13-bun-mam-mien-tay.png",
    tags: ["cay nhe", "ca", "tom", "muc", "heo", "nau", "mien Tay", "mien Nam", "trua", "toi", "nhom ban", "dam da", "man", "co hai san", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Phở & Bún", name: "Bún đậu mắm tôm",
    desc: "Set bún đậu gồm đậu hũ chiên giòn, bún lá, chả cốm, nem chua rán, dồi sụn, thịt luộc. Chấm mắm tôm pha chanh đường ớt sủi bọt. Đặc sản Hà Nội. Cay vừa. Phù hợp nhóm bạn, nhậu.",
    price: 95000, img: "/menu-images/14-bun-dau-mam-tom.png",
    tags: ["cay vua", "heo", "dau hu", "chien", "luoc", "mien Bac", "Ha Noi", "trua", "toi", "nhau", "nhom ban", "dam da", "man", "co gluten", "tam trung", "share", "2-3 nguoi", "quanh nam"],
  },

  // ══════════════ 3. CƠM VIỆT (7) ══════════════
  {
    cat: "Cơm Việt", name: "Cơm tấm sườn bì chả",
    desc: "Cơm tấm Sài Gòn chuẩn vị với sườn heo nướng mật ong, bì heo trộn thính, chả trứng hấp. Kèm mỡ hành, đồ chua, dưa leo và nước mắm pha. Bữa trưa phổ biến nhất Sài Gòn. Không cay. Phần ăn đầy đặn.",
    price: 65000, img: "/menu-images/15-com-tam-suon-bi-cha.png",
    tags: ["khong cay", "heo", "nuong", "hap", "mien Nam", "Sai Gon", "sang", "trua", "hang ngay", "tre em", "gia dinh", "giau protein", "dam da", "ngot", "co trung", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Cơm Việt", name: "Cơm gà Hội An",
    desc: "Cơm nghệ vàng ươm nấu với nước luộc gà, gà ta xé sợi mềm, da giòn. Rau sống, hành phi, nước mắm gừng. Kèm canh gà nóng. Không cay. Đặc sản miền Trung, phù hợp mọi lứa tuổi.",
    price: 70000, img: "/menu-images/16-com-ga-hoi-an.png",
    tags: ["khong cay", "ga", "luoc", "mien Trung", "Da Nang", "sang", "trua", "hang ngay", "tre em", "nguoi gia", "gia dinh", "giau protein", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Cơm Việt", name: "Cơm sườn nướng",
    desc: "Sườn heo ướp sả ớt, mật ong, nước mắm nướng than hoa. Cơm trắng nóng, đồ chua, dưa leo, mỡ hành, trứng ốp la. Nước mắm pha chua ngọt. Vị thơm khói. Cay nhẹ. Phù hợp bữa trưa/tối hàng ngày.",
    price: 60000, img: "/menu-images/17-com-suon-nuong.png",
    tags: ["cay nhe", "heo", "nuong", "mien Nam", "Sai Gon", "trua", "toi", "hang ngay", "gia dinh", "giau protein", "dam da", "thom khoi", "ngot", "co trung", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Cơm Việt", name: "Cơm cá kho tộ",
    desc: "Cá basa phi lê kho tộ trong nồi đất với nước mắm, đường thốt nốt, tiêu, hành, tỏi. Nước kho sánh đậm, cá mềm thấm vị mặn-ngọt. Kèm cơm trắng nóng, canh rau cải xanh. Cay nhẹ. Món cơm trưa truyền thống miền Nam.",
    price: 65000, img: "/menu-images/18-com-ca-kho-to.png",
    tags: ["cay nhe", "ca", "kho", "mien Nam", "trua", "toi", "hang ngay", "gia dinh", "nguoi gia", "giau protein", "dam da", "man", "ngot", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Cơm Việt", name: "Cơm chiên Sài Gòn",
    desc: "Cơm chiên lửa lớn với tôm, lạp xưởng, trứng gà, đậu Hà Lan, cà rốt, hành lá. Hạt cơm tơi rời, vàng đều, thơm mỡ tỏi. Không cay. Phù hợp cả trẻ em và người lớn.",
    price: 55000, img: "/menu-images/19-com-chien-sai-gon.png",
    tags: ["khong cay", "tom", "heo", "chien", "mien Nam", "Sai Gon", "trua", "toi", "hang ngay", "tre em", "gia dinh", "dam da", "co hai san", "co trung", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Cơm Việt", name: "Cơm hến Huế",
    desc: "Đặc sản Huế với cơm nguội trộn hến xào sả ớt, rau sống thái nhuyễn, đậu phộng rang, tóp mỡ giòn, mắm ruốc Huế. Trộn đều, vị mặn-cay-chua-béo. Cay vừa. Trải nghiệm ẩm thực cung đình Huế.",
    price: 55000, img: "/menu-images/20-com-hen-hue.png",
    tags: ["cay vua", "rau", "xao", "mien Trung", "Hue", "sang", "trua", "hang ngay", "nhom ban", "dam da", "man", "chua", "beo", "co hai san", "co dau phong", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Cơm Việt", name: "Cơm bò lúc lắc",
    desc: "Bò Úc thái hạt lựu ướp tiêu đen, tỏi, nước tương, xào lửa lớn nhanh tay. Kèm cơm trắng nóng, cà chua, xà lách, hành tây, đồ chua. Không cay. Phần ăn giàu protein. Phù hợp bữa trưa/tối.",
    price: 95000, img: "/menu-images/21-com-bo-luc-lac.png",
    tags: ["khong cay", "bo", "xao", "mien Nam", "Sai Gon", "trua", "toi", "hang ngay", "tiep khach", "giau protein", "dam da", "tam trung", "ca nhan", "quanh nam"],
  },

  // ══════════════ 4. HẢI SẢN (7) ══════════════
  {
    cat: "Hải sản", name: "Tôm hùm nướng mỡ hành",
    desc: "Tôm hùm bông tươi sống (~500g/con) nướng mỡ hành thơm lừng, rắc hành phi và đậu phộng. Thịt tôm ngọt, chắc, thấm mỡ hành béo. Kèm muối tiêu chanh. Không cay. Đặt trước 30 phút. Phù hợp tiệc đặc biệt.",
    price: 890000, img: "/menu-images/22-tom-hum-nuong-mo-hanh.png",
    tags: ["khong cay", "tom", "nuong", "mien Trung", "toi", "tiec", "hen ho", "sinh nhat", "tiep khach", "giau protein", "beo", "ngot", "co hai san", "co dau phong", "premium", "2-3 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Hải sản", name: "Cá lóc nướng trui",
    desc: "Cá lóc đồng nướng nguyên con trong rơm rạ kiểu miền Tây. Thịt cá trắng ngọt, thơm khói rơm. Gỡ thịt cuốn bánh tráng với rau sống, chấm mắm nêm. Cay nhẹ. Đặc sản miền Tây. Đặt trước 25 phút.",
    price: 195000, img: "/menu-images/23-ca-loc-nuong-trui.png",
    tags: ["cay nhe", "ca", "nuong", "mien Tay", "mien Nam", "toi", "nhau", "nhom ban", "giau protein", "it dau mo", "thom khoi", "ngot", "tam trung", "share", "2-3 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Hải sản", name: "Tôm rang muối Tây Ninh",
    desc: "Tôm sú tươi rang muối ớt Tây Ninh, tỏi phi giòn, ớt xanh, lá curry. Vỏ giòn rụm, thịt tôm ngọt. Cay nhẹ. Món nhậu phổ biến. Phù hợp ăn kèm cơm hoặc nhậu bia. 6-8 con/phần.",
    price: 185000, img: "/menu-images/24-tom-rang-muoi-tay-ninh.png",
    tags: ["cay nhe", "tom", "rang", "mien Nam", "toi", "nhau", "nhom ban", "giau protein", "dam da", "man", "co hai san", "tam trung", "share", "quanh nam"],
  },
  {
    cat: "Hải sản", name: "Cua rang me",
    desc: "Cua gạch (~600g) rang me chua ngọt. Thịt cua chắc ngọt, sốt me sánh bám đều. Ăn kèm bánh mì nóng chấm sốt. Hải sản tươi sống. Không cay. Đặt trước 20 phút. Phù hợp nhóm 2-4 người, tiệc nhóm.",
    price: 380000, img: "/menu-images/25-cua-rang-me.png",
    tags: ["khong cay", "cua", "rang", "mien Nam", "Sai Gon", "toi", "tiec", "nhom ban", "tiep khach", "giau protein", "chua", "ngot", "co hai san", "cao cap", "share", "2-3 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Hải sản", name: "Mực xào sa tế",
    desc: "Mực ống tươi cắt khoanh, xào lửa lớn với sốt sa tế, ớt chuông, hành tây, gừng. Mực giòn sần sật, vị cay thơm nồng. Ăn kèm cơm trắng. Cay đậm. Có thể giảm cay theo yêu cầu.",
    price: 135000, img: "/menu-images/26-muc-xao-sa-te.png",
    tags: ["cay dam", "muc", "xao", "mien Nam", "toi", "nhau", "nhom ban", "giau protein", "dam da", "co hai san", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Hải sản", name: "Nghêu hấp sả",
    desc: "Nghêu trắng tươi sống hấp với sả cây, lá chanh, gừng, ớt. Nước hấp ngọt thanh thơm sả. Ăn nóng, chấm muối tiêu chanh. Cay nhẹ. Món hải sản nhẹ, ít calo, giàu kẽm. Phù hợp nhậu bia.",
    price: 95000, img: "/menu-images/27-ngheu-hap-sa.png",
    tags: ["cay nhe", "rau", "hap", "mien Nam", "toi", "nhau", "nhom ban", "healthy", "it calo", "thanh nhe", "co hai san", "tam trung", "share", "quanh nam"],
  },
  {
    cat: "Hải sản", name: "Ốc hương rang bơ tỏi",
    desc: "Ốc hương tươi sống rang bơ tỏi phi vàng, rắc hành lá. Giòn sần sật, vị ngọt tự nhiên, thơm bơ tỏi. Phục vụ nóng trên đĩa gang. Không cay. Món nhậu hải sản yêu thích. Đặt trước 15 phút.",
    price: 165000, img: "/menu-images/28-oc-huong-rang-bo-toi.png",
    tags: ["khong cay", "rau", "rang", "mien Trung", "toi", "nhau", "nhom ban", "giau protein", "beo", "ngot", "co hai san", "co sua", "tam trung", "share", "dat truoc", "quanh nam"],
  },

  // ══════════════ 5. LẨU (7) ══════════════
  {
    cat: "Lẩu", name: "Lẩu chua cá lăng",
    desc: "Nước lẩu chua từ me, cà chua, thơm (dứa), giá hẹ. Cá lăng cắt khúc (~800g), thịt chắc ngọt. Rau muống, bắp chuối, bún tươi. Đặc sản miền Bắc. Không cay. Phục vụ 2-3 người. Phù hợp gia đình, trẻ em.",
    price: 320000, img: "/menu-images/29-lau-chua-ca-lang.png",
    tags: ["khong cay", "ca", "nau", "mien Bac", "toi", "tre em", "gia dinh", "giau protein", "chua", "thanh nhe", "cao cap", "share", "2-3 nguoi", "mua lanh"],
  },
  {
    cat: "Lẩu", name: "Lẩu bò nhúng giấm",
    desc: "Nước lẩu giấm nuôi với dấm bỗng, sả, thơm. Bò thượng hạng thái lát mỏng nhúng chín tái. Kèm rau muống, bắp chuối, bún tươi. Đặc sản miền Nam. Không cay. Phục vụ 2-4 người.",
    price: 350000, img: "/menu-images/30-lau-bo-nhung-giam.png",
    tags: ["khong cay", "bo", "nau", "mien Nam", "toi", "gia dinh", "tiep khach", "giau protein", "chua", "thanh nhe", "cao cap", "share", "2-3 nguoi", "quanh nam"],
  },
  {
    cat: "Lẩu", name: "Lẩu nấm chay",
    desc: "Nước dùng chay từ nấm đông cô, nấm hương, củ cải, bắp ngô. Gồm 5 loại nấm, đậu hũ, rau cải, bắp non. 100% thực vật, không MSG. Không cay. Phù hợp người ăn chay, detox. Phục vụ 2-3 người.",
    price: 250000, img: "/menu-images/31-lau-nam-chay.png",
    tags: ["khong cay", "nam", "dau hu", "rau", "nau", "toi", "gia dinh", "chay", "vegan", "healthy", "it calo", "khong MSG", "thanh nhe", "tam trung", "share", "2-3 nguoi", "quanh nam"],
  },
  {
    cat: "Lẩu", name: "Lẩu gà lá é Đà Lạt",
    desc: "Gà ta thả vườn (~1.2kg), nước dùng ninh xương gà với lá é Đà Lạt thơm đặc trưng. Kèm rau rừng, nấm, bún tươi. Nước dùng ngọt thanh. Không cay. Đặc sản Tây Nguyên. Phục vụ 3-4 người.",
    price: 280000, img: "/menu-images/32-lau-ga-la-e-da-lat.png",
    tags: ["khong cay", "ga", "nam", "nau", "Tay Nguyen", "toi", "tre em", "gia dinh", "giau protein", "thanh nhe", "ngot", "tam trung", "share", "3-5 nguoi", "dat truoc", "mua lanh"],
  },
  {
    cat: "Lẩu", name: "Lẩu hải sản chua cay",
    desc: "Nước lẩu chua cay với me, cà chua, sả, ớt sa tế. Gồm tôm sú, mực, cá phi lê, sò điệp, nghêu. Hải sản tươi sống. Cay đậm. Phục vụ 3-5 người. Phù hợp tiệc nhóm. Đặt trước 30 phút.",
    price: 450000, img: "/menu-images/33-lau-hai-san-chua-cay.png",
    tags: ["cay dam", "tom", "muc", "ca", "nau", "mien Nam", "toi", "tiec", "nhom ban", "giau protein", "chua", "dam da", "co hai san", "cao cap", "share", "3-5 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Lẩu", name: "Lẩu dê thuốc bắc",
    desc: "Thịt dê tươi (~800g) nấu trong nước dùng thuốc bắc gồm kỷ tử, táo đỏ, đương quy, hoàng kỳ. Vị thơm nồng, bổ dưỡng. Kèm rau cải, nấm, bún. Cay nhẹ. Phù hợp mùa lạnh. Phục vụ 3-4 người.",
    price: 380000, img: "/menu-images/34-lau-de-thuoc-bac.png",
    tags: ["cay nhe", "bo", "nam", "tiem", "nau", "toi", "nhom ban", "giau protein", "dam da", "beo", "cao cap", "share", "3-5 nguoi", "dat truoc", "mua lanh"],
  },
  {
    cat: "Lẩu", name: "Lẩu mắm miền Tây",
    desc: "Lẩu mắm đặc sản miền Tây với mắm cá linh lên men. Gồm cá lóc, tôm, mực, heo quay giòn da. Rau đồng: bông bí, bông điên điển, rau nhút. Cay vừa. Hương mắm đặc trưng. Phục vụ 3-4 người.",
    price: 320000, img: "/menu-images/35-lau-mam-mien-tay.png",
    tags: ["cay vua", "ca", "tom", "heo", "nau", "mien Tay", "mien Nam", "toi", "nhau", "nhom ban", "dam da", "man", "co hai san", "cao cap", "share", "3-5 nguoi", "quanh nam"],
  },

  // ══════════════ 6. MÓN GÀ (7) ══════════════
  {
    cat: "Món gà", name: "Gà nướng mật ong",
    desc: "Đùi gà ta ướp mật ong, tỏi, gừng, ngũ vị hương qua đêm, nướng lò cho da vàng giòn, thịt mềm ngọt. Kèm muối tiêu chanh và rau sống. Không cay. Phù hợp bữa tối gia đình. Có thể chọn nguyên con.",
    price: 185000, img: "/menu-images/36-ga-nuong-mat-ong.png",
    tags: ["khong cay", "ga", "nuong", "toi", "hang ngay", "tre em", "gia dinh", "giau protein", "ngot", "thom khoi", "tam trung", "ca nhan", "share", "quanh nam"],
  },
  {
    cat: "Món gà", name: "Gà hấp lá chanh",
    desc: "Gà ta nguyên con (~1.2kg) hấp với lá chanh tươi, sả, gừng. Thịt mềm, da co giòn, thơm lá chanh đặc trưng. Chấm muối tiêu chanh. Không cay, không dầu mỡ. Phù hợp gia đình 3-4 người. Đặt trước 25 phút.",
    price: 280000, img: "/menu-images/37-ga-hap-la-chanh.png",
    tags: ["khong cay", "ga", "hap", "toi", "tiec", "gia dinh", "nguoi gia", "tiep khach", "giau protein", "it dau mo", "healthy", "thanh nhe", "cao cap", "share", "3-5 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Món gà", name: "Cánh gà chiên nước mắm",
    desc: "Cánh gà chiên giòn rồi rim sốt nước mắm-tỏi-ớt-đường caramel. Vị mặn ngọt đậm đà, thơm nước mắm Phú Quốc. 6 cánh/phần. Cay nhẹ. Món nhậu yêu thích. Phù hợp nhậu bia hoặc ăn kèm cơm.",
    price: 95000, img: "/menu-images/38-canh-ga-chien-nuoc-mam.png",
    tags: ["cay nhe", "ga", "chien", "mien Nam", "toi", "nhau", "hang ngay", "nhom ban", "giau protein", "dam da", "man", "ngot", "tam trung", "ca nhan", "share", "quanh nam"],
  },
  {
    cat: "Món gà", name: "Gà xào sả ớt",
    desc: "Gà ta chặt miếng xào lửa lớn với sả băm, ớt hiểm, hành tím, lá chanh. Thịt gà săn, thấm gia vị sả. Ăn kèm cơm trắng nóng. Cay vừa. Món cơm nhà đơn giản mà ngon. Phù hợp bữa trưa/tối.",
    price: 95000, img: "/menu-images/39-ga-xao-sa-ot.png",
    tags: ["cay vua", "ga", "xao", "trua", "toi", "hang ngay", "gia dinh", "giau protein", "dam da", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Món gà", name: "Gà nướng muối ớt xanh",
    desc: "Nửa con gà ta (~600g) ướp muối hạt, ớt xanh giã, tỏi, sả rồi nướng than hoa. Da giòn rụm, thịt ngọt mọng nước. Chấm muối ớt xanh. Cay vừa. Đặc sản quán nướng Việt Nam. Đặt trước 20 phút.",
    price: 195000, img: "/menu-images/40-ga-nuong-muoi-ot-xanh.png",
    tags: ["cay vua", "ga", "nuong", "toi", "nhau", "nhom ban", "giau protein", "dam da", "man", "thom khoi", "tam trung", "share", "2-3 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Món gà", name: "Gà tiềm thuốc bắc",
    desc: "Gà ác nguyên con tiềm (hầm 3 tiếng) với đương quy, kỷ tử, táo đỏ, hoàng kỳ, nấm đông cô. Nước dùng ngọt thanh, bổ dưỡng. Thịt mềm rục. Không cay. Phù hợp bồi bổ sức khỏe. Đặt trước 3 tiếng.",
    price: 250000, img: "/menu-images/41-ga-tiem-thuoc-bac.png",
    tags: ["khong cay", "ga", "nam", "tiem", "toi", "nguoi gia", "healthy", "thanh nhe", "beo", "ngot", "cao cap", "ca nhan", "dat truoc", "mua lanh"],
  },
  {
    cat: "Món gà", name: "Gà rô ti kiểu Việt",
    desc: "Gà ta nguyên con ướp ngũ vị hương, mật ong, nước tương, tỏi, gừng rồi quay giòn. Da vàng óng, giòn rụm, thịt mềm thấm gia vị. Chặt miếng, kèm muối tiêu chanh. Không cay. Phù hợp tiệc gia đình, sinh nhật.",
    price: 320000, img: "/menu-images/42-ga-ro-ti-kieu-viet.png",
    tags: ["khong cay", "ga", "nuong", "toi", "tiec", "sinh nhat", "gia dinh", "tiep khach", "giau protein", "dam da", "ngot", "thom khoi", "cao cap", "share", "3-5 nguoi", "dat truoc", "quanh nam"],
  },

  // ══════════════ 7. ĐẶC SẢN VÙNG MIỀN (7) ══════════════
  {
    cat: "Đặc sản vùng miền", name: "Mì Quảng tôm thịt",
    desc: "Mì Quảng sợi vàng nghệ, nước dùng đậm đà từ tôm và xương heo, đậu phộng rang, bánh tráng nướng, trứng cút, rau sống. Đặc sản Quảng Nam-Đà Nẵng. Cay nhẹ. Vị đậm, ít nước, khác biệt hoàn toàn với phở.",
    price: 70000, img: "/menu-images/43-mi-quang-tom-thit.png",
    tags: ["cay nhe", "tom", "heo", "nau", "mien Trung", "Da Nang", "sang", "trua", "hang ngay", "nhom ban", "giau protein", "dam da", "co hai san", "co dau phong", "co trung", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Đặc sản vùng miền", name: "Cao lầu Hội An",
    desc: "Sợi mì cao lầu dày, dai, nhuộm nước tro đặc trưng Hội An. Thịt heo xá xíu, rau sống, giá, bánh tráng nướng giòn. Nước sốt đậm đà ít nước. Món ăn chỉ có ở Hội An. Không cay. Trải nghiệm ẩm thực độc đáo.",
    price: 80000, img: "/menu-images/44-cao-lau-hoi-an.png",
    tags: ["khong cay", "heo", "nau", "mien Trung", "Da Nang", "trua", "hang ngay", "tiep khach", "dam da", "co gluten", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Đặc sản vùng miền", name: "Bê thui Cầu Mống",
    desc: "Bê non thui rơm kiểu Cầu Mống (Quảng Nam). Thịt bê mềm, hồng đào, thơm khói rơm. Cuốn bánh tráng với rau sống, chuối chát, khế, chấm mắm nêm cay. Cay nhẹ. Đặc sản miền Trung. Phù hợp nhóm 4-6 người.",
    price: 350000, img: "/menu-images/45-be-thui-cau-mong.png",
    tags: ["cay nhe", "bo", "nuong", "mien Trung", "toi", "tiec", "nhau", "nhom ban", "giau protein", "thom khoi", "dam da", "cao cap", "share", "3-5 nguoi", "dat truoc", "quanh nam"],
  },
  {
    cat: "Đặc sản vùng miền", name: "Hủ tiếu Nam Vang",
    desc: "Hủ tiếu sợi dai trong nước dùng xương heo ninh trong, tôm, thịt heo, gan, tim. Rắc hành phi, tỏi phi, cần tây, hẹ. Đặc sản Sài Gòn gốc Hoa. Không cay. Phù hợp bữa sáng. Chọn khô hoặc nước.",
    price: 65000, img: "/menu-images/46-hu-tieu-nam-vang.png",
    tags: ["khong cay", "heo", "tom", "nau", "mien Nam", "Sai Gon", "sang", "an khuya", "hang ngay", "tre em", "nguoi gia", "thanh nhe", "co hai san", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Đặc sản vùng miền", name: "Bánh tráng cuốn thịt heo",
    desc: "Đặc sản Đà Nẵng: thịt heo ba chỉ luộc thái mỏng, cuốn bánh tráng với rau sống, chuối chát, dưa leo, chấm mắm nêm tỏi ớt. Cay nhẹ. Thanh mát, không dầu mỡ. Phù hợp mùa nóng.",
    price: 85000, img: "/menu-images/47-banh-trang-cuon-thit-heo.png",
    tags: ["cay nhe", "heo", "luoc", "cuon", "mien Trung", "Da Nang", "toi", "nhom ban", "healthy", "it dau mo", "it calo", "thanh nhe", "tam trung", "share", "2-3 nguoi", "mua nong"],
  },
  {
    cat: "Đặc sản vùng miền", name: "Cháo lòng Sài Gòn",
    desc: "Cháo trắng nấu nhừ với huyết heo, lòng heo luộc chín. Rắc hành phi, tiêu, ngò rí. Ăn kèm giò cháo quẩy giòn. Không cay. Đặc sản Sài Gòn bình dân. Phù hợp bữa sáng, ăn khuya.",
    price: 45000, img: "/menu-images/48-chao-long-sai-gon.png",
    tags: ["khong cay", "heo", "nau", "mien Nam", "Sai Gon", "sang", "an khuya", "hang ngay", "tre em", "nguoi gia", "thanh nhe", "beo", "co gluten", "binh dan", "ca nhan", "mua lanh"],
  },
  {
    cat: "Đặc sản vùng miền", name: "Xôi gà Hà Nội",
    desc: "Xôi nếp cái hoa vàng dẻo thơm, phủ gà ta xé sợi, hành phi giòn, mỡ hành. Kèm ruốc chà bông và nước mắm gừng. Đặc sản ăn sáng Hà Nội. Không cay. Phần ăn no lâu, giàu năng lượng. Mang đi tiện lợi.",
    price: 50000, img: "/menu-images/49-xoi-ga-ha-noi.png",
    tags: ["khong cay", "ga", "hap", "mien Bac", "Ha Noi", "sang", "hang ngay", "tre em", "gia dinh", "giau protein", "beo", "ngot", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },

  // ══════════════ 8. MÓN CHAY (7) ══════════════
  {
    cat: "Món chay", name: "Phở chay nấm đông cô",
    desc: "Nước dùng chay ninh từ củ cải trắng, bắp ngô, nấm đông cô, gừng. Phở tươi, nấm, đậu hũ chiên, rau cải, hành lá. 100% thực vật, không MSG. Không cay. Phù hợp ngày rằm, mùng một, người ăn chay, vegan.",
    price: 60000, img: "/menu-images/50-pho-chay-nam-dong-co.png",
    tags: ["khong cay", "nam", "dau hu", "rau", "nau", "sang", "trua", "hang ngay", "nguoi gia", "chay", "vegan", "healthy", "it calo", "khong MSG", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Món chay", name: "Cơm chiên chay ngũ sắc",
    desc: "Cơm chiên với đậu hũ, nấm, bắp ngô, đậu Hà Lan, cà rốt, ớt chuông. Không trứng, không hành tỏi (chay thanh tịnh). Hạt cơm tơi, nhiều màu sắc. Không cay. Phù hợp vegan. Giàu chất xơ.",
    price: 50000, img: "/menu-images/51-com-chien-chay-ngu-sac.png",
    tags: ["khong cay", "dau hu", "nam", "rau", "chien", "trua", "toi", "hang ngay", "tre em", "chay", "vegan", "healthy", "khong MSG", "thanh nhe", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Món chay", name: "Gỏi cuốn chay",
    desc: "Cuốn tươi với đậu hũ chiên, xà lách, bún, rau thơm, dưa leo, cà rốt. Chấm sốt đậu phộng chay. Không thịt, không hải sản. Nhẹ, mát, giàu chất xơ. Không cay. Phù hợp khai vị chay.",
    price: 45000, img: "/menu-images/52-goi-cuon-chay.png",
    tags: ["khong cay", "dau hu", "rau", "cuon", "trua", "hang ngay", "tre em", "nguoi gia", "chay", "vegan", "healthy", "it calo", "it dau mo", "thanh nhe", "co dau phong", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Món chay", name: "Canh khổ qua nhồi nấm",
    desc: "Khổ qua nhồi nhân nấm hương, mộc nhĩ, bún tàu, đậu hũ non, nấu canh chay. Vị đắng nhẹ thanh nhiệt, giải độc. Không cay. Phù hợp mùa nóng, người cần detox. Món canh chay truyền thống.",
    price: 55000, img: "/menu-images/53-canh-kho-qua-nhoi-nam.png",
    tags: ["khong cay", "nam", "dau hu", "rau", "nau", "trua", "toi", "nguoi gia", "chay", "vegan", "healthy", "it calo", "khong MSG", "thanh nhe", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Món chay", name: "Đậu hũ sốt cà chua",
    desc: "Đậu hũ non chiên vàng, rim sốt cà chua tươi với hành tây, ớt chuông, nấm mèo. Vị chua ngọt nhẹ nhàng. Không cay. Ăn kèm cơm. Phù hợp mọi lứa tuổi kể cả trẻ em. Giàu protein thực vật.",
    price: 45000, img: "/menu-images/54-dau-hu-sot-ca-chua.png",
    tags: ["khong cay", "dau hu", "rau", "chien", "trua", "toi", "hang ngay", "tre em", "nguoi gia", "chay", "vegan", "giau protein", "chua", "ngot", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Món chay", name: "Mì Quảng chay",
    desc: "Mì Quảng sợi vàng nghệ, nước dùng chay đậm đà với đậu phộng rang, đậu hũ chiên, nấm, rau sống. Bánh tráng nướng bẻ vụn. Đặc sản Quảng Nam phiên bản chay. Cay nhẹ.",
    price: 55000, img: "/menu-images/55-mi-quang-chay.png",
    tags: ["cay nhe", "dau hu", "nam", "rau", "nau", "mien Trung", "trua", "hang ngay", "chay", "vegan", "dam da", "co dau phong", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Món chay", name: "Bún chay Huế",
    desc: "Bún nước dùng chay sa tế sả, ớt, nghệ. Đậu hũ chiên, nấm đông cô, cà chua, rau muống. Phiên bản chay của Bún bò Huế. Cay vừa. Phù hợp người ăn chay thích vị đậm đà. Có thể giảm cay.",
    price: 55000, img: "/menu-images/56-bun-chay-hue.png",
    tags: ["cay vua", "dau hu", "nam", "rau", "nau", "mien Trung", "Hue", "trua", "hang ngay", "chay", "vegan", "dam da", "man", "binh dan", "ca nhan", "quanh nam"],
  },

  // ══════════════ 9. CÀ PHÊ & TRÀ (7) ══════════════
  {
    cat: "Cà phê & Trà", name: "Cà phê sữa đá",
    desc: "Cà phê Robusta Buôn Ma Thuột pha phin truyền thống. Hòa cùng sữa đặc và đá viên. Vị đắng đậm, béo ngọt, thơm nồng. Thức uống biểu tượng Việt Nam. Caffeine cao, phù hợp buổi sáng.",
    price: 35000, img: "/menu-images/57-ca-phe-sua-da.png",
    tags: ["khong cay", "sang", "trua", "hang ngay", "nhom ban", "dam da", "ngot", "beo", "co sua", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Cà phê & Trà", name: "Cà phê trứng Hà Nội",
    desc: "Đặc sản Hà Nội: lòng đỏ trứng đánh bông với sữa đặc tạo lớp kem trứng mịn phủ trên cà phê đen đậm. Nóng hoặc đá. Vị béo ngậy, ngọt nhẹ. Trải nghiệm độc đáo chỉ có ở Việt Nam.",
    price: 45000, img: "/menu-images/58-ca-phe-trung-ha-noi.png",
    tags: ["khong cay", "mien Bac", "Ha Noi", "sang", "hang ngay", "tiep khach", "beo", "ngot", "co trung", "co sua", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Cà phê & Trà", name: "Bạc xỉu Sài Gòn",
    desc: "Phiên bản cà phê sữa Sài Gòn — nhiều sữa, ít cà phê. Vị ngọt béo, thơm nhẹ. Caffeine thấp. Phù hợp người mới uống cà phê, phụ nữ hoặc ai thích vị nhẹ nhàng.",
    price: 35000, img: "/menu-images/59-bac-xiu-sai-gon.png",
    tags: ["khong cay", "mien Nam", "Sai Gon", "sang", "hang ngay", "tre em", "thanh nhe", "ngot", "beo", "co sua", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Cà phê & Trà", name: "Trà đào cam sả",
    desc: "Trà đen hãm đậm, đào ngâm mật ong, cam vàng vắt tươi, sả cây đập dập, đá viên. Vị ngọt thanh, chua nhẹ, thơm sả. Thức uống giải khát phổ biến nhất Việt Nam hiện nay. Phù hợp mọi lứa tuổi.",
    price: 45000, img: "/menu-images/60-tra-dao-cam-sa.png",
    tags: ["khong cay", "sang", "trua", "toi", "hang ngay", "tre em", "nguoi gia", "gia dinh", "healthy", "thanh nhe", "ngot", "chua", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Cà phê & Trà", name: "Trà sen Tây Hồ",
    desc: "Trà sen Tây Hồ (Hà Nội) — trà xanh ướp hương sen tự nhiên từ hoa sen Hồ Tây. Hãm nóng trong ấm sứ. Vị trà thơm, hậu ngọt, thanh mát. Đặc sản trà quý Việt Nam. Phù hợp thưởng trà chiều.",
    price: 55000, img: "/menu-images/61-tra-sen-tay-ho.png",
    tags: ["khong cay", "mien Bac", "Ha Noi", "toi", "tiep khach", "nguoi gia", "healthy", "it calo", "thanh nhe", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Cà phê & Trà", name: "Trà sữa trân châu",
    desc: "Trà đen pha sữa tươi, trân châu đường đen handmade dẻo mềm. Chọn mức đường (0%-100%) và mức đá. Thức uống yêu thích giới trẻ Việt Nam. Lưu ý: nhiều đường nếu chọn full.",
    price: 45000, img: "/menu-images/62-tra-sua-tran-chau.png",
    tags: ["khong cay", "trua", "toi", "hang ngay", "tre em", "nhom ban", "ngot", "beo", "co sua", "binh dan", "ca nhan", "mang di", "quanh nam"],
  },
  {
    cat: "Cà phê & Trà", name: "Cà phê dừa",
    desc: "Cà phê phin đậm pha cùng nước cốt dừa béo ngậy, đá viên. Vị đắng cà phê hòa quyện béo thơm dừa. Đặc sản cà phê kiểu mới Việt Nam. Caffeine trung bình. Phù hợp người thích vị lạ.",
    price: 45000, img: "/menu-images/63-ca-phe-dua.png",
    tags: ["khong cay", "sang", "trua", "hang ngay", "nhom ban", "beo", "ngot", "co sua", "binh dan", "ca nhan", "quanh nam"],
  },

  // ══════════════ 10. NƯỚC ÉP & SINH TỐ (7) ══════════════
  {
    cat: "Nước ép & Sinh tố", name: "Nước ép cam tươi",
    desc: "Cam Sài Gòn vắt tươi 100%, không thêm đường, không chất bảo quản. Giàu vitamin C. Vị chua ngọt tự nhiên, tươi mát. Phù hợp mọi lứa tuổi, đặc biệt trẻ em. Uống ngay sau khi pha.",
    price: 40000, img: "/menu-images/64-nuoc-ep-cam-tuoi.png",
    tags: ["khong cay", "sang", "trua", "hang ngay", "tre em", "nguoi gia", "gia dinh", "healthy", "it calo", "chua", "ngot", "thanh nhe", "binh dan", "ca nhan", "quanh nam", "giai nhiet"],
  },
  {
    cat: "Nước ép & Sinh tố", name: "Sinh tố bơ Đắk Lắk",
    desc: "Bơ sáp Đắk Lắk chín mềm xay nhuyễn với sữa đặc, đá xay. Béo ngậy, thơm bơ. Giàu chất béo tốt, kali, vitamin E. Phù hợp trẻ em cần tăng cân, người tập gym. Không caffeine.",
    price: 50000, img: "/menu-images/65-sinh-to-bo-dak-lak.png",
    tags: ["khong cay", "Tay Nguyen", "sang", "trua", "hang ngay", "tre em", "healthy", "giau protein", "beo", "ngot", "co sua", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Nước ép & Sinh tố", name: "Nước ép dưa hấu",
    desc: "Dưa hấu đỏ xay nguyên chất, không đường. Vị ngọt tự nhiên, mát lạnh giải nhiệt. Giàu lycopene, vitamin A. Ít calo. Phù hợp người ăn kiêng, mùa hè. 100% trái cây.",
    price: 35000, img: "/menu-images/66-nuoc-ep-dua-hau.png",
    tags: ["khong cay", "trua", "toi", "hang ngay", "tre em", "nguoi gia", "healthy", "it calo", "ngot", "thanh nhe", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Nước ép & Sinh tố", name: "Sinh tố xoài Hòa Lộc",
    desc: "Xoài cát Hòa Lộc chín thơm xay với sữa tươi, đá xay, mật ong. Vị ngọt đậm, thơm xoài nhiệt đới. Giàu vitamin A, C. Phù hợp mọi lứa tuổi. Có phiên bản không sữa (vegan).",
    price: 45000, img: "/menu-images/67-sinh-to-xoai-hoa-loc.png",
    tags: ["khong cay", "mien Nam", "trua", "toi", "hang ngay", "tre em", "gia dinh", "healthy", "ngot", "co sua", "binh dan", "ca nhan", "mua nong"],
  },
  {
    cat: "Nước ép & Sinh tố", name: "Nước rau má",
    desc: "Rau má tươi xay nhuyễn với đường, đá viên. Vị thanh mát, hơi đắng nhẹ. Giải nhiệt, thanh lọc cơ thể, tốt cho da. Thức uống dân gian Việt Nam. Giàu vitamin K, C.",
    price: 30000, img: "/menu-images/68-nuoc-rau-ma.png",
    tags: ["khong cay", "rau", "mien Nam", "trua", "toi", "hang ngay", "nguoi gia", "healthy", "it calo", "thanh nhe", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Nước ép & Sinh tố", name: "Sinh tố dâu tây Đà Lạt",
    desc: "Dâu tây Đà Lạt tươi xay với sữa chua, mật ong, đá. Vị chua ngọt hài hòa, màu hồng đẹp. Giàu vitamin C, antioxidant. Phù hợp da đẹp, sức khỏe. Trẻ em rất thích.",
    price: 50000, img: "/menu-images/69-sinh-to-dau-tay-da-lat.png",
    tags: ["khong cay", "Tay Nguyen", "trua", "toi", "hang ngay", "tre em", "healthy", "it calo", "chua", "ngot", "co sua", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Nước ép & Sinh tố", name: "Nước mía Sài Gòn",
    desc: "Mía tươi ép tại chỗ, thêm tắc (quất) và đá viên. Vị ngọt mía tự nhiên, chua nhẹ, mát lạnh. Thức uống đường phố Sài Gòn. Giàu đường tự nhiên, năng lượng nhanh. Phù hợp mùa nóng.",
    price: 25000, img: "/menu-images/70-nuoc-mia-sai-gon.png",
    tags: ["khong cay", "mien Nam", "Sai Gon", "sang", "trua", "hang ngay", "tre em", "nguoi gia", "ngot", "thanh nhe", "binh dan", "ca nhan", "mang di", "mua nong", "giai nhiet"],
  },

  // ══════════════ 11. TRÁNG MIỆNG (7) ══════════════
  {
    cat: "Tráng miệng", name: "Chè khúc bạch",
    desc: "Khúc bạch mềm mịn, vải thiều, nhãn, hạnh nhân, nước siro đường phèn. Ăn lạnh. Không cay. Xuất xứ Hải Phòng. Phù hợp tráng miệng. Trẻ em yêu thích. Vị ngọt thanh mát.",
    price: 45000, img: "/menu-images/71-che-khuc-bach.png",
    tags: ["khong cay", "mien Bac", "toi", "hang ngay", "tre em", "gia dinh", "ngot", "thanh nhe", "co sua", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Tráng miệng", name: "Bánh flan caramel",
    desc: "Bánh flan mềm mịn từ trứng gà, sữa tươi, vanilla, phủ caramel đắng nhẹ. Dùng lạnh. Không cay. Món tráng miệng phổ biến nhất Việt Nam. Phù hợp mọi lứa tuổi.",
    price: 30000, img: "/menu-images/72-banh-flan-caramel.png",
    tags: ["khong cay", "toi", "hang ngay", "tre em", "nguoi gia", "gia dinh", "ngot", "beo", "co trung", "co sua", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Tráng miệng", name: "Chè bưởi",
    desc: "Cùi bưởi dẻo, nước cốt dừa béo, đậu xanh, bột báng. Ăn lạnh hoặc nóng. Không cay. Chè truyền thống miền Nam. Vị béo dừa, ngọt nhẹ. Phù hợp tráng miệng hoặc ăn vặt.",
    price: 35000, img: "/menu-images/73-che-buoi.png",
    tags: ["khong cay", "mien Nam", "toi", "hang ngay", "tre em", "nguoi gia", "ngot", "beo", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Tráng miệng", name: "Sương sa hạt lựu",
    desc: "Thạch rau câu sợi, hạt lựu bột năng lá dứa xanh-đỏ, nước cốt dừa, đá bào. Vị ngọt mát, dẻo dai. Không cay. Đặc sản miền Nam. Phù hợp mùa nóng, trẻ em và người lớn đều thích.",
    price: 35000, img: "/menu-images/74-suong-sa-hat-luu.png",
    tags: ["khong cay", "mien Nam", "toi", "hang ngay", "tre em", "gia dinh", "chay", "vegan", "ngot", "thanh nhe", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Tráng miệng", name: "Chè trôi nước",
    desc: "Viên bột nếp dẻo nhồi đậu xanh, nấu nước gừng đường phèn. Rắc mè rang, dừa nạo. Ăn nóng. Không cay. Chè truyền thống Tết Đoan ngọ. Vị gừng ấm bụng. Phù hợp mùa lạnh.",
    price: 35000, img: "/menu-images/75-che-troi-nuoc.png",
    tags: ["khong cay", "toi", "hang ngay", "tre em", "nguoi gia", "chay", "vegan", "ngot", "beo", "binh dan", "ca nhan", "mua lanh"],
  },
  {
    cat: "Tráng miệng", name: "Bánh chuối nướng",
    desc: "Chuối chín nấu với nước cốt dừa, bột mì, đường, bơ rồi nướng vàng. Rắc mè đen và dừa nạo. Vị ngọt béo, thơm chuối dừa. Không cay. Đặc sản miền Nam. Ăn nóng.",
    price: 30000, img: "/menu-images/76-banh-chuoi-nuong.png",
    tags: ["khong cay", "nuong", "mien Nam", "toi", "hang ngay", "tre em", "gia dinh", "ngot", "beo", "co sua", "co gluten", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Tráng miệng", name: "Xôi xoài",
    desc: "Xôi nếp dẻo nấu nước cốt dừa, xoài cát chín thái lát, rắc đậu xanh. Không cay. Tráng miệng kiểu Đông Nam Á phổ biến tại Việt Nam. Vị ngọt béo, thơm xoài dừa. Phù hợp mùa xoài.",
    price: 45000, img: "/menu-images/77-xoi-xoai.png",
    tags: ["khong cay", "mien Nam", "toi", "hang ngay", "tre em", "gia dinh", "chay", "vegan", "ngot", "beo", "binh dan", "ca nhan", "mua nong"],
  },

  // ══════════════ 12. TRÁI CÂY TƯƠI (7) ══════════════
  {
    cat: "Trái cây tươi", name: "Đĩa trái cây theo mùa",
    desc: "Đĩa trái cây tươi gồm các loại theo mùa: xoài, dưa hấu, thanh long, ổi, thơm. Gọt sẵn, cắt miếng. Kèm muối ớt, mắm chanh đường. Không cay. Tươi mát, giàu vitamin. Phù hợp chia sẻ nhóm.",
    price: 75000, img: "/menu-images/78-dia-trai-cay-theo-mua.png",
    tags: ["khong cay", "toi", "tiec", "tre em", "gia dinh", "nhom ban", "chay", "vegan", "healthy", "it calo", "ngot", "thanh nhe", "tam trung", "share", "2-3 nguoi", "quanh nam"],
  },
  {
    cat: "Trái cây tươi", name: "Xoài cát Hòa Lộc",
    desc: "Xoài cát Hòa Lộc (Tiền Giang) chín cây, thịt vàng óng, ngọt đậm không chua. Gọt sẵn, cắt miếng. Loại xoài ngon nhất Việt Nam. Giàu vitamin A, C. Theo mùa (tháng 4-7).",
    price: 65000, img: "/menu-images/79-xoai-cat-hoa-loc.png",
    tags: ["khong cay", "mien Nam", "toi", "tre em", "nguoi gia", "gia dinh", "chay", "vegan", "healthy", "it calo", "ngot", "binh dan", "ca nhan", "mua nong"],
  },
  {
    cat: "Trái cây tươi", name: "Sầu riêng Ri6",
    desc: "Sầu riêng Ri6 (Vĩnh Long) tách múi, thịt vàng kem, béo ngậy, thơm đặc trưng. Phục vụ trong hộp kín. Loại trái cây 'vua' Đông Nam Á. Giàu năng lượng, kali. Lưu ý: mùi mạnh. Có thể mang về.",
    price: 120000, img: "/menu-images/80-sau-rieng-ri6.png",
    tags: ["khong cay", "mien Nam", "toi", "nhom ban", "beo", "ngot", "tam trung", "ca nhan", "mang di", "mua nong"],
  },
  {
    cat: "Trái cây tươi", name: "Dưa hấu lạnh",
    desc: "Dưa hấu đỏ ngọt, ướp lạnh, cắt miếng. Giải nhiệt mùa nóng. Giàu lycopene, vitamin C. Ít calo (~30 cal/100g). Phù hợp người ăn kiêng, trẻ em. Dùng sau bữa ăn hoặc giữa buổi.",
    price: 35000, img: "/menu-images/81-dua-hau-lanh.png",
    tags: ["khong cay", "toi", "hang ngay", "tre em", "nguoi gia", "chay", "vegan", "healthy", "it calo", "ngot", "thanh nhe", "binh dan", "ca nhan", "mua nong", "giai nhiet"],
  },
  {
    cat: "Trái cây tươi", name: "Bưởi da xanh Bến Tre",
    desc: "Bưởi da xanh (Bến Tre) tách múi, tép bưởi hồng mọng nước, ngọt thanh không đắng. Giàu vitamin C, chất xơ, ít đường. Phù hợp người tiểu đường, ăn kiêng. Ăn kèm muối ớt.",
    price: 55000, img: "/menu-images/82-buoi-da-xanh-ben-tre.png",
    tags: ["khong cay", "mien Nam", "toi", "nguoi gia", "chay", "vegan", "healthy", "it calo", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Trái cây tươi", name: "Thanh long Bình Thuận",
    desc: "Thanh long ruột đỏ Bình Thuận, ngọt thanh, mát lạnh. Giàu vitamin C, chất xơ, antioxidant. Ít calo, tốt cho tiêu hóa. Phù hợp detox. Trái cây xuất khẩu chủ lực Việt Nam.",
    price: 45000, img: "/menu-images/83-thanh-long-binh-thuan.png",
    tags: ["khong cay", "mien Nam", "toi", "hang ngay", "nguoi gia", "chay", "vegan", "healthy", "it calo", "ngot", "thanh nhe", "binh dan", "ca nhan", "quanh nam", "giai nhiet"],
  },
  {
    cat: "Trái cây tươi", name: "Đu đủ chín mật ong",
    desc: "Đu đủ ruột vàng chín, gọt sẵn cắt miếng. Giàu enzyme papain hỗ trợ tiêu hóa, vitamin C, A. Rất phù hợp ăn sau bữa ăn nhiều thịt. Phù hợp mọi lứa tuổi, đặc biệt người già.",
    price: 40000, img: "/menu-images/84-du-du-chin-mat-ong.png",
    tags: ["khong cay", "toi", "hang ngay", "tre em", "nguoi gia", "chay", "vegan", "healthy", "it calo", "ngot", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },

  // ══════════════ 13. BIA & RƯỢU (7) ══════════════
  {
    cat: "Bia & Rượu", name: "Bia Sài Gòn Special",
    desc: "Bia Sài Gòn Special (Sabeco) lon 330ml, thương hiệu bia lâu đời nhất Việt Nam từ 1875. Vị bia lager nhẹ, malt thơm, hậu đắng vừa phải, nồng độ 4.9%. Uống lạnh 2-4°C. Phù hợp nhậu hải sản, lẩu, nướng. Phổ biến khắp miền Nam.",
    price: 20000, img: "/menu-images/85-bia-sai-gon-special.png",
    tags: ["khong cay", "mien Nam", "Sai Gon", "toi", "nhau", "nhom ban", "gia dinh", "dam da", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Bia & Rượu", name: "Bia Hà Nội",
    desc: "Bia Hà Nội (Habeco) lon 330ml, hương vị đặc trưng miền Bắc từ 1890. Bia lager truyền thống, vị đắng đậm hơn bia Sài Gòn, malt mạnh, nồng độ 4.5%. Uống lạnh. Phù hợp bún chả, phở, nem rán. Biểu tượng bia thủ đô.",
    price: 18000, img: "/menu-images/86-bia-ha-noi.png",
    tags: ["khong cay", "mien Bac", "Ha Noi", "toi", "nhau", "nhom ban", "dam da", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Bia & Rượu", name: "Bia Tiger Crystal",
    desc: "Bia Tiger Crystal lon 330ml, bia lager cao cấp, lọc lạnh ở 0°C cho vị trong trẻo, thanh nhẹ, dễ uống. Nồng độ 4.6%. Phổ biến tại Việt Nam. Phù hợp nhậu nhẹ, hải sản, nướng. Uống lạnh 0-4°C.",
    price: 22000, img: "/menu-images/87-bia-tiger-crystal.png",
    tags: ["khong cay", "toi", "nhau", "nhom ban", "hen ho", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Bia & Rượu", name: "Bia hơi Hà Nội",
    desc: "Bia hơi tươi Hà Nội phục vụ trong cốc vại (~400ml), bia không qua xử lý nhiệt nên giữ nguyên hương vị tươi mới. Nồng độ ~3%, nhẹ, dễ uống, bọt mịn. Đặc sản đường phố Hà Nội, uống tại chỗ. Phù hợp nhậu vỉa hè, bún chả.",
    price: 12000, img: "/menu-images/88-bia-hoi-ha-noi.png",
    tags: ["khong cay", "mien Bac", "Ha Noi", "toi", "an khuya", "nhau", "nhom ban", "thanh nhe", "binh dan", "ca nhan", "quanh nam"],
  },
  {
    cat: "Bia & Rượu", name: "Rượu nếp cẩm",
    desc: "Rượu nếp cẩm truyền thống ngâm từ gạo nếp cẩm lên men tự nhiên. Nồng độ ~12-15%, vị ngọt nhẹ, thơm nếp, màu tím đỏ đẹp. Phục vụ trong ly nhỏ 50ml. Rượu dân gian Việt Nam. Phù hợp tiệc, nhậu, tiếp khách. Uống vừa phải.",
    price: 35000, img: "/menu-images/89-ruou-nep-cam.png",
    tags: ["khong cay", "mien Bac", "toi", "tiec", "nhau", "tiep khach", "ngot", "dam da", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Bia & Rượu", name: "Rượu mơ Hà Nội",
    desc: "Rượu mơ ngâm đường phèn, quả mơ Hương Tích (Hà Nội). Nồng độ ~15-18%, vị chua ngọt thanh, thơm mơ tự nhiên, màu vàng hổ phách. Ly 50ml. Đặc sản Hà Nội. Phù hợp phụ nữ, tiếp khách. Uống sipping từng ngụm nhỏ.",
    price: 40000, img: "/menu-images/90-ruou-mo-ha-noi.png",
    tags: ["khong cay", "mien Bac", "Ha Noi", "toi", "tiec", "hen ho", "tiep khach", "chua", "ngot", "thanh nhe", "tam trung", "ca nhan", "quanh nam"],
  },
  {
    cat: "Bia & Rượu", name: "Cocktail chanh đào mật ong",
    desc: "Cocktail nhà hàng tự pha: rượu vodka Việt, chanh đào ngâm mật ong, soda, đá viên, lá bạc hà. Nồng độ ~8-10%, vị chua ngọt sảng khoái, thơm chanh đào. Ly 250ml. Phù hợp hen hò, tiệc. Có phiên bản không cồn (mocktail).",
    price: 65000, img: "/menu-images/91-cocktail-chanh-dao-mat-ong.png",
    tags: ["khong cay", "toi", "tiec", "hen ho", "sinh nhat", "nhom ban", "chua", "ngot", "thanh nhe", "tam trung", "ca nhan", "quanh nam"],
  },
];

/* ---- Main ---- */
async function main() {
  console.log("🔑 Đăng nhập admin...");
  const token = await login();
  console.log("✅ OK\n");

  // Create categories
  console.log(`📁 Tạo ${CATEGORIES.length} danh mục...`);
  const catMap = new Map();
  for (const cat of CATEGORIES) {
    try {
      const res = await api(token, "POST", "/admin/categories", { name: cat.name, displayOrder: cat.displayOrder, isActive: true });
      catMap.set(cat.name, res.categoryId);
      console.log(`  ✅ ${cat.name}`);
    } catch { /* fallback below */ }
  }
  if (catMap.size < CATEGORIES.length) {
    const menuData = await api(token, "GET", "/menu", null);
    for (const c of menuData.categories) if (!catMap.has(c.name)) catMap.set(c.name, c.categoryId);
  }

  // Create items
  console.log(`\n🍽️ Tạo ${ITEMS.length} món ăn (${CATEGORIES.length} danh mục)...`);
  let created = 0, skipped = 0;
  // Collect tag stats
  const allTags = new Set();

  for (const item of ITEMS) {
    const categoryId = catMap.get(item.cat);
    if (!categoryId) { skipped++; continue; }
    try {
      await api(token, "POST", "/admin/menu-items/", {
        categoryId, name: item.name, description: item.desc,
        price: item.price, imageUrl: item.img, isAvailable: true, tags: item.tags,
      });
      created++;
      item.tags.forEach(t => allTags.add(t));
      const spice = item.tags.find(t => ["khong cay","cay nhe","cay vua","cay dam"].includes(t)) ?? "?";
      console.log(`  ✅ [${item.cat}] ${item.name} (${item.tags.length} tags) — ${spice}`);
    } catch (err) {
      console.log(`  ⚠️ ${item.name}: ${err.message.slice(0, 80)}`);
      skipped++;
    }
  }

  // Stats
  const tagCounts = {};
  for (const item of ITEMS) for (const t of item.tags) tagCounts[t] = (tagCounts[t] || 0) + 1;
  const avgTags = (ITEMS.reduce((s, i) => s + i.tags.length, 0) / ITEMS.length).toFixed(1);

  console.log(`\n🎉 Hoàn tất! ${created}/${ITEMS.length} món.`);
  console.log(`\n📊 THỐNG KÊ TAG SYSTEM:`);
  console.log(`   🏷️ Tổng tags duy nhất: ${allTags.size}`);
  console.log(`   📝 Trung bình tags/món: ${avgTags}`);
  console.log(`\n   🌶️ Mức cay:`);
  console.log(`      khong cay: ${tagCounts["khong cay"]||0} | cay nhe: ${tagCounts["cay nhe"]||0} | cay vua: ${tagCounts["cay vua"]||0} | cay dam: ${tagCounts["cay dam"]||0}`);
  console.log(`   🥩 Nguyên liệu phổ biến:`);
  ["heo","ga","bo","ca","tom","muc","cua","dau hu","nam","rau"].forEach(t =>
    console.log(`      ${t}: ${tagCounts[t]||0} món`));
  console.log(`   👨‍🍳 Chế biến:`);
  ["nuong","chien","hap","xao","kho","luoc","nau","rang","tiem","cuon"].forEach(t =>
    console.log(`      ${t}: ${tagCounts[t]||0} món`));
  console.log(`   🗺️ Vùng miền:`);
  ["mien Bac","mien Trung","mien Nam","Ha Noi","Hue","Sai Gon","Da Nang","mien Tay","Tay Nguyen"].forEach(t =>
    console.log(`      ${t}: ${tagCounts[t]||0} món`));
  console.log(`   🎯 Đối tượng:`);
  ["tre em","nguoi gia","gia dinh","nhom ban","tiep khach"].forEach(t =>
    console.log(`      ${t}: ${tagCounts[t]||0} món`));
  console.log(`   🥗 Chế độ ăn:`);
  ["chay","vegan","healthy","it calo","giau protein","it dau mo","khong MSG"].forEach(t =>
    console.log(`      ${t}: ${tagCounts[t]||0} món`));
  console.log(`\n   🇻🇳 100% ẩm thực Việt Nam — Sẵn sàng huấn luyện AI!`);
}

main().catch(err => { console.error("❌", err.message); process.exit(1); });
