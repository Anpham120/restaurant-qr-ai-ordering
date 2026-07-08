using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class SeedOfficialMenuAndThirtyTables : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "customer_phone_number",
                table: "orders",
                type: "character varying(20)",
                maxLength: 20,
                nullable: true);

            migrationBuilder.AddColumn<decimal>(
                name: "discount_amount",
                table: "orders",
                type: "numeric(18,2)",
                precision: 18,
                scale: 2,
                nullable: false,
                defaultValue: 0m);

            migrationBuilder.AddColumn<string>(
                name: "promotion_code",
                table: "orders",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "promotion_id",
                table: "orders",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.CreateTable(
                name: "loyalty_members",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    phone_number = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    full_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    points = table.Column<int>(type: "integer", nullable: false),
                    lifetime_spend = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_loyalty_members", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "loyalty_rewards",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    description = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    points_required = table.Column<int>(type: "integer", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_loyalty_rewards", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "promotions",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    description = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    discount_value = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    min_order_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: true),
                    max_discount_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: true),
                    is_flash_sale = table.Column<bool>(type: "boolean", nullable: false),
                    starts_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    ends_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_promotions", x => x.id);
                });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_appetizer",
                column: "name",
                value: "Khai vị");

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_dessert",
                columns: new[] { "display_order", "name" },
                values: new object[] { 110, "Tráng miệng" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_drink",
                columns: new[] { "display_order", "name" },
                values: new object[] { 90, "Cà phê & Trà" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_main",
                columns: new[] { "display_order", "name" },
                values: new object[] { 30, "Cơm Việt" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_noodle",
                columns: new[] { "display_order", "name" },
                values: new object[] { 20, "Phở & Bún" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_seafood",
                column: "name",
                value: "Hải sản");

            migrationBuilder.InsertData(
                table: "categories",
                columns: new[] { "id", "created_at", "display_order", "is_active", "name", "updated_at" },
                values: new object[,]
                {
                    { "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 130, true, "Bia & Rượu", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 60, true, "Món gà", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 120, true, "Trái cây tươi", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 50, true, "Lẩu", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 100, true, "Nước ép & Sinh tố", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 70, true, "Đặc sản vùng miền", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), 80, true, "Món chay", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_001",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_appetizer", "Tôm tươi, thịt heo luộc, bún, rau thơm cuốn trong bánh tráng mỏng, chấm tương đậu phộng.", "/menu-images/01-goi-cuon-tom-thit.png", "Gỏi cuốn tôm thịt", 65000m, new[] { "pho bien", "signature" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_002",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_appetizer", "Nem giòn rụm nhân thịt, mộc nhĩ, miến, trứng — chiên vàng, chấm nước mắm chua ngọt.", "/menu-images/02-nem-ran-ha-noi.png", "Nem rán Hà Nội", 75000m, new[] { "chien", "Ha Noi" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_003",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_appetizer", "Vỏ giòn vàng ươm, nhân tôm thịt giá đỗ, cuốn rau sống chấm nước mắm.", "/menu-images/03-banh-xeo-mien-tay.png", "Bánh xèo miền Tây", 85000m, new[] { "mien Tay" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_004",
                columns: new[] { "category_id", "description", "image_url", "is_available", "name", "price", "tags" },
                values: new object[] { "cat_appetizer", "Bánh cuốn mỏng mịn nhân thịt mộc nhĩ, ăn kèm chả quế và nước mắm.", "/menu-images/04-banh-cuon-thanh-tri.png", true, "Bánh cuốn Thanh Trì", 55000m, new[] { "Ha Noi", "sang" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_005",
                columns: new[] { "description", "image_url", "name", "price", "tags" },
                values: new object[] { "Xoài xanh giòn trộn tôm sú tươi, đậu phộng rang, rau thơm, nước mắm chua ngọt.", "/menu-images/05-goi-xoai-tom-su.png", "Gỏi xoài tôm sú", 85000m, new[] { "chua", "tom" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_006",
                columns: new[] { "description", "image_url", "name", "price", "tags" },
                values: new object[] { "Bánh mì giòn kẹp pate, chả lụa, dưa leo, đồ chua và rau mùi tươi.", "/menu-images/06-banh-mi-pate-sai-gon.png", "Bánh mì pate Sài Gòn", 35000m, new[] { "Sai Gon", "binh dan" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_007",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_appetizer", "Súp nóng hổi với thịt cua, măng tươi, trứng cút và nấm hương thơm lừng.", "/menu-images/07-sup-mang-cua.png", "Súp măng cua", 65000m, new[] { "cua", "nong" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_008",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Nước dùng hầm xương 12 tiếng, thịt bò tái mềm, nạm giòn, hành lá tươi.", "/menu-images/08-pho-bo-tai-nam.png", "Phở bò tái nạm", 75000m, new[] { "bo", "signature" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_009",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Phở gà ta nước trong, thịt gà dai ngọt, hành phi thơm phức.", "/menu-images/09-pho-ga-ta.png", "Phở gà ta", 70000m, new[] { "ga" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_010",
                columns: new[] { "category_id", "description", "image_url", "is_available", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Nước lèo đậm đà sả ớt, thịt bò giò heo, chả cua Huế chính gốc.", "/menu-images/10-bun-bo-hue.png", true, "Bún bò Huế", 80000m, new[] { "cay vua", "Hue" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_011",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Chả viên và chả miếng nướng than hoa, bún tươi, nước mắm chua ngọt.", "/menu-images/11-bun-cha-ha-noi.png", "Bún chả Hà Nội", 75000m, new[] { "nuong", "Ha Noi" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_012",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Nước dùng cua đồng cà chua, riêu cua béo ngậy, đậu hũ, rau muống.", "/menu-images/12-bun-rieu-cua-dong.png", "Bún riêu cua đồng", 70000m, new[] { "cua" } });

            migrationBuilder.InsertData(
                table: "menu_items",
                columns: new[] { "id", "category_id", "created_at", "description", "image_url", "is_available", "name", "price", "tags", "updated_at" },
                values: new object[,]
                {
                    { "m_013", "cat_noodle", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Nước lèo mắm cá linh đậm đà, tôm, mực, thịt quay, rau sống miền Tây.", "/menu-images/13-bun-mam-mien-tay.png", true, "Bún mắm miền Tây", 85000m, new[] { "mien Tay", "dam da" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_014", "cat_noodle", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bún lá, đậu hũ chiên giòn, chả cốm, nem chua, mắm tôm Gia Truyền.", "/menu-images/14-bun-dau-mam-tom.png", true, "Bún đậu mắm tôm", 95000m, new[] { "Ha Noi", "nhom ban" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_015", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Sườn nướng mật ong, bì heo giòn dai, chả trứng hấp mềm — Sài Gòn chính gốc.", "/menu-images/15-com-tam-suon-bi-cha.png", true, "Cơm tấm sườn bì chả", 65000m, new[] { "Sai Gon", "pho bien" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_016", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cơm nghệ vàng ươm, gà xé phay, rau sống, nước mắm gừng đặc trưng.", "/menu-images/16-com-ga-hoi-an.png", true, "Cơm gà Hội An", 70000m, new[] { "ga", "Hoi An" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_017", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Sườn heo ướp ngũ vị nướng than hoa, cơm trắng, đồ chua, nước mắm.", "/menu-images/17-com-suon-nuong.png", true, "Cơm sườn nướng", 60000m, new[] { "nuong", "heo" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_018", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cá basa kho tộ đất với nước màu dừa, tiêu, hành, ớt, cơm nóng.", "/menu-images/18-com-ca-kho-to.png", true, "Cơm cá kho tộ", 65000m, new[] { "ca", "kho" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_019", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cơm chiên tỏi với lạp xưởng, tôm, trứng, đậu que, cà rốt.", "/menu-images/19-com-chien-sai-gon.png", true, "Cơm chiên Sài Gòn", 55000m, new[] { "chien" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_020", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cơm nguội trộn hến xào, rau thơm, đậu phộng, mắm ruốc Huế.", "/menu-images/20-com-hen-hue.png", true, "Cơm hến Huế", 55000m, new[] { "Hue" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_021", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bò Úc lúc lắc áp chảo bơ tỏi, cơm trắng, salad rau xanh.", "/menu-images/21-com-bo-luc-lac.png", true, "Cơm bò lúc lắc", 95000m, new[] { "bo", "cao cap" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_022", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Tôm hùm tươi nướng mỡ hành phi vàng thơm phức, ăn kèm cơm chiên.", "/menu-images/22-tom-hum-nuong-mo-hanh.png", true, "Tôm hùm nướng mỡ hành", 890000m, new[] { "cao cap", "tiec" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_023", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cá lóc nướng rơm kiểu miền Tây, cuốn bánh tráng rau sống chấm mắm nêm.", "/menu-images/23-ca-loc-nuong-trui.png", true, "Cá lóc nướng trui", 195000m, new[] { "nuong", "mien Tay" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_024", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Tôm sú rang muối ớt giòn rụm, thơm lừng tỏi phi và lá chanh.", "/menu-images/24-tom-rang-muoi-tay-ninh.png", true, "Tôm rang muối Tây Ninh", 185000m, new[] { "tom", "share" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_025", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cua biển rang sốt me chua ngọt đậm đà, ăn kèm bánh mì nóng.", "/menu-images/25-cua-rang-me.png", true, "Cua rang me", 380000m, new[] { "cua", "share" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_026", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Mực tươi xào sa tế ớt cay nồng, hành tây, ớt chuông, rau muống.", "/menu-images/26-muc-xao-sa-te.png", true, "Mực xào sa tế", 135000m, new[] { "muc", "cay vua" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_027", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Nghêu tươi hấp sả ớt, nước dùng thơm ngọt tự nhiên.", "/menu-images/27-ngheu-hap-sa.png", true, "Nghêu hấp sả", 95000m, new[] { "hap", "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_028", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Ốc hương rang bơ tỏi phi vàng, thơm nức, giòn ngọt.", "/menu-images/28-oc-huong-rang-bo-toi.png", true, "Ốc hương rang bơ tỏi", 165000m, new[] { "rang", "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_057", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cà phê phin truyền thống pha sữa đặc, đá viên mát lạnh.", "/menu-images/57-ca-phe-sua-da.png", true, "Cà phê sữa đá", 35000m, new[] { "pho bien" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_058", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cà phê đen đậm phủ kem trứng béo ngậy kiểu Hà Nội.", "/menu-images/58-ca-phe-trung-ha-noi.png", true, "Cà phê trứng Hà Nội", 45000m, new[] { "Ha Noi", "beo" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_059", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Sữa đặc nhiều, cà phê ít — thức uống nhẹ nhàng kiểu Sài Gòn.", "/menu-images/59-bac-xiu-sai-gon.png", true, "Bạc xỉu Sài Gòn", 35000m, new[] { "Sai Gon", "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_060", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Trà pha đào tươi, cam vàng, sả thơm, đá viên mát lạnh.", "/menu-images/60-tra-dao-cam-sa.png", true, "Trà đào cam sả", 45000m, new[] { "giai nhiet" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_061", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Trà ướp sen Tây Hồ thơm thanh, pha ấm truyền thống.", "/menu-images/61-tra-sen-tay-ho.png", true, "Trà sen Tây Hồ", 55000m, new[] { "Ha Noi", "thanh nhe" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_062", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Trà sữa đậm đà với trân châu đen dai giòn tự làm.", "/menu-images/62-tra-sua-tran-chau.png", true, "Trà sữa trân châu", 45000m, new[] { "tre em", "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_063", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cà phê phin pha cốt dừa béo ngậy, đá xay mát lạnh.", "/menu-images/63-ca-phe-dua.png", true, "Cà phê dừa", 45000m, new[] { "beo" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_071", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Chè khúc bạch mát lạnh, thạch hạnh nhân, vải thiều, nước cốt dừa.", "/menu-images/71-che-khuc-bach.png", true, "Chè khúc bạch", 45000m, new[] { "ngot", "giai nhiet" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_072", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bánh flan mềm mịn với lớp caramel đắng nhẹ.", "/menu-images/72-banh-flan-caramel.png", true, "Bánh flan caramel", 30000m, new[] { "ngot", "tre em" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_073", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Chè bưởi cùi trắng, đậu xanh, nước cốt dừa béo ngậy.", "/menu-images/73-che-buoi.png", true, "Chè bưởi", 35000m, new[] { "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_074", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Sương sa mát lạnh, hạt lựu giòn sần sật, nước cốt dừa.", "/menu-images/74-suong-sa-hat-luu.png", true, "Sương sa hạt lựu", 35000m, new[] { "giai nhiet" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_075", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Viên chè nếp dẻo nhân đậu xanh, nước gừng ngọt ấm.", "/menu-images/75-che-troi-nuoc.png", true, "Chè trôi nước", 35000m, new[] { "ngot", "mua lanh" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_076", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bánh chuối nướng vàng ruộm, nước cốt dừa béo, mè rang.", "/menu-images/76-banh-chuoi-nuong.png", true, "Bánh chuối nướng", 30000m, new[] { "nuong", "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_077", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Xôi nếp dẻo thơm, xoài chín ngọt, nước cốt dừa béo ngậy.", "/menu-images/77-xoi-xoai.png", true, "Xôi xoài", 45000m, new[] { "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.InsertData(
                table: "restaurant_tables",
                columns: new[] { "id", "created_at", "display_name", "is_active", "qr_token", "table_code", "updated_at" },
                values: new object[,]
                {
                    { "tbl_09", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 09", true, "cmc-table-t09-qr", "T09", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_10", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 10", true, "cmc-table-t10-qr", "T10", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_11", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 11", true, "cmc-table-t11-qr", "T11", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_12", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 12", true, "cmc-table-t12-qr", "T12", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_13", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 13", true, "cmc-table-t13-qr", "T13", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_14", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 14", true, "cmc-table-t14-qr", "T14", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_15", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 15", true, "cmc-table-t15-qr", "T15", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_16", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 16", true, "cmc-table-t16-qr", "T16", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_17", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 17", true, "cmc-table-t17-qr", "T17", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_18", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 18", true, "cmc-table-t18-qr", "T18", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_19", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 19", true, "cmc-table-t19-qr", "T19", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_20", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 20", true, "cmc-table-t20-qr", "T20", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_21", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 21", true, "cmc-table-t21-qr", "T21", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_22", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 22", true, "cmc-table-t22-qr", "T22", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_23", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 23", true, "cmc-table-t23-qr", "T23", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_24", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 24", true, "cmc-table-t24-qr", "T24", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_25", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 25", true, "cmc-table-t25-qr", "T25", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_26", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 26", true, "cmc-table-t26-qr", "T26", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_27", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 27", true, "cmc-table-t27-qr", "T27", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_28", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 28", true, "cmc-table-t28-qr", "T28", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_29", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 29", true, "cmc-table-t29-qr", "T29", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_30", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), "Ban 30", true, "cmc-table-t30-qr", "T30", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.InsertData(
                table: "menu_items",
                columns: new[] { "id", "category_id", "created_at", "description", "image_url", "is_available", "name", "price", "tags", "updated_at" },
                values: new object[,]
                {
                    { "m_029", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cá lăng tươi nấu lẩu chua me, dọc mùng, bạc hà, rau sống.", "/menu-images/29-lau-chua-ca-lang.png", true, "Lẩu chua cá lăng", 320000m, new[] { "ca", "3-5 nguoi" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_030", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bò Úc thái mỏng nhúng nước lẩu giấm nuôi, ăn kèm bún và rau.", "/menu-images/30-lau-bo-nhung-giam.png", true, "Lẩu bò nhúng giấm", 350000m, new[] { "bo", "3-5 nguoi" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_031", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Nước dùng nấm hương, đông cô, kim châm, nấm đùi gà, rau củ tươi.", "/menu-images/31-lau-nam-chay.png", true, "Lẩu nấm chay", 250000m, new[] { "chay", "nam" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_032", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà ta thả vườn nấu lẩu lá é Đà Lạt thơm đặc trưng cao nguyên.", "/menu-images/32-lau-ga-la-e-da-lat.png", true, "Lẩu gà lá é Đà Lạt", 280000m, new[] { "ga", "Tay Nguyen" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_033", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Tôm, mực, nghêu nấu Tom Yum chua cay đậm đà kiểu Thái-Việt.", "/menu-images/33-lau-hai-san-chua-cay.png", true, "Lẩu hải sản chua cay", 450000m, new[] { "cay dam", "co hai san" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_034", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Thịt dê non hầm thuốc bắc bổ dưỡng, ăn kèm mì và rau thơm.", "/menu-images/34-lau-de-thuoc-bac.png", true, "Lẩu dê thuốc bắc", 380000m, new[] { "tiem", "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_035", "cat_hotpot", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Lẩu mắm cá linh chính gốc miền Tây, rau đồng, bông điên điển.", "/menu-images/35-lau-mam-mien-tay.png", true, "Lẩu mắm miền Tây", 320000m, new[] { "mien Tay", "dam da" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_036", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà ta nướng mật ong vàng ươm, da giòn thịt mềm thấm vị.", "/menu-images/36-ga-nuong-mat-ong.png", true, "Gà nướng mật ong", 185000m, new[] { "nuong", "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_037", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà ta hấp lá chanh thơm, chấm muối tiêu chanh đặc biệt.", "/menu-images/37-ga-hap-la-chanh.png", true, "Gà hấp lá chanh", 280000m, new[] { "hap", "gia dinh" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_038", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cánh gà chiên giòn rim nước mắm tỏi ớt caramel hoá.", "/menu-images/38-canh-ga-chien-nuoc-mam.png", true, "Cánh gà chiên nước mắm", 95000m, new[] { "chien", "tre em" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_039", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà ta xào sả ớt cay nồng, hành tây, ớt chuông.", "/menu-images/39-ga-xao-sa-ot.png", true, "Gà xào sả ớt", 95000m, new[] { "xao", "cay vua" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_040", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà nướng muối ớt xanh Nha Trang giòn da, đậm vị.", "/menu-images/40-ga-nuong-muoi-ot-xanh.png", true, "Gà nướng muối ớt xanh", 195000m, new[] { "nuong", "cay nhe" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_041", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà ta tiềm thuốc bắc bổ dưỡng, nước dùng thanh ngọt.", "/menu-images/41-ga-tiem-thuoc-bac.png", true, "Gà tiềm thuốc bắc", 250000m, new[] { "tiem", "nguoi gia" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_042", "cat_chicken", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gà rô ti vàng ruộm kiểu Việt, ăn kèm khoai tây và salad.", "/menu-images/42-ga-ro-ti-kieu-viet.png", true, "Gà rô ti kiểu Việt", 320000m, new[] { "gia dinh" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_043", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Mì Quảng sợi vàng, tôm thịt, đậu phộng, bánh tráng nướng.", "/menu-images/43-mi-quang-tom-thit.png", true, "Mì Quảng tôm thịt", 70000m, new[] { "mien Trung" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_044", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cao lầu sợi dai đặc trưng, thịt xá xíu, rau sống Hội An.", "/menu-images/44-cao-lau-hoi-an.png", true, "Cao lầu Hội An", 80000m, new[] { "Hoi An" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_045", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bê thui da giòn thịt mềm, cuốn bánh tráng rau sống.", "/menu-images/45-be-thui-cau-mong.png", true, "Bê thui Cầu Mống", 350000m, new[] { "mien Trung", "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_046", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Hủ tiếu nước trong, tôm thịt gan, giá đỗ, hẹ tươi.", "/menu-images/46-hu-tieu-nam-vang.png", true, "Hủ tiếu Nam Vang", 65000m, new[] { "mien Nam" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_047", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Thịt heo luộc cuốn bánh tráng, rau sống, chấm mắm nêm.", "/menu-images/47-banh-trang-cuon-thit-heo.png", true, "Bánh tráng cuốn thịt heo", 85000m, new[] { "Da Nang", "cuon" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_048", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cháo nóng hổi với lòng heo tươi, giá đỗ, hành phi, quẩy giòn.", "/menu-images/48-chao-long-sai-gon.png", true, "Cháo lòng Sài Gòn", 45000m, new[] { "Sai Gon", "an khuya" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_049", "cat_regional", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Xôi nếp dẻo thơm, gà xé phay, hành phi, mỡ hành.", "/menu-images/49-xoi-ga-ha-noi.png", true, "Xôi gà Hà Nội", 50000m, new[] { "Ha Noi", "sang" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_050", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Phở chay nước dùng nấm đông cô, đậu hũ, nấm tươi, rau thơm.", "/menu-images/50-pho-chay-nam-dong-co.png", true, "Phở chay nấm đông cô", 60000m, new[] { "chay", "nam" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_051", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cơm chiên với nấm, đậu hũ, cà rốt, đậu que, bắp ngọt.", "/menu-images/51-com-chien-chay-ngu-sac.png", true, "Cơm chiên chay ngũ sắc", 50000m, new[] { "chay", "chien" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_052", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Gỏi cuốn nhân đậu hũ, bún, rau thơm, bơ, chấm tương đậu.", "/menu-images/52-goi-cuon-chay.png", true, "Gỏi cuốn chay", 45000m, new[] { "chay", "healthy" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_053", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Khổ qua nhồi nấm đông cô, nấu canh thanh mát giải nhiệt.", "/menu-images/53-canh-kho-qua-nhoi-nam.png", true, "Canh khổ qua nhồi nấm", 55000m, new[] { "chay", "giai nhiet" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_054", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Đậu hũ chiên giòn sốt cà chua tươi, hành lá, rau mùi.", "/menu-images/54-dau-hu-sot-ca-chua.png", true, "Đậu hũ sốt cà chua", 45000m, new[] { "chay", "dau hu" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_055", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Mì Quảng chay nước dùng nấm, đậu hũ, rau sống, đậu phộng.", "/menu-images/55-mi-quang-chay.png", true, "Mì Quảng chay", 55000m, new[] { "chay", "mien Trung" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_056", "cat_vegetarian", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bún Huế chay nước dùng sả ớt, đậu hũ, nấm, rau sống.", "/menu-images/56-bun-chay-hue.png", true, "Bún chay Huế", 55000m, new[] { "chay", "Hue" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_064", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cam tươi ép nguyên chất, không đường, giàu vitamin C.", "/menu-images/64-nuoc-ep-cam-tuoi.png", true, "Nước ép cam tươi", 40000m, new[] { "healthy" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_065", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bơ 034 Đắk Lắk xay nhuyễn với sữa đặc và đá viên.", "/menu-images/65-sinh-to-bo-dak-lak.png", true, "Sinh tố bơ Đắk Lắk", 50000m, new[] { "beo", "Tay Nguyen" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_066", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Dưa hấu đỏ ép tươi mát lạnh, giải nhiệt mùa hè.", "/menu-images/66-nuoc-ep-dua-hau.png", true, "Nước ép dưa hấu", 35000m, new[] { "giai nhiet" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_067", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Xoài cát Hòa Lộc xay nhuyễn với sữa tươi và đá.", "/menu-images/67-sinh-to-xoai-hoa-loc.png", true, "Sinh tố xoài Hòa Lộc", 45000m, new[] { "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_068", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Rau má tươi xay nhuyễn, thanh mát giải nhiệt.", "/menu-images/68-nuoc-rau-ma.png", true, "Nước rau má", 30000m, new[] { "giai nhiet", "healthy" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_069", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Dâu tây Đà Lạt xay sữa tươi, ngọt dịu tự nhiên.", "/menu-images/69-sinh-to-dau-tay-da-lat.png", true, "Sinh tố dâu tây Đà Lạt", 50000m, new[] { "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_070", "cat_juice", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Mía tươi ép cùng quất, đá lạnh — đặc sản đường phố Sài Gòn.", "/menu-images/70-nuoc-mia-sai-gon.png", true, "Nước mía Sài Gòn", 25000m, new[] { "Sai Gon", "binh dan" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_078", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Tổng hợp trái cây tươi theo mùa, bày đĩa đẹp mắt.", "/menu-images/78-dia-trai-cay-theo-mua.png", true, "Đĩa trái cây theo mùa", 75000m, new[] { "healthy", "share" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_079", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Xoài cát Hòa Lộc chín vàng, ngọt lịm, thơm đặc trưng.", "/menu-images/79-xoai-cat-hoa-loc.png", true, "Xoài cát Hòa Lộc", 65000m, new[] { "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_080", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Sầu riêng Ri6 cơm vàng dày, béo ngậy, ít xơ.", "/menu-images/80-sau-rieng-ri6.png", true, "Sầu riêng Ri6", 120000m, new[] { "beo", "cao cap" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_081", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Dưa hấu đỏ mát lạnh, cắt miếng sẵn, giải khát.", "/menu-images/81-dua-hau-lanh.png", true, "Dưa hấu lạnh", 35000m, new[] { "giai nhiet" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_082", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bưởi da xanh ruột đỏ, ngọt thanh, không đắng.", "/menu-images/82-buoi-da-xanh-ben-tre.png", true, "Bưởi da xanh Bến Tre", 55000m, new[] { "mien Tay" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_083", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Thanh long ruột đỏ Bình Thuận tươi mát, giàu dinh dưỡng.", "/menu-images/83-thanh-long-binh-thuan.png", true, "Thanh long Bình Thuận", 45000m, new[] { "healthy" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_084", "cat_fruit", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Đu đủ chín vàng ngọt mật, cắt miếng rưới mật ong.", "/menu-images/84-du-du-chin-mat-ong.png", true, "Đu đủ chín mật ong", 40000m, new[] { "ngot", "healthy" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_085", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bia Sài Gòn Special lon 330ml, vị đậm đà truyền thống.", "/menu-images/85-bia-sai-gon-special.png", true, "Bia Sài Gòn Special", 20000m, new[] { "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_086", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bia Hà Nội lon 330ml, vị nhẹ thanh mát.", "/menu-images/86-bia-ha-noi.png", true, "Bia Hà Nội", 18000m, new[] { "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_087", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bia Tiger Crystal lon 330ml, vị thanh nhẹ.", "/menu-images/87-bia-tiger-crystal.png", true, "Bia Tiger Crystal", 22000m, new[] { "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_088", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Bia hơi Hà Nội tươi mát, cốc 330ml.", "/menu-images/88-bia-hoi-ha-noi.png", true, "Bia hơi Hà Nội", 12000m, new[] { "nhau", "binh dan" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_089", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Rượu nếp cẩm truyền thống, ngọt dịu, thơm nồng.", "/menu-images/89-ruou-nep-cam.png", true, "Rượu nếp cẩm", 35000m, new[] { "nhau" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_090", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Rượu mơ Hà Nội chua ngọt thanh, uống lạnh.", "/menu-images/90-ruou-mo-ha-noi.png", true, "Rượu mơ Hà Nội", 40000m, new[] { "nhau", "chua" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_091", "cat_alcohol", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), "Cocktail chanh đào mật ong tươi mát, thơm ngọt tự nhiên.", "/menu-images/91-cocktail-chanh-dao-mat-ong.png", true, "Cocktail chanh đào mật ong", 65000m, new[] { "ngot" }, new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.CreateIndex(
                name: "IX_orders_promotion_id",
                table: "orders",
                column: "promotion_id");

            migrationBuilder.CreateIndex(
                name: "IX_loyalty_members_phone_number",
                table: "loyalty_members",
                column: "phone_number",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_loyalty_rewards_is_active",
                table: "loyalty_rewards",
                column: "is_active");

            migrationBuilder.CreateIndex(
                name: "IX_loyalty_rewards_points_required",
                table: "loyalty_rewards",
                column: "points_required");

            migrationBuilder.CreateIndex(
                name: "IX_promotions_code",
                table: "promotions",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_promotions_is_active",
                table: "promotions",
                column: "is_active");

            migrationBuilder.AddForeignKey(
                name: "FK_orders_promotions_promotion_id",
                table: "orders",
                column: "promotion_id",
                principalTable: "promotions",
                principalColumn: "id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_orders_promotions_promotion_id",
                table: "orders");

            migrationBuilder.DropTable(
                name: "loyalty_members");

            migrationBuilder.DropTable(
                name: "loyalty_rewards");

            migrationBuilder.DropTable(
                name: "promotions");

            migrationBuilder.DropIndex(
                name: "IX_orders_promotion_id",
                table: "orders");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_013");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_014");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_015");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_016");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_017");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_018");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_019");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_020");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_021");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_022");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_023");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_024");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_025");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_026");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_027");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_028");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_029");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_030");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_031");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_032");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_033");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_034");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_035");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_036");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_037");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_038");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_039");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_040");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_041");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_042");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_043");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_044");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_045");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_046");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_047");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_048");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_049");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_050");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_051");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_052");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_053");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_054");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_055");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_056");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_057");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_058");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_059");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_060");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_061");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_062");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_063");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_064");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_065");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_066");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_067");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_068");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_069");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_070");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_071");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_072");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_073");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_074");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_075");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_076");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_077");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_078");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_079");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_080");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_081");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_082");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_083");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_084");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_085");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_086");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_087");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_088");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_089");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_090");

            migrationBuilder.DeleteData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_091");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_09");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_10");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_11");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_12");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_13");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_14");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_15");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_16");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_17");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_18");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_19");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_20");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_21");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_22");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_23");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_24");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_25");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_26");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_27");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_28");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_29");

            migrationBuilder.DeleteData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_30");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_alcohol");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_chicken");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_fruit");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_hotpot");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_juice");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_regional");

            migrationBuilder.DeleteData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_vegetarian");

            migrationBuilder.DropColumn(
                name: "customer_phone_number",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "discount_amount",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "promotion_code",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "promotion_id",
                table: "orders");

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_appetizer",
                column: "name",
                value: "Khai vi");

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_dessert",
                columns: new[] { "display_order", "name" },
                values: new object[] { 60, "Trang mieng" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_drink",
                columns: new[] { "display_order", "name" },
                values: new object[] { 50, "Do uong" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_main",
                columns: new[] { "display_order", "name" },
                values: new object[] { 20, "Mon chinh" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_noodle",
                columns: new[] { "display_order", "name" },
                values: new object[] { 30, "Pho va bun" });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_seafood",
                column: "name",
                value: "Hai san");

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_001",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_main", "Ga chien gion, com thom, dua chua.", "https://example.com/images/com-ga-xoi-mo.jpg", "Com ga xoi mo", 45000m, new[] { "pho bien", "mon chinh", "signature" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_002",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_main", "Suon uop mat ong nuong than, an kem rau chua.", "https://example.com/images/com-suon-nuong.jpg", "Com suon nuong", 52000m, new[] { "pho bien", "nuong" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_003",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Pho bo nuoc dung trong, bo tai mem, rau thom.", "https://example.com/images/pho-bo-tai.jpg", "Pho bo tai", 55000m, new[] { "nong", "pho", "bo" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_004",
                columns: new[] { "category_id", "description", "image_url", "is_available", "name", "price", "tags" },
                values: new object[] { "cat_noodle", "Nuoc dung dam vi sa te, bo, cha cua va rau song.", "https://example.com/images/bun-bo-hue.jpg", false, "Bun bo Hue", 60000m, new[] { "cay", "het hang", "unavailable-demo" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_005",
                columns: new[] { "description", "image_url", "name", "price", "tags" },
                values: new object[] { "Goi cuon tuoi kem nuoc cham dau phong.", "https://example.com/images/goi-cuon.jpg", "Goi cuon tom thit", 39000m, new[] { "fresh", "light" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_006",
                columns: new[] { "description", "image_url", "name", "price", "tags" },
                values: new object[] { "Cha gio gion nhan hai san, sot mayo cay.", "https://example.com/images/cha-gio-hai-san.jpg", "Cha gio hai san", 42000m, new[] { "chien gion", "seafood" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_007",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_seafood", "Tom tuoi rang muoi ot, an kem rau thom.", "https://example.com/images/tom-rang-muoi.jpg", "Tom rang muoi", 185000m, new[] { "seafood", "share" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_008",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_seafood", "Lau Thai chua cay voi tom, muc, ca va rau tuoi.", "https://example.com/images/lau-thai-hai-san.jpg", "Lau Thai hai san", 345000m, new[] { "spicy", "seafood", "share" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_009",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_drink", "Tra dao mat lanh voi cam vang va sa tuoi.", "https://example.com/images/tra-dao-cam-sa.jpg", "Tra dao cam sa", 55000m, new[] { "drink", "fresh" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_010",
                columns: new[] { "category_id", "description", "image_url", "is_available", "name", "price", "tags" },
                values: new object[] { "cat_drink", "Ca phe rang xay pha phin, sua dac va da vien.", "https://example.com/images/ca-phe-sua-da.jpg", false, "Ca phe sua da", 45000m, new[] { "drink", "coffee", "unavailable-demo" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_011",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_dessert", "Khuc bach beo nhe, vai, hanh nhan va siro duong phen.", "https://example.com/images/che-khuc-bach.jpg", "Che khuc bach", 55000m, new[] { "sweet", "cool" } });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_012",
                columns: new[] { "category_id", "description", "image_url", "name", "price", "tags" },
                values: new object[] { "cat_dessert", "Banh flan min, caramel thom, dung lanh.", "https://example.com/images/banh-flan.jpg", "Banh flan caramel", 35000m, new[] { "sweet", "classic" } });
        }
    }
}
