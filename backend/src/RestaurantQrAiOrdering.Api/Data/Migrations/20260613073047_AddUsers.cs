using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

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
                    email = table.Column<string>(type: "character varying(160)", maxLength: 160, nullable: false),
                    full_name = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: false),
                    password_hash = table.Column<string>(type: "character varying(512)", maxLength: 512, nullable: false),
                    role = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.id);
                });

            var createdAt = new DateTimeOffset(new DateTime(2026, 6, 13, 7, 30, 44, DateTimeKind.Unspecified), TimeSpan.Zero);

            migrationBuilder.InsertData(
                table: "users",
                columns: new[] { "id", "created_at", "email", "full_name", "password_hash", "role", "updated_at" },
                values: new object[,]
                {
                    { "usr_admin", createdAt, "admin@restaurant.local", "Quan Tri Vien", "v1.100000.2FZk9K5Yru/klQtpkjDGJQ==.9gGU3IU+rG4JGkMgsvORd0Cqmsykp5xeaZCAQ95S4cM=", "Admin", createdAt },
                    { "usr_customer_seed", createdAt, "customer@restaurant.local", "Khach Hang Mau", "v1.100000.uSV+rreaBwKjA3WUTqZD8Q==.8pVVHQiXquhg7U1O6soESBvdr6tDM+Ibi3vwe0uHXaY=", "Customer", createdAt },
                    { "usr_kitchen", createdAt, "kitchen@restaurant.local", "Dau Bep", "v1.100000.u76cG06YBTjLue+rOz5B1w==.vNcRBLo2BXctMwTDqX3/p55jgxk6Dfki+Jx7CkRKSBc=", "Kitchen", createdAt },
                    { "usr_staff", createdAt, "staff@restaurant.local", "Nhan Vien Thu Ngan", "v1.100000.c9UhEBod8mtmPQLeP2nnWQ==.an2Aa1goSjTZ8uS8joy2I3W11iWwNhiOsg4YreIn9mU=", "Staff", createdAt }
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
        }
    }
}
