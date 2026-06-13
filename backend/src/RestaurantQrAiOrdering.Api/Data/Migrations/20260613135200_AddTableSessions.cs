using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddTableSessions : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            for (var tableNumber = 1; tableNumber <= 8; tableNumber++)
            {
                migrationBuilder.UpdateData(
                    table: "restaurant_tables",
                    keyColumn: "id",
                    keyValue: $"tbl_{tableNumber:00}",
                    column: "qr_token",
                    value: $"cmc-table-t{tableNumber:00}-qr");
            }

            migrationBuilder.CreateTable(
                name: "table_sessions",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    restaurant_table_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    table_code = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    qr_token = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    order_type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    opened_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    expires_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    closed_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_table_sessions", x => x.id);
                    table.ForeignKey(
                        name: "FK_table_sessions_restaurant_tables_restaurant_table_id",
                        column: x => x.restaurant_table_id,
                        principalTable: "restaurant_tables",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateIndex(
                name: "IX_table_sessions_expires_at",
                table: "table_sessions",
                column: "expires_at");

            migrationBuilder.CreateIndex(
                name: "IX_table_sessions_qr_token",
                table: "table_sessions",
                column: "qr_token");

            migrationBuilder.CreateIndex(
                name: "IX_table_sessions_restaurant_table_id",
                table: "table_sessions",
                column: "restaurant_table_id");

            migrationBuilder.CreateIndex(
                name: "IX_table_sessions_status",
                table: "table_sessions",
                column: "status");

            migrationBuilder.CreateIndex(
                name: "IX_table_sessions_table_code",
                table: "table_sessions",
                column: "table_code");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "table_sessions");

            for (var tableNumber = 1; tableNumber <= 8; tableNumber++)
            {
                migrationBuilder.UpdateData(
                    table: "restaurant_tables",
                    keyColumn: "id",
                    keyValue: $"tbl_{tableNumber:00}",
                    column: "qr_token",
                    value: $"qr-demo-t{tableNumber:00}");
            }
        }
    }
}
