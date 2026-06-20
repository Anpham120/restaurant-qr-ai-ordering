using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddOrderAccessToken : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "customer_access_token",
                table: "orders",
                type: "character varying(64)",
                maxLength: 64,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "customer_access_token",
                table: "orders");
        }
    }
}
