using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "categories",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    display_order = table.Column<int>(type: "integer", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_categories", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "restaurant_tables",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    table_code = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    display_name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    qr_token = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_restaurant_tables", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "menu_items",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    category_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    description = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: false),
                    price = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    image_url = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    is_available = table.Column<bool>(type: "boolean", nullable: false),
                    tags = table.Column<string[]>(type: "text[]", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_menu_items", x => x.id);
                    table.ForeignKey(
                        name: "FK_menu_items_categories_category_id",
                        column: x => x.category_id,
                        principalTable: "categories",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "orders",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    order_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    order_type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    restaurant_table_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    table_code = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    pickup_customer_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    pickup_customer_phone = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    pickup_requested_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    delivery_recipient_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    delivery_phone_number = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    delivery_address = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    delivery_note = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    mock_delivery_fee = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    subtotal_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    total_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_orders", x => x.id);
                    table.ForeignKey(
                        name: "FK_orders_restaurant_tables_restaurant_table_id",
                        column: x => x.restaurant_table_id,
                        principalTable: "restaurant_tables",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "knowledge_entries",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    title = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    content = table.Column<string>(type: "text", nullable: false),
                    source_type = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    menu_item_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    tags = table.Column<string[]>(type: "text[]", nullable: false),
                    embedding = table.Column<string>(type: "jsonb", nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_knowledge_entries", x => x.id);
                    table.ForeignKey(
                        name: "FK_knowledge_entries_menu_items_menu_item_id",
                        column: x => x.menu_item_id,
                        principalTable: "menu_items",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "chat_sessions",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    restaurant_table_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    table_code = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    order_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    is_closed = table.Column<bool>(type: "boolean", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_chat_sessions", x => x.id);
                    table.ForeignKey(
                        name: "FK_chat_sessions_orders_order_id",
                        column: x => x.order_id,
                        principalTable: "orders",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_chat_sessions_restaurant_tables_restaurant_table_id",
                        column: x => x.restaurant_table_id,
                        principalTable: "restaurant_tables",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "order_items",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    order_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    menu_item_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    menu_item_name = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    unit_price = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    quantity = table.Column<int>(type: "integer", nullable: false),
                    note = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_order_items", x => x.id);
                    table.ForeignKey(
                        name: "FK_order_items_menu_items_menu_item_id",
                        column: x => x.menu_item_id,
                        principalTable: "menu_items",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_order_items_orders_order_id",
                        column: x => x.order_id,
                        principalTable: "orders",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "payments",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    order_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    method = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    provider_transaction_id = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    paid_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_payments", x => x.id);
                    table.ForeignKey(
                        name: "FK_payments_orders_order_id",
                        column: x => x.order_id,
                        principalTable: "orders",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "chat_messages",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    chat_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    role = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    content = table.Column<string>(type: "text", nullable: false),
                    suggested_cart_actions_json = table.Column<string>(type: "jsonb", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_chat_messages", x => x.id);
                    table.ForeignKey(
                        name: "FK_chat_messages_chat_sessions_chat_session_id",
                        column: x => x.chat_session_id,
                        principalTable: "chat_sessions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.InsertData(
                table: "categories",
                columns: new[] { "id", "created_at", "display_order", "is_active", "name", "updated_at" },
                values: new object[,]
                {
                    { "cat_appetizer", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), 10, true, "Khai vi", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), 60, true, "Trang mieng", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), 50, true, "Do uong", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), 20, true, "Mon chinh", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_noodle", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), 30, true, "Pho va bun", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), 40, true, "Hai san", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.InsertData(
                table: "restaurant_tables",
                columns: new[] { "id", "created_at", "display_name", "is_active", "qr_token", "table_code", "updated_at" },
                values: new object[,]
                {
                    { "tbl_01", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 01", true, "qr-demo-t01", "T01", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_02", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 02", true, "qr-demo-t02", "T02", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_03", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 03", true, "qr-demo-t03", "T03", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_04", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 04", true, "qr-demo-t04", "T04", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_05", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 05", true, "qr-demo-t05", "T05", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_06", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 06", true, "qr-demo-t06", "T06", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_07", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 07", true, "qr-demo-t07", "T07", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "tbl_08", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), "Ban 08", true, "qr-demo-t08", "T08", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.InsertData(
                table: "menu_items",
                columns: new[] { "id", "category_id", "created_at", "description", "image_url", "is_available", "name", "price", "tags", "updated_at" },
                values: new object[,]
                {
                    { "m_001", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Ga chien gion, com thom, dua chua.", "https://example.com/images/com-ga-xoi-mo.jpg", true, "Com ga xoi mo", 45000m, new[] { "pho bien", "mon chinh", "signature" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_002", "cat_main", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Suon uop mat ong nuong than, an kem rau chua.", "https://example.com/images/com-suon-nuong.jpg", true, "Com suon nuong", 52000m, new[] { "pho bien", "nuong" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_003", "cat_noodle", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Pho bo nuoc dung trong, bo tai mem, rau thom.", "https://example.com/images/pho-bo-tai.jpg", true, "Pho bo tai", 55000m, new[] { "nong", "pho", "bo" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_004", "cat_noodle", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Nuoc dung dam vi sa te, bo, cha cua va rau song.", "https://example.com/images/bun-bo-hue.jpg", false, "Bun bo Hue", 60000m, new[] { "cay", "het hang", "unavailable-demo" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_005", "cat_appetizer", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Goi cuon tuoi kem nuoc cham dau phong.", "https://example.com/images/goi-cuon.jpg", true, "Goi cuon tom thit", 39000m, new[] { "fresh", "light" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_006", "cat_appetizer", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Cha gio gion nhan hai san, sot mayo cay.", "https://example.com/images/cha-gio-hai-san.jpg", true, "Cha gio hai san", 42000m, new[] { "chien gion", "seafood" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_007", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Tom tuoi rang muoi ot, an kem rau thom.", "https://example.com/images/tom-rang-muoi.jpg", true, "Tom rang muoi", 185000m, new[] { "seafood", "share" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_008", "cat_seafood", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Lau Thai chua cay voi tom, muc, ca va rau tuoi.", "https://example.com/images/lau-thai-hai-san.jpg", true, "Lau Thai hai san", 345000m, new[] { "spicy", "seafood", "share" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_009", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Tra dao mat lanh voi cam vang va sa tuoi.", "https://example.com/images/tra-dao-cam-sa.jpg", true, "Tra dao cam sa", 55000m, new[] { "drink", "fresh" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_010", "cat_drink", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Ca phe rang xay pha phin, sua dac va da vien.", "https://example.com/images/ca-phe-sua-da.jpg", false, "Ca phe sua da", 45000m, new[] { "drink", "coffee", "unavailable-demo" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_011", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Khuc bach beo nhe, vai, hanh nhan va siro duong phen.", "https://example.com/images/che-khuc-bach.jpg", true, "Che khuc bach", 55000m, new[] { "sweet", "cool" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "m_012", "cat_dessert", new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), "Banh flan min, caramel thom, dung lanh.", "https://example.com/images/banh-flan.jpg", true, "Banh flan caramel", 35000m, new[] { "sweet", "classic" }, new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.CreateIndex(
                name: "IX_categories_display_order",
                table: "categories",
                column: "display_order");

            migrationBuilder.CreateIndex(
                name: "IX_categories_is_active",
                table: "categories",
                column: "is_active");

            migrationBuilder.CreateIndex(
                name: "IX_chat_messages_chat_session_id",
                table: "chat_messages",
                column: "chat_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_chat_sessions_is_closed",
                table: "chat_sessions",
                column: "is_closed");

            migrationBuilder.CreateIndex(
                name: "IX_chat_sessions_order_id",
                table: "chat_sessions",
                column: "order_id");

            migrationBuilder.CreateIndex(
                name: "IX_chat_sessions_restaurant_table_id",
                table: "chat_sessions",
                column: "restaurant_table_id");

            migrationBuilder.CreateIndex(
                name: "IX_knowledge_entries_is_active",
                table: "knowledge_entries",
                column: "is_active");

            migrationBuilder.CreateIndex(
                name: "IX_knowledge_entries_menu_item_id",
                table: "knowledge_entries",
                column: "menu_item_id");

            migrationBuilder.CreateIndex(
                name: "IX_menu_items_category_id",
                table: "menu_items",
                column: "category_id");

            migrationBuilder.CreateIndex(
                name: "IX_menu_items_is_available",
                table: "menu_items",
                column: "is_available");

            migrationBuilder.CreateIndex(
                name: "IX_order_items_menu_item_id",
                table: "order_items",
                column: "menu_item_id");

            migrationBuilder.CreateIndex(
                name: "IX_order_items_order_id",
                table: "order_items",
                column: "order_id");

            migrationBuilder.CreateIndex(
                name: "IX_orders_created_at",
                table: "orders",
                column: "created_at");

            migrationBuilder.CreateIndex(
                name: "IX_orders_order_code",
                table: "orders",
                column: "order_code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_orders_restaurant_table_id",
                table: "orders",
                column: "restaurant_table_id");

            migrationBuilder.CreateIndex(
                name: "IX_orders_status",
                table: "orders",
                column: "status");

            migrationBuilder.CreateIndex(
                name: "IX_payments_order_id",
                table: "payments",
                column: "order_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_payments_status",
                table: "payments",
                column: "status");

            migrationBuilder.CreateIndex(
                name: "IX_restaurant_tables_is_active",
                table: "restaurant_tables",
                column: "is_active");

            migrationBuilder.CreateIndex(
                name: "IX_restaurant_tables_qr_token",
                table: "restaurant_tables",
                column: "qr_token",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_restaurant_tables_table_code",
                table: "restaurant_tables",
                column: "table_code",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "chat_messages");

            migrationBuilder.DropTable(
                name: "knowledge_entries");

            migrationBuilder.DropTable(
                name: "order_items");

            migrationBuilder.DropTable(
                name: "payments");

            migrationBuilder.DropTable(
                name: "chat_sessions");

            migrationBuilder.DropTable(
                name: "menu_items");

            migrationBuilder.DropTable(
                name: "orders");

            migrationBuilder.DropTable(
                name: "categories");

            migrationBuilder.DropTable(
                name: "restaurant_tables");
        }
    }
}
