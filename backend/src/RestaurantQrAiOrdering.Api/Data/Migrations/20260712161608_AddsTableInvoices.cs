using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddsTableInvoices : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "table_invoices",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    invoice_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    table_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    subtotal_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    discount_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    total_amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    promotion_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    promotion_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    customer_phone_number = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: true),
                    method = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_table_invoices", x => x.id);
                    table.ForeignKey(
                        name: "FK_table_invoices_promotions_promotion_id",
                        column: x => x.promotion_id,
                        principalTable: "promotions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.SetNull);
                    table.ForeignKey(
                        name: "FK_table_invoices_table_sessions_table_session_id",
                        column: x => x.table_session_id,
                        principalTable: "table_sessions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_table_invoices_invoice_code",
                table: "table_invoices",
                column: "invoice_code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_table_invoices_promotion_id",
                table: "table_invoices",
                column: "promotion_id");

            migrationBuilder.CreateIndex(
                name: "IX_table_invoices_status",
                table: "table_invoices",
                column: "status");

            migrationBuilder.CreateIndex(
                name: "IX_table_invoices_table_session_id",
                table: "table_invoices",
                column: "table_session_id",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "table_invoices");
        }
    }
}
