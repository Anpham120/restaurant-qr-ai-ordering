using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class EnforceSingleActiveTableSession : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                UPDATE table_sessions
                SET status = 'Expired',
                    closed_at = COALESCE(closed_at, NOW()),
                    updated_at = NOW()
                WHERE status = 'Open'
                  AND closed_at IS NULL
                  AND expires_at <= NOW();
                """);

            migrationBuilder.DropIndex(
                name: "IX_table_sessions_restaurant_table_id",
                table: "table_sessions");

            migrationBuilder.CreateIndex(
                name: "UX_table_sessions_active_restaurant_table",
                table: "table_sessions",
                column: "restaurant_table_id",
                unique: true,
                filter: "\"status\" = 'Open' AND \"closed_at\" IS NULL");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "UX_table_sessions_active_restaurant_table",
                table: "table_sessions");

            migrationBuilder.CreateIndex(
                name: "IX_table_sessions_restaurant_table_id",
                table: "table_sessions",
                column: "restaurant_table_id");
        }
    }
}
