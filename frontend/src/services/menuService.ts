import { createApiClient } from "@cmc/api-client";
import type { MenuItem } from "../types";
import { resolveMenuImage } from "../utils/menuImages";

export type CustomerMenuCategory = {
  categoryId: string;
  name: string;
};

export type CustomerMenuResponse = {
  categories: CustomerMenuCategory[];
  items: MenuItem[];
};

const api = createApiClient();

function mapBackendMenu(menu: CustomerMenuResponse): CustomerMenuResponse {
  return {
    categories: menu.categories,
    items: menu.items.map((item, index) => ({
      ...item,
      imageUrl: resolveMenuImage(item.name, item.imageUrl, index),
      tags: item.tags ?? [],
    })),
  };
}

/* ======================================================================
   Fallback menu data — used when backend API is offline
   ====================================================================== */
const FALLBACK_CATEGORIES: CustomerMenuCategory[] = [
  { categoryId: "c1", name: "Khai vị" },
  { categoryId: "c2", name: "Phở & Bún" },
  { categoryId: "c3", name: "Cơm Việt" },
  { categoryId: "c4", name: "Hải sản" },
  { categoryId: "c5", name: "Lẩu" },
  { categoryId: "c6", name: "Món gà" },
  { categoryId: "c7", name: "Đặc sản vùng miền" },
  { categoryId: "c8", name: "Món chay" },
  { categoryId: "c9", name: "Cà phê & Trà" },
  { categoryId: "c10", name: "Nước ép & Sinh tố" },
  { categoryId: "c11", name: "Tráng miệng" },
  { categoryId: "c12", name: "Trái cây tươi" },
  { categoryId: "c13", name: "Bia & Rượu" },
];

function fb(id: number, name: string, cat: string, price: number, desc: string): MenuItem {
  const padded = String(id).padStart(2, "0");
  const slug = name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return { id: `fb-${id}`, name, categoryName: cat, price, description: desc, imageUrl: `/menu-images/${padded}-${slug}.png`, isAvailable: true, tags: [] };
}

const FALLBACK_ITEMS: MenuItem[] = [
  // Khai vị
  fb(1, "Gỏi cuốn tôm thịt", "Khai vị", 65000, "Tôm tươi, thịt heo luộc, bún, rau thơm cuốn trong bánh tráng mỏng, chấm tương đậu phộng."),
  fb(2, "Nem rán Hà Nội", "Khai vị", 75000, "Nem giòn rụm nhân thịt, mộc nhĩ, miến, trứng — chiên vàng, chấm nước mắm chua ngọt."),
  fb(3, "Bánh xèo miền Tây", "Khai vị", 85000, "Vỏ giòn vàng ươm, nhân tôm thịt giá đỗ, cuốn rau sống chấm nước mắm."),
  fb(4, "Bánh cuốn Thanh Trì", "Khai vị", 55000, "Bánh cuốn mỏng mịn nhân thịt mộc nhĩ, ăn kèm chả quế và nước mắm."),
  fb(5, "Gỏi xoài tôm sú", "Khai vị", 85000, "Xoài xanh giòn trộn tôm sú tươi, đậu phộng rang, rau thơm, nước mắm chua ngọt."),
  fb(6, "Bánh mì pate Sài Gòn", "Khai vị", 35000, "Bánh mì giòn kẹp pate, chả lụa, dưa leo, đồ chua và rau mùi tươi."),
  fb(7, "Súp măng cua", "Khai vị", 65000, "Súp nóng hổi với thịt cua, măng tươi, trứng cút và nấm hương thơm lừng."),
  // Phở & Bún
  fb(8, "Phở bò tái nạm", "Phở & Bún", 75000, "Nước dùng hầm xương 12 tiếng, thịt bò tái mềm, nạm giòn, hành lá tươi."),
  fb(9, "Phở gà ta", "Phở & Bún", 70000, "Phở gà ta nước trong, thịt gà dai ngọt, hành phi thơm phức."),
  fb(10, "Bún bò Huế", "Phở & Bún", 80000, "Nước lèo đậm đà sả ớt, thịt bò giò heo, chả cua Huế chính gốc."),
  fb(11, "Bún chả Hà Nội", "Phở & Bún", 75000, "Chả viên và chả miếng nướng than hoa, bún tươi, nước mắm chua ngọt."),
  fb(12, "Bún riêu cua đồng", "Phở & Bún", 70000, "Nước dùng cua đồng cà chua, riêu cua béo ngậy, đậu hũ, rau muống."),
  fb(13, "Bún mắm miền Tây", "Phở & Bún", 85000, "Nước lèo mắm cá linh đậm đà, tôm, mực, thịt quay, rau sống miền Tây."),
  fb(14, "Bún đậu mắm tôm", "Phở & Bún", 95000, "Bún lá, đậu hũ chiên giòn, chả cốm, nem chua, mắm tôm Gia Truyền."),
  // Cơm Việt
  fb(15, "Cơm tấm sườn bì chả", "Cơm Việt", 65000, "Sườn nướng mật ong, bì heo giòn dai, chả trứng hấp mềm — Sài Gòn chính gốc."),
  fb(16, "Cơm gà Hội An", "Cơm Việt", 70000, "Cơm nghệ vàng ươm, gà xé phay, rau sống, nước mắm gừng đặc trưng."),
  fb(17, "Cơm sườn nướng", "Cơm Việt", 60000, "Sườn heo ướp ngũ vị nướng than hoa, cơm trắng, đồ chua, nước mắm."),
  fb(18, "Cơm cá kho tộ", "Cơm Việt", 65000, "Cá basa kho tộ đất với nước màu dừa, tiêu, hành, ớt, cơm nóng."),
  fb(19, "Cơm chiên Sài Gòn", "Cơm Việt", 55000, "Cơm chiên tỏi với lạp xưởng, tôm, trứng, đậu que, cà rốt."),
  fb(20, "Cơm hến Huế", "Cơm Việt", 55000, "Cơm nguội trộn hến xào, rau thơm, đậu phộng, mắm ruốc Huế."),
  fb(21, "Cơm bò lúc lắc", "Cơm Việt", 95000, "Bò Úc lúc lắc áp chảo bơ tỏi, cơm trắng, salad rau xanh."),
  // Hải sản
  fb(22, "Tôm hùm nướng mỡ hành", "Hải sản", 890000, "Tôm hùm tươi nướng mỡ hành phi vàng thơm phức, ăn kèm cơm chiên."),
  fb(23, "Cá lóc nướng trui", "Hải sản", 195000, "Cá lóc nướng rơm kiểu miền Tây, cuốn bánh tráng rau sống chấm mắm nêm."),
  fb(24, "Tôm rang muối Tây Ninh", "Hải sản", 185000, "Tôm sú rang muối ớt giòn rụm, thơm lừng tỏi phi và lá chanh."),
  fb(25, "Cua rang me", "Hải sản", 380000, "Cua biển rang sốt me chua ngọt đậm đà, ăn kèm bánh mì nóng."),
  fb(26, "Mực xào sa tế", "Hải sản", 135000, "Mực tươi xào sa tế ớt cay nồng, hành tây, ớt chuông, rau muống."),
  fb(27, "Nghêu hấp sả", "Hải sản", 95000, "Nghêu tươi hấp sả ớt, nước dùng thơm ngọt tự nhiên."),
  fb(28, "Ốc hương rang bơ tỏi", "Hải sản", 165000, "Ốc hương rang bơ tỏi phi vàng, thơm nức, giòn ngọt."),
  // Lẩu
  fb(29, "Lẩu chua cá lăng", "Lẩu", 320000, "Cá lăng tươi nấu lẩu chua me, dọc mùng, bạc hà, rau sống."),
  fb(30, "Lẩu bò nhúng giấm", "Lẩu", 350000, "Bò Úc thái mỏng nhúng nước lẩu giấm nuôi, ăn kèm bún và rau."),
  fb(31, "Lẩu nấm chay", "Lẩu", 250000, "Nước dùng nấm hương, đông cô, kim châm, nấm đùi gà, rau củ tươi."),
  fb(32, "Lẩu gà lá é Đà Lạt", "Lẩu", 280000, "Gà ta thả vườn nấu lẩu lá é Đà Lạt thơm đặc trưng cao nguyên."),
  fb(33, "Lẩu hải sản chua cay", "Lẩu", 450000, "Tôm, mực, nghêu nấu Tom Yum chua cay đậm đà kiểu Thái-Việt."),
  fb(34, "Lẩu dê thuốc bắc", "Lẩu", 380000, "Thịt dê non hầm thuốc bắc bổ dưỡng, ăn kèm mì và rau thơm."),
  fb(35, "Lẩu mắm miền Tây", "Lẩu", 320000, "Lẩu mắm cá linh chính gốc miền Tây, rau đồng, bông điên điển."),
  // Món gà
  fb(36, "Gà nướng mật ong", "Món gà", 185000, "Gà ta nướng mật ong vàng ươm, da giòn thịt mềm thấm vị."),
  fb(37, "Gà hấp lá chanh", "Món gà", 280000, "Gà ta hấp lá chanh thơm, chấm muối tiêu chanh đặc biệt."),
  fb(38, "Cánh gà chiên nước mắm", "Món gà", 95000, "Cánh gà chiên giòn rim nước mắm tỏi ớt caramel hoá."),
  fb(39, "Gà xào sả ớt", "Món gà", 95000, "Gà ta xào sả ớt cay nồng, hành tây, ớt chuông."),
  fb(40, "Gà nướng muối ớt xanh", "Món gà", 195000, "Gà nướng muối ớt xanh Nha Trang giòn da, đậm vị."),
  fb(41, "Gà tiềm thuốc bắc", "Món gà", 250000, "Gà ta tiềm thuốc bắc bổ dưỡng, nước dùng thanh ngọt."),
  fb(42, "Gà rô ti kiểu Việt", "Món gà", 320000, "Gà rô ti vàng ruộm kiểu Việt, ăn kèm khoai tây và salad."),
  // Đặc sản vùng miền
  fb(43, "Mì Quảng tôm thịt", "Đặc sản vùng miền", 70000, "Mì Quảng sợi vàng, tôm thịt, đậu phộng, bánh tráng nướng."),
  fb(44, "Cao lầu Hội An", "Đặc sản vùng miền", 80000, "Cao lầu sợi dai đặc trưng, thịt xá xíu, rau sống Hội An."),
  fb(45, "Bê thui Cầu Mống", "Đặc sản vùng miền", 350000, "Bê thui da giòn thịt mềm, cuốn bánh tráng rau sống."),
  fb(46, "Hủ tiếu Nam Vang", "Đặc sản vùng miền", 65000, "Hủ tiếu nước trong, tôm thịt gan, giá đỗ, hẹ tươi."),
  fb(47, "Bánh tráng cuốn thịt heo", "Đặc sản vùng miền", 85000, "Thịt heo luộc cuốn bánh tráng, rau sống, chấm mắm nêm."),
  fb(48, "Cháo lòng Sài Gòn", "Đặc sản vùng miền", 45000, "Cháo nóng hổi với lòng heo tươi, giá đỗ, hành phi, quẩy giòn."),
  fb(49, "Xôi gà Hà Nội", "Đặc sản vùng miền", 50000, "Xôi nếp dẻo thơm, gà xé phay, hành phi, mỡ hành."),
  // Món chay
  fb(50, "Phở chay nấm đông cô", "Món chay", 60000, "Phở chay nước dùng nấm đông cô, đậu hũ, nấm tươi, rau thơm."),
  fb(51, "Cơm chiên chay ngũ sắc", "Món chay", 50000, "Cơm chiên với nấm, đậu hũ, cà rốt, đậu que, bắp ngọt."),
  fb(52, "Gỏi cuốn chay", "Món chay", 45000, "Gỏi cuốn nhân đậu hũ, bún, rau thơm, bơ, chấm tương đậu."),
  fb(53, "Canh khổ qua nhồi nấm", "Món chay", 55000, "Khổ qua nhồi nấm đông cô, nấu canh thanh mát giải nhiệt."),
  fb(54, "Đậu hũ sốt cà chua", "Món chay", 45000, "Đậu hũ chiên giòn sốt cà chua tươi, hành lá, rau mùi."),
  fb(55, "Mì Quảng chay", "Món chay", 55000, "Mì Quảng chay nước dùng nấm, đậu hũ, rau sống, đậu phộng."),
  fb(56, "Bún chay Huế", "Món chay", 55000, "Bún Huế chay nước dùng sả ớt, đậu hũ, nấm, rau sống."),
  // Cà phê & Trà
  fb(57, "Cà phê sữa đá", "Cà phê & Trà", 35000, "Cà phê phin truyền thống pha sữa đặc, đá viên mát lạnh."),
  fb(58, "Cà phê trứng Hà Nội", "Cà phê & Trà", 45000, "Cà phê đen đậm phủ kem trứng béo ngậy kiểu Hà Nội."),
  fb(59, "Bạc xỉu Sài Gòn", "Cà phê & Trà", 35000, "Sữa đặc nhiều, cà phê ít — thức uống nhẹ nhàng kiểu Sài Gòn."),
  fb(60, "Trà đào cam sả", "Cà phê & Trà", 45000, "Trà pha đào tươi, cam vàng, sả thơm, đá viên mát lạnh."),
  fb(61, "Trà sen Tây Hồ", "Cà phê & Trà", 55000, "Trà ướp sen Tây Hồ thơm thanh, pha ấm truyền thống."),
  fb(62, "Trà sữa trân châu", "Cà phê & Trà", 45000, "Trà sữa đậm đà với trân châu đen dai giòn tự làm."),
  fb(63, "Cà phê dừa", "Cà phê & Trà", 45000, "Cà phê phin pha cốt dừa béo ngậy, đá xay mát lạnh."),
  // Nước ép & Sinh tố
  fb(64, "Nước ép cam tươi", "Nước ép & Sinh tố", 40000, "Cam tươi ép nguyên chất, không đường, giàu vitamin C."),
  fb(65, "Sinh tố bơ Đắk Lắk", "Nước ép & Sinh tố", 50000, "Bơ 034 Đắk Lắk xay nhuyễn với sữa đặc và đá viên."),
  fb(66, "Nước ép dưa hấu", "Nước ép & Sinh tố", 35000, "Dưa hấu đỏ ép tươi mát lạnh, giải nhiệt mùa hè."),
  fb(67, "Sinh tố xoài Hòa Lộc", "Nước ép & Sinh tố", 45000, "Xoài cát Hòa Lộc xay nhuyễn với sữa tươi và đá."),
  fb(68, "Nước rau má", "Nước ép & Sinh tố", 30000, "Rau má tươi xay nhuyễn, thanh mát giải nhiệt."),
  fb(69, "Sinh tố dâu tây Đà Lạt", "Nước ép & Sinh tố", 50000, "Dâu tây Đà Lạt xay sữa tươi, ngọt dịu tự nhiên."),
  fb(70, "Nước mía Sài Gòn", "Nước ép & Sinh tố", 25000, "Mía tươi ép cùng quất, đá lạnh — đặc sản đường phố Sài Gòn."),
  // Tráng miệng
  fb(71, "Chè khúc bạch", "Tráng miệng", 45000, "Chè khúc bạch mát lạnh, thạch hạnh nhân, vải thiều, nước cốt dừa."),
  fb(72, "Bánh flan caramel", "Tráng miệng", 30000, "Bánh flan mềm mịn với lớp caramel đắng nhẹ."),
  fb(73, "Chè bưởi", "Tráng miệng", 35000, "Chè bưởi cùi trắng, đậu xanh, nước cốt dừa béo ngậy."),
  fb(74, "Sương sa hạt lựu", "Tráng miệng", 35000, "Sương sa mát lạnh, hạt lựu giòn sần sật, nước cốt dừa."),
  fb(75, "Chè trôi nước", "Tráng miệng", 35000, "Viên chè nếp dẻo nhân đậu xanh, nước gừng ngọt ấm."),
  fb(76, "Bánh chuối nướng", "Tráng miệng", 30000, "Bánh chuối nướng vàng ruộm, nước cốt dừa béo, mè rang."),
  fb(77, "Xôi xoài", "Tráng miệng", 45000, "Xôi nếp dẻo thơm, xoài chín ngọt, nước cốt dừa béo ngậy."),
  // Trái cây tươi
  fb(78, "Đĩa trái cây theo mùa", "Trái cây tươi", 75000, "Tổng hợp trái cây tươi theo mùa, bày đĩa đẹp mắt."),
  fb(79, "Xoài cát Hòa Lộc", "Trái cây tươi", 65000, "Xoài cát Hòa Lộc chín vàng, ngọt lịm, thơm đặc trưng."),
  fb(80, "Sầu riêng Ri6", "Trái cây tươi", 120000, "Sầu riêng Ri6 cơm vàng dày, béo ngậy, ít xơ."),
  fb(81, "Dưa hấu lạnh", "Trái cây tươi", 35000, "Dưa hấu đỏ mát lạnh, cắt miếng sẵn, giải khát."),
  fb(82, "Bưởi da xanh Bến Tre", "Trái cây tươi", 55000, "Bưởi da xanh ruột đỏ, ngọt thanh, không đắng."),
  fb(83, "Thanh long Bình Thuận", "Trái cây tươi", 45000, "Thanh long ruột đỏ Bình Thuận tươi mát, giàu dinh dưỡng."),
  fb(84, "Đu đủ chín mật ong", "Trái cây tươi", 40000, "Đu đủ chín vàng ngọt mật, cắt miếng rưới mật ong."),
  // Bia & Rượu
  fb(85, "Bia Sài Gòn Special", "Bia & Rượu", 20000, "Bia Sài Gòn Special lon 330ml, vị đậm đà truyền thống."),
  fb(86, "Bia Hà Nội", "Bia & Rượu", 18000, "Bia Hà Nội lon 330ml, vị nhẹ thanh mát."),
  fb(87, "Bia Tiger Crystal", "Bia & Rượu", 22000, "Bia Tiger Crystal lon 330ml, vị thanh nhẹ."),
  fb(88, "Bia hơi Hà Nội", "Bia & Rượu", 12000, "Bia hơi Hà Nội tươi mát, cốc 330ml."),
  fb(89, "Rượu nếp cẩm", "Bia & Rượu", 35000, "Rượu nếp cẩm truyền thống, ngọt dịu, thơm nồng."),
  fb(90, "Rượu mơ Hà Nội", "Bia & Rượu", 40000, "Rượu mơ Hà Nội chua ngọt thanh, uống lạnh."),
  fb(91, "Cocktail chanh đào mật ong", "Bia & Rượu", 65000, "Cocktail chanh đào mật ong tươi mát, thơm ngọt tự nhiên."),
];

const FALLBACK_MENU: CustomerMenuResponse = {
  categories: FALLBACK_CATEGORIES,
  items: FALLBACK_ITEMS,
};

export async function fetchCustomerMenu(): Promise<CustomerMenuResponse> {
  try {
    return mapBackendMenu((await api.menu.get()) as CustomerMenuResponse);
  } catch {
    console.warn("[menuService] API offline — using fallback menu data");
    return FALLBACK_MENU;
  }
}
