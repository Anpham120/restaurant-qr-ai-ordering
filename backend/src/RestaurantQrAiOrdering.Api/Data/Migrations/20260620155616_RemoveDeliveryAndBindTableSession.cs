using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveDeliveryAndBindTableSession : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "delivery_address",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "delivery_note",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "delivery_phone_number",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "delivery_recipient_name",
                table: "orders");

            migrationBuilder.AddColumn<string>(
                name: "table_session_id",
                table: "orders",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.CreateTable(
                name: "order_status_history",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    order_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    from_status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    to_status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    source = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    changed_by_user_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    changed_by_role = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    note = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_order_status_history", x => x.id);
                    table.ForeignKey(
                        name: "FK_order_status_history_orders_order_id",
                        column: x => x.order_id,
                        principalTable: "orders",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_orders_table_session_id",
                table: "orders",
                column: "table_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_order_status_history_created_at",
                table: "order_status_history",
                column: "created_at");

            migrationBuilder.CreateIndex(
                name: "IX_order_status_history_order_id",
                table: "order_status_history",
                column: "order_id");

            migrationBuilder.AddForeignKey(
                name: "FK_orders_table_sessions_table_session_id",
                table: "orders",
                column: "table_session_id",
                principalTable: "table_sessions",
                principalColumn: "id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_orders_table_sessions_table_session_id",
                table: "orders");

            migrationBuilder.DropTable(
                name: "order_status_history");

            migrationBuilder.DropIndex(
                name: "IX_orders_table_session_id",
                table: "orders");

            migrationBuilder.DropColumn(
                name: "table_session_id",
                table: "orders");

            migrationBuilder.AddColumn<string>(
                name: "delivery_address",
                table: "orders",
                type: "character varying(500)",
                maxLength: 500,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "delivery_note",
                table: "orders",
                type: "character varying(500)",
                maxLength: 500,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "delivery_phone_number",
                table: "orders",
                type: "character varying(20)",
                maxLength: 20,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "delivery_recipient_name",
                table: "orders",
                type: "character varying(200)",
                maxLength: 200,
                nullable: true);
        }
    }
}
