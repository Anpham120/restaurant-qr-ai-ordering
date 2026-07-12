using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class SupportsTableSessionSettlement : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AlterColumn<string>(
                name: "order_id",
                table: "payments",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true,
                oldClrType: typeof(string),
                oldType: "character varying(50)",
                oldMaxLength: 50);

            migrationBuilder.AddColumn<string>(
                name: "table_invoice_id",
                table: "payments",
                type: "character varying(50)",
                maxLength: 50,
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_payments_table_invoice_id",
                table: "payments",
                column: "table_invoice_id",
                unique: true);

            migrationBuilder.AddCheckConstraint(
                name: "CK_payments_single_target",
                table: "payments",
                sql: "(order_id IS NULL) <> (table_invoice_id IS NULL)");

            migrationBuilder.AddForeignKey(
                name: "FK_payments_table_invoices_table_invoice_id",
                table: "payments",
                column: "table_invoice_id",
                principalTable: "table_invoices",
                principalColumn: "id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_payments_table_invoices_table_invoice_id",
                table: "payments");

            migrationBuilder.DropIndex(
                name: "IX_payments_table_invoice_id",
                table: "payments");

            migrationBuilder.DropCheckConstraint(
                name: "CK_payments_single_target",
                table: "payments");

            migrationBuilder.Sql(
                "DELETE FROM payments WHERE table_invoice_id IS NOT NULL");

            migrationBuilder.DropColumn(
                name: "table_invoice_id",
                table: "payments");

            migrationBuilder.AlterColumn<string>(
                name: "order_id",
                table: "payments",
                type: "character varying(50)",
                maxLength: 50,
                nullable: false,
                defaultValue: "",
                oldClrType: typeof(string),
                oldType: "character varying(50)",
                oldMaxLength: 50,
                oldNullable: true);
        }
    }
}
