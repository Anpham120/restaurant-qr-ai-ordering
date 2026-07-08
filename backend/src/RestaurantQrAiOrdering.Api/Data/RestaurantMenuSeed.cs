using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Data;

/// <summary>
/// Single source of truth for the official 91-dish menu (13 categories).
/// Used by both the EF Core model seed (migrations) and the in-memory
/// chat data store so the AI assistant sees the same menu as customers.
/// Image files live in the customer web app under /menu-images.
/// </summary>
public static class RestaurantMenuSeed
{
    public static IReadOnlyList<Category> CreateCategories(DateTimeOffset seededAt)
    {
        return
        [
            Cat("cat_appetizer", "Khai vị", 10, seededAt),
            Cat("cat_noodle", "Phở & Bún", 20, seededAt),
            Cat("cat_main", "Cơm Việt", 30, seededAt),
            Cat("cat_seafood", "Hải sản", 40, seededAt),
            Cat("cat_hotpot", "Lẩu", 50, seededAt),
            Cat("cat_chicken", "Món gà", 60, seededAt),
            Cat("cat_regional", "Đặc sản vùng miền", 70, seededAt),
            Cat("cat_vegetarian", "Món chay", 80, seededAt),
            Cat("cat_drink", "Cà phê & Trà", 90, seededAt),
            Cat("cat_juice", "Nước ép & Sinh tố", 100, seededAt),
            Cat("cat_dessert", "Tráng miệng", 110, seededAt),
            Cat("cat_fruit", "Trái cây tươi", 120, seededAt),
            Cat("cat_alcohol", "Bia & Rượu", 130, seededAt)
        ];
    }

    public static IReadOnlyList<MenuItem> CreateMenuItems(DateTimeOffset seededAt)
    {
        return
        [
            // Khai vị
            Item(1, "cat_appetizer", "Gỏi cuốn tôm thịt", 65000, "Tôm tươi, thịt heo luộc, bún, rau thơm cuốn trong bánh tráng mỏng, chấm tương đậu phộng.", "goi-cuon-tom-thit", seededAt, ["pho bien", "signature"]),
            Item(2, "cat_appetizer", "Nem rán Hà Nội", 75000, "Nem giòn rụm nhân thịt, mộc nhĩ, miến, trứng — chiên vàng, chấm nước mắm chua ngọt.", "nem-ran-ha-noi", seededAt, ["chien", "Ha Noi"]),
            Item(3, "cat_appetizer", "Bánh xèo miền Tây", 85000, "Vỏ giòn vàng ươm, nhân tôm thịt giá đỗ, cuốn rau sống chấm nước mắm.", "banh-xeo-mien-tay", seededAt, ["mien Tay"]),
            Item(4, "cat_appetizer", "Bánh cuốn Thanh Trì", 55000, "Bánh cuốn mỏng mịn nhân thịt mộc nhĩ, ăn kèm chả quế và nước mắm.", "banh-cuon-thanh-tri", seededAt, ["Ha Noi", "sang"]),
            Item(5, "cat_appetizer", "Gỏi xoài tôm sú", 85000, "Xoài xanh giòn trộn tôm sú tươi, đậu phộng rang, rau thơm, nước mắm chua ngọt.", "goi-xoai-tom-su", seededAt, ["chua", "tom"]),
            Item(6, "cat_appetizer", "Bánh mì pate Sài Gòn", 35000, "Bánh mì giòn kẹp pate, chả lụa, dưa leo, đồ chua và rau mùi tươi.", "banh-mi-pate-sai-gon", seededAt, ["Sai Gon", "binh dan"]),
            Item(7, "cat_appetizer", "Súp măng cua", 65000, "Súp nóng hổi với thịt cua, măng tươi, trứng cút và nấm hương thơm lừng.", "sup-mang-cua", seededAt, ["cua", "nong"]),
            // Phở & Bún
            Item(8, "cat_noodle", "Phở bò tái nạm", 75000, "Nước dùng hầm xương 12 tiếng, thịt bò tái mềm, nạm giòn, hành lá tươi.", "pho-bo-tai-nam", seededAt, ["bo", "signature"]),
            Item(9, "cat_noodle", "Phở gà ta", 70000, "Phở gà ta nước trong, thịt gà dai ngọt, hành phi thơm phức.", "pho-ga-ta", seededAt, ["ga"]),
            Item(10, "cat_noodle", "Bún bò Huế", 80000, "Nước lèo đậm đà sả ớt, thịt bò giò heo, chả cua Huế chính gốc.", "bun-bo-hue", seededAt, ["cay vua", "Hue"]),
            Item(11, "cat_noodle", "Bún chả Hà Nội", 75000, "Chả viên và chả miếng nướng than hoa, bún tươi, nước mắm chua ngọt.", "bun-cha-ha-noi", seededAt, ["nuong", "Ha Noi"]),
            Item(12, "cat_noodle", "Bún riêu cua đồng", 70000, "Nước dùng cua đồng cà chua, riêu cua béo ngậy, đậu hũ, rau muống.", "bun-rieu-cua-dong", seededAt, ["cua"]),
            Item(13, "cat_noodle", "Bún mắm miền Tây", 85000, "Nước lèo mắm cá linh đậm đà, tôm, mực, thịt quay, rau sống miền Tây.", "bun-mam-mien-tay", seededAt, ["mien Tay", "dam da"]),
            Item(14, "cat_noodle", "Bún đậu mắm tôm", 95000, "Bún lá, đậu hũ chiên giòn, chả cốm, nem chua, mắm tôm Gia Truyền.", "bun-dau-mam-tom", seededAt, ["Ha Noi", "nhom ban"]),
            // Cơm Việt
            Item(15, "cat_main", "Cơm tấm sườn bì chả", 65000, "Sườn nướng mật ong, bì heo giòn dai, chả trứng hấp mềm — Sài Gòn chính gốc.", "com-tam-suon-bi-cha", seededAt, ["Sai Gon", "pho bien"]),
            Item(16, "cat_main", "Cơm gà Hội An", 70000, "Cơm nghệ vàng ươm, gà xé phay, rau sống, nước mắm gừng đặc trưng.", "com-ga-hoi-an", seededAt, ["ga", "Hoi An"]),
            Item(17, "cat_main", "Cơm sườn nướng", 60000, "Sườn heo ướp ngũ vị nướng than hoa, cơm trắng, đồ chua, nước mắm.", "com-suon-nuong", seededAt, ["nuong", "heo"]),
            Item(18, "cat_main", "Cơm cá kho tộ", 65000, "Cá basa kho tộ đất với nước màu dừa, tiêu, hành, ớt, cơm nóng.", "com-ca-kho-to", seededAt, ["ca", "kho"]),
            Item(19, "cat_main", "Cơm chiên Sài Gòn", 55000, "Cơm chiên tỏi với lạp xưởng, tôm, trứng, đậu que, cà rốt.", "com-chien-sai-gon", seededAt, ["chien"]),
            Item(20, "cat_main", "Cơm hến Huế", 55000, "Cơm nguội trộn hến xào, rau thơm, đậu phộng, mắm ruốc Huế.", "com-hen-hue", seededAt, ["Hue"]),
            Item(21, "cat_main", "Cơm bò lúc lắc", 95000, "Bò Úc lúc lắc áp chảo bơ tỏi, cơm trắng, salad rau xanh.", "com-bo-luc-lac", seededAt, ["bo", "cao cap"]),
            // Hải sản
            Item(22, "cat_seafood", "Tôm hùm nướng mỡ hành", 890000, "Tôm hùm tươi nướng mỡ hành phi vàng thơm phức, ăn kèm cơm chiên.", "tom-hum-nuong-mo-hanh", seededAt, ["cao cap", "tiec"]),
            Item(23, "cat_seafood", "Cá lóc nướng trui", 195000, "Cá lóc nướng rơm kiểu miền Tây, cuốn bánh tráng rau sống chấm mắm nêm.", "ca-loc-nuong-trui", seededAt, ["nuong", "mien Tay"]),
            Item(24, "cat_seafood", "Tôm rang muối Tây Ninh", 185000, "Tôm sú rang muối ớt giòn rụm, thơm lừng tỏi phi và lá chanh.", "tom-rang-muoi-tay-ninh", seededAt, ["tom", "share"]),
            Item(25, "cat_seafood", "Cua rang me", 380000, "Cua biển rang sốt me chua ngọt đậm đà, ăn kèm bánh mì nóng.", "cua-rang-me", seededAt, ["cua", "share"]),
            Item(26, "cat_seafood", "Mực xào sa tế", 135000, "Mực tươi xào sa tế ớt cay nồng, hành tây, ớt chuông, rau muống.", "muc-xao-sa-te", seededAt, ["muc", "cay vua"]),
            Item(27, "cat_seafood", "Nghêu hấp sả", 95000, "Nghêu tươi hấp sả ớt, nước dùng thơm ngọt tự nhiên.", "ngheu-hap-sa", seededAt, ["hap", "nhau"]),
            Item(28, "cat_seafood", "Ốc hương rang bơ tỏi", 165000, "Ốc hương rang bơ tỏi phi vàng, thơm nức, giòn ngọt.", "oc-huong-rang-bo-toi", seededAt, ["rang", "nhau"]),
            // Lẩu
            Item(29, "cat_hotpot", "Lẩu chua cá lăng", 320000, "Cá lăng tươi nấu lẩu chua me, dọc mùng, bạc hà, rau sống.", "lau-chua-ca-lang", seededAt, ["ca", "3-5 nguoi"]),
            Item(30, "cat_hotpot", "Lẩu bò nhúng giấm", 350000, "Bò Úc thái mỏng nhúng nước lẩu giấm nuôi, ăn kèm bún và rau.", "lau-bo-nhung-giam", seededAt, ["bo", "3-5 nguoi"]),
            Item(31, "cat_hotpot", "Lẩu nấm chay", 250000, "Nước dùng nấm hương, đông cô, kim châm, nấm đùi gà, rau củ tươi.", "lau-nam-chay", seededAt, ["chay", "nam"]),
            Item(32, "cat_hotpot", "Lẩu gà lá é Đà Lạt", 280000, "Gà ta thả vườn nấu lẩu lá é Đà Lạt thơm đặc trưng cao nguyên.", "lau-ga-la-e-da-lat", seededAt, ["ga", "Tay Nguyen"]),
            Item(33, "cat_hotpot", "Lẩu hải sản chua cay", 450000, "Tôm, mực, nghêu nấu Tom Yum chua cay đậm đà kiểu Thái-Việt.", "lau-hai-san-chua-cay", seededAt, ["cay dam", "co hai san"]),
            Item(34, "cat_hotpot", "Lẩu dê thuốc bắc", 380000, "Thịt dê non hầm thuốc bắc bổ dưỡng, ăn kèm mì và rau thơm.", "lau-de-thuoc-bac", seededAt, ["tiem", "nhau"]),
            Item(35, "cat_hotpot", "Lẩu mắm miền Tây", 320000, "Lẩu mắm cá linh chính gốc miền Tây, rau đồng, bông điên điển.", "lau-mam-mien-tay", seededAt, ["mien Tay", "dam da"]),
            // Món gà
            Item(36, "cat_chicken", "Gà nướng mật ong", 185000, "Gà ta nướng mật ong vàng ươm, da giòn thịt mềm thấm vị.", "ga-nuong-mat-ong", seededAt, ["nuong", "ngot"]),
            Item(37, "cat_chicken", "Gà hấp lá chanh", 280000, "Gà ta hấp lá chanh thơm, chấm muối tiêu chanh đặc biệt.", "ga-hap-la-chanh", seededAt, ["hap", "gia dinh"]),
            Item(38, "cat_chicken", "Cánh gà chiên nước mắm", 95000, "Cánh gà chiên giòn rim nước mắm tỏi ớt caramel hoá.", "canh-ga-chien-nuoc-mam", seededAt, ["chien", "tre em"]),
            Item(39, "cat_chicken", "Gà xào sả ớt", 95000, "Gà ta xào sả ớt cay nồng, hành tây, ớt chuông.", "ga-xao-sa-ot", seededAt, ["xao", "cay vua"]),
            Item(40, "cat_chicken", "Gà nướng muối ớt xanh", 195000, "Gà nướng muối ớt xanh Nha Trang giòn da, đậm vị.", "ga-nuong-muoi-ot-xanh", seededAt, ["nuong", "cay nhe"]),
            Item(41, "cat_chicken", "Gà tiềm thuốc bắc", 250000, "Gà ta tiềm thuốc bắc bổ dưỡng, nước dùng thanh ngọt.", "ga-tiem-thuoc-bac", seededAt, ["tiem", "nguoi gia"]),
            Item(42, "cat_chicken", "Gà rô ti kiểu Việt", 320000, "Gà rô ti vàng ruộm kiểu Việt, ăn kèm khoai tây và salad.", "ga-ro-ti-kieu-viet", seededAt, ["gia dinh"]),
            // Đặc sản vùng miền
            Item(43, "cat_regional", "Mì Quảng tôm thịt", 70000, "Mì Quảng sợi vàng, tôm thịt, đậu phộng, bánh tráng nướng.", "mi-quang-tom-thit", seededAt, ["mien Trung"]),
            Item(44, "cat_regional", "Cao lầu Hội An", 80000, "Cao lầu sợi dai đặc trưng, thịt xá xíu, rau sống Hội An.", "cao-lau-hoi-an", seededAt, ["Hoi An"]),
            Item(45, "cat_regional", "Bê thui Cầu Mống", 350000, "Bê thui da giòn thịt mềm, cuốn bánh tráng rau sống.", "be-thui-cau-mong", seededAt, ["mien Trung", "nhau"]),
            Item(46, "cat_regional", "Hủ tiếu Nam Vang", 65000, "Hủ tiếu nước trong, tôm thịt gan, giá đỗ, hẹ tươi.", "hu-tieu-nam-vang", seededAt, ["mien Nam"]),
            Item(47, "cat_regional", "Bánh tráng cuốn thịt heo", 85000, "Thịt heo luộc cuốn bánh tráng, rau sống, chấm mắm nêm.", "banh-trang-cuon-thit-heo", seededAt, ["Da Nang", "cuon"]),
            Item(48, "cat_regional", "Cháo lòng Sài Gòn", 45000, "Cháo nóng hổi với lòng heo tươi, giá đỗ, hành phi, quẩy giòn.", "chao-long-sai-gon", seededAt, ["Sai Gon", "an khuya"]),
            Item(49, "cat_regional", "Xôi gà Hà Nội", 50000, "Xôi nếp dẻo thơm, gà xé phay, hành phi, mỡ hành.", "xoi-ga-ha-noi", seededAt, ["Ha Noi", "sang"]),
            // Món chay
            Item(50, "cat_vegetarian", "Phở chay nấm đông cô", 60000, "Phở chay nước dùng nấm đông cô, đậu hũ, nấm tươi, rau thơm.", "pho-chay-nam-dong-co", seededAt, ["chay", "nam"]),
            Item(51, "cat_vegetarian", "Cơm chiên chay ngũ sắc", 50000, "Cơm chiên với nấm, đậu hũ, cà rốt, đậu que, bắp ngọt.", "com-chien-chay-ngu-sac", seededAt, ["chay", "chien"]),
            Item(52, "cat_vegetarian", "Gỏi cuốn chay", 45000, "Gỏi cuốn nhân đậu hũ, bún, rau thơm, bơ, chấm tương đậu.", "goi-cuon-chay", seededAt, ["chay", "healthy"]),
            Item(53, "cat_vegetarian", "Canh khổ qua nhồi nấm", 55000, "Khổ qua nhồi nấm đông cô, nấu canh thanh mát giải nhiệt.", "canh-kho-qua-nhoi-nam", seededAt, ["chay", "giai nhiet"]),
            Item(54, "cat_vegetarian", "Đậu hũ sốt cà chua", 45000, "Đậu hũ chiên giòn sốt cà chua tươi, hành lá, rau mùi.", "dau-hu-sot-ca-chua", seededAt, ["chay", "dau hu"]),
            Item(55, "cat_vegetarian", "Mì Quảng chay", 55000, "Mì Quảng chay nước dùng nấm, đậu hũ, rau sống, đậu phộng.", "mi-quang-chay", seededAt, ["chay", "mien Trung"]),
            Item(56, "cat_vegetarian", "Bún chay Huế", 55000, "Bún Huế chay nước dùng sả ớt, đậu hũ, nấm, rau sống.", "bun-chay-hue", seededAt, ["chay", "Hue"]),
            // Cà phê & Trà
            Item(57, "cat_drink", "Cà phê sữa đá", 35000, "Cà phê phin truyền thống pha sữa đặc, đá viên mát lạnh.", "ca-phe-sua-da", seededAt, ["pho bien"]),
            Item(58, "cat_drink", "Cà phê trứng Hà Nội", 45000, "Cà phê đen đậm phủ kem trứng béo ngậy kiểu Hà Nội.", "ca-phe-trung-ha-noi", seededAt, ["Ha Noi", "beo"]),
            Item(59, "cat_drink", "Bạc xỉu Sài Gòn", 35000, "Sữa đặc nhiều, cà phê ít — thức uống nhẹ nhàng kiểu Sài Gòn.", "bac-xiu-sai-gon", seededAt, ["Sai Gon", "ngot"]),
            Item(60, "cat_drink", "Trà đào cam sả", 45000, "Trà pha đào tươi, cam vàng, sả thơm, đá viên mát lạnh.", "tra-dao-cam-sa", seededAt, ["giai nhiet"]),
            Item(61, "cat_drink", "Trà sen Tây Hồ", 55000, "Trà ướp sen Tây Hồ thơm thanh, pha ấm truyền thống.", "tra-sen-tay-ho", seededAt, ["Ha Noi", "thanh nhe"]),
            Item(62, "cat_drink", "Trà sữa trân châu", 45000, "Trà sữa đậm đà với trân châu đen dai giòn tự làm.", "tra-sua-tran-chau", seededAt, ["tre em", "ngot"]),
            Item(63, "cat_drink", "Cà phê dừa", 45000, "Cà phê phin pha cốt dừa béo ngậy, đá xay mát lạnh.", "ca-phe-dua", seededAt, ["beo"]),
            // Nước ép & Sinh tố
            Item(64, "cat_juice", "Nước ép cam tươi", 40000, "Cam tươi ép nguyên chất, không đường, giàu vitamin C.", "nuoc-ep-cam-tuoi", seededAt, ["healthy"]),
            Item(65, "cat_juice", "Sinh tố bơ Đắk Lắk", 50000, "Bơ 034 Đắk Lắk xay nhuyễn với sữa đặc và đá viên.", "sinh-to-bo-dak-lak", seededAt, ["beo", "Tay Nguyen"]),
            Item(66, "cat_juice", "Nước ép dưa hấu", 35000, "Dưa hấu đỏ ép tươi mát lạnh, giải nhiệt mùa hè.", "nuoc-ep-dua-hau", seededAt, ["giai nhiet"]),
            Item(67, "cat_juice", "Sinh tố xoài Hòa Lộc", 45000, "Xoài cát Hòa Lộc xay nhuyễn với sữa tươi và đá.", "sinh-to-xoai-hoa-loc", seededAt, ["ngot"]),
            Item(68, "cat_juice", "Nước rau má", 30000, "Rau má tươi xay nhuyễn, thanh mát giải nhiệt.", "nuoc-rau-ma", seededAt, ["giai nhiet", "healthy"]),
            Item(69, "cat_juice", "Sinh tố dâu tây Đà Lạt", 50000, "Dâu tây Đà Lạt xay sữa tươi, ngọt dịu tự nhiên.", "sinh-to-dau-tay-da-lat", seededAt, ["ngot"]),
            Item(70, "cat_juice", "Nước mía Sài Gòn", 25000, "Mía tươi ép cùng quất, đá lạnh — đặc sản đường phố Sài Gòn.", "nuoc-mia-sai-gon", seededAt, ["Sai Gon", "binh dan"]),
            // Tráng miệng
            Item(71, "cat_dessert", "Chè khúc bạch", 45000, "Chè khúc bạch mát lạnh, thạch hạnh nhân, vải thiều, nước cốt dừa.", "che-khuc-bach", seededAt, ["ngot", "giai nhiet"]),
            Item(72, "cat_dessert", "Bánh flan caramel", 30000, "Bánh flan mềm mịn với lớp caramel đắng nhẹ.", "banh-flan-caramel", seededAt, ["ngot", "tre em"]),
            Item(73, "cat_dessert", "Chè bưởi", 35000, "Chè bưởi cùi trắng, đậu xanh, nước cốt dừa béo ngậy.", "che-buoi", seededAt, ["ngot"]),
            Item(74, "cat_dessert", "Sương sa hạt lựu", 35000, "Sương sa mát lạnh, hạt lựu giòn sần sật, nước cốt dừa.", "suong-sa-hat-luu", seededAt, ["giai nhiet"]),
            Item(75, "cat_dessert", "Chè trôi nước", 35000, "Viên chè nếp dẻo nhân đậu xanh, nước gừng ngọt ấm.", "che-troi-nuoc", seededAt, ["ngot", "mua lanh"]),
            Item(76, "cat_dessert", "Bánh chuối nướng", 30000, "Bánh chuối nướng vàng ruộm, nước cốt dừa béo, mè rang.", "banh-chuoi-nuong", seededAt, ["nuong", "ngot"]),
            Item(77, "cat_dessert", "Xôi xoài", 45000, "Xôi nếp dẻo thơm, xoài chín ngọt, nước cốt dừa béo ngậy.", "xoi-xoai", seededAt, ["ngot"]),
            // Trái cây tươi
            Item(78, "cat_fruit", "Đĩa trái cây theo mùa", 75000, "Tổng hợp trái cây tươi theo mùa, bày đĩa đẹp mắt.", "dia-trai-cay-theo-mua", seededAt, ["healthy", "share"]),
            Item(79, "cat_fruit", "Xoài cát Hòa Lộc", 65000, "Xoài cát Hòa Lộc chín vàng, ngọt lịm, thơm đặc trưng.", "xoai-cat-hoa-loc", seededAt, ["ngot"]),
            Item(80, "cat_fruit", "Sầu riêng Ri6", 120000, "Sầu riêng Ri6 cơm vàng dày, béo ngậy, ít xơ.", "sau-rieng-ri6", seededAt, ["beo", "cao cap"]),
            Item(81, "cat_fruit", "Dưa hấu lạnh", 35000, "Dưa hấu đỏ mát lạnh, cắt miếng sẵn, giải khát.", "dua-hau-lanh", seededAt, ["giai nhiet"]),
            Item(82, "cat_fruit", "Bưởi da xanh Bến Tre", 55000, "Bưởi da xanh ruột đỏ, ngọt thanh, không đắng.", "buoi-da-xanh-ben-tre", seededAt, ["mien Tay"]),
            Item(83, "cat_fruit", "Thanh long Bình Thuận", 45000, "Thanh long ruột đỏ Bình Thuận tươi mát, giàu dinh dưỡng.", "thanh-long-binh-thuan", seededAt, ["healthy"]),
            Item(84, "cat_fruit", "Đu đủ chín mật ong", 40000, "Đu đủ chín vàng ngọt mật, cắt miếng rưới mật ong.", "du-du-chin-mat-ong", seededAt, ["ngot", "healthy"]),
            // Bia & Rượu
            Item(85, "cat_alcohol", "Bia Sài Gòn Special", 20000, "Bia Sài Gòn Special lon 330ml, vị đậm đà truyền thống.", "bia-sai-gon-special", seededAt, ["nhau"]),
            Item(86, "cat_alcohol", "Bia Hà Nội", 18000, "Bia Hà Nội lon 330ml, vị nhẹ thanh mát.", "bia-ha-noi", seededAt, ["nhau"]),
            Item(87, "cat_alcohol", "Bia Tiger Crystal", 22000, "Bia Tiger Crystal lon 330ml, vị thanh nhẹ.", "bia-tiger-crystal", seededAt, ["nhau"]),
            Item(88, "cat_alcohol", "Bia hơi Hà Nội", 12000, "Bia hơi Hà Nội tươi mát, cốc 330ml.", "bia-hoi-ha-noi", seededAt, ["nhau", "binh dan"]),
            Item(89, "cat_alcohol", "Rượu nếp cẩm", 35000, "Rượu nếp cẩm truyền thống, ngọt dịu, thơm nồng.", "ruou-nep-cam", seededAt, ["nhau"]),
            Item(90, "cat_alcohol", "Rượu mơ Hà Nội", 40000, "Rượu mơ Hà Nội chua ngọt thanh, uống lạnh.", "ruou-mo-ha-noi", seededAt, ["nhau", "chua"]),
            Item(91, "cat_alcohol", "Cocktail chanh đào mật ong", 65000, "Cocktail chanh đào mật ong tươi mát, thơm ngọt tự nhiên.", "cocktail-chanh-dao-mat-ong", seededAt, ["ngot"])
        ];
    }

    private static Category Cat(string id, string name, int displayOrder, DateTimeOffset seededAt)
    {
        return new Category
        {
            Id = id,
            Name = name,
            DisplayOrder = displayOrder,
            IsActive = true,
            CreatedAt = seededAt,
            UpdatedAt = seededAt
        };
    }

    private static MenuItem Item(
        int number,
        string categoryId,
        string name,
        decimal price,
        string description,
        string imageSlug,
        DateTimeOffset seededAt,
        string[] tags)
    {
        return new MenuItem
        {
            Id = $"m_{number:D3}",
            CategoryId = categoryId,
            Name = name,
            Description = description,
            Price = price,
            ImageUrl = $"/menu-images/{number:D2}-{imageSlug}.png",
            IsAvailable = true,
            Tags = tags.ToList(),
            CreatedAt = seededAt,
            UpdatedAt = seededAt
        };
    }
}
