using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class RemoveSeededUsers : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DeleteData(
                table: "users",
                keyColumn: "id",
                keyValue: "usr_admin");

            migrationBuilder.DeleteData(
                table: "users",
                keyColumn: "id",
                keyValue: "usr_customer_seed");

            migrationBuilder.DeleteData(
                table: "users",
                keyColumn: "id",
                keyValue: "usr_kitchen");

            migrationBuilder.DeleteData(
                table: "users",
                keyColumn: "id",
                keyValue: "usr_staff");

            // Reconciles pre-existing model drift: the Order.MockDeliveryFee property was
            // removed from the entity earlier without a migration, leaving an orphaned column.
            migrationBuilder.DropColumn(
                name: "mock_delivery_fee",
                table: "orders");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<decimal>(
                name: "mock_delivery_fee",
                table: "orders",
                type: "numeric(18,2)",
                precision: 18,
                scale: 2,
                nullable: false,
                defaultValue: 0m);

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
        }
    }
}
