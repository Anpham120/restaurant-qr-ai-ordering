using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddUsers : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "users",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    full_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    email = table.Column<string>(type: "character varying(255)", maxLength: 255, nullable: false),
                    password_hash = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    role = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.id);
                });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_appetizer",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_dessert",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_drink",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_main",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_noodle",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_seafood",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 704, DateTimeKind.Unspecified).AddTicks(8638), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_001",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_002",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_003",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_004",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_005",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_006",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_007",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_008",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_009",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_010",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_011",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_012",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(968), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_01",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_02",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_03",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_04",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_05",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_06",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_07",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_08",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 705, DateTimeKind.Unspecified).AddTicks(4629), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.InsertData(
                table: "users",
                columns: new[] { "id", "created_at", "email", "full_name", "password_hash", "role", "updated_at" },
                values: new object[,]
                {
                    { "usr_admin", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)), "admin@restaurant.local", "Quan Tri Vien", "v1.100000.2FZk9K5Yru/klQtpkjDGJQ==.9gGU3IU+rG4JGkMgsvORd0Cqmsykp5xeaZCAQ95S4cM=", "Admin", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "usr_customer_seed", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)), "customer@restaurant.local", "Khach Hang Mau", "v1.100000.uSV+rreaBwKjA3WUTqZD8Q==.8pVVHQiXquhg7U1O6soESBvdr6tDM+Ibi3vwe0uHXaY=", "Customer", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "usr_kitchen", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)), "kitchen@restaurant.local", "Dau Bep", "v1.100000.u76cG06YBTjLue+rOz5B1w==.vNcRBLo2BXctMwTDqX3/p55jgxk6Dfki+Jx7CkRKSBc=", "Kitchen", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)) },
                    { "usr_staff", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)), "staff@restaurant.local", "Nhan Vien Thu Ngan", "v1.100000.c9UhEBod8mtmPQLeP2nnWQ==.an2Aa1goSjTZ8uS8joy2I3W11iWwNhiOsg4YreIn9mU=", "Staff", new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, 707, DateTimeKind.Unspecified).AddTicks(7962), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.CreateIndex(
                name: "IX_users_email",
                table: "users",
                column: "email",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "users");

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_appetizer",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_dessert",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_drink",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_main",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_noodle",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "categories",
                keyColumn: "id",
                keyValue: "cat_seafood",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(1865), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_001",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_002",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_003",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_004",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_005",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_006",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_007",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_008",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_009",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_010",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_011",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "menu_items",
                keyColumn: "id",
                keyValue: "m_012",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(3524), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_01",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_02",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_03",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_04",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_05",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_06",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_07",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });

            migrationBuilder.UpdateData(
                table: "restaurant_tables",
                keyColumn: "id",
                keyValue: "tbl_08",
                columns: new[] { "created_at", "updated_at" },
                values: new object[] { new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)), new DateTimeOffset(new DateTime(2026, 6, 13, 3, 11, 23, 195, DateTimeKind.Unspecified).AddTicks(5563), new TimeSpan(0, 0, 0, 0, 0)) });
        }
    }
}
