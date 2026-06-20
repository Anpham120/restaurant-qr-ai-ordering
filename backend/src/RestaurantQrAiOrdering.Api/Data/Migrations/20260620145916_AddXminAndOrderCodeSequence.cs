using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddXminAndOrderCodeSequence : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // Backing sequence for human-facing order codes (ORD-1001, 1002, ...).
            // Atomic nextval replaces the Count()+1 generation that could race to a
            // duplicate code under concurrent order creation.
            migrationBuilder.CreateSequence(
                name: "orders_order_code_seq",
                startValue: 1001L);

            // NOTE: Order/Payment optimistic concurrency maps the Postgres xmin *system*
            // column, which already exists on every table. EF scaffolds AddColumn("xmin",
            // type: "xid") here, but applying it fails ("conflicts with a system column"),
            // so the generated column DDL is intentionally removed. The model snapshot
            // still records xmin, so runtime concurrency checks work and no spurious diff
            // surfaces in later migrations.
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropSequence(
                name: "orders_order_code_seq");
        }
    }
}
