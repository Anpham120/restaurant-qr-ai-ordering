using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    public partial class AddsCounterShifts : Migration
    {
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "counter_shifts",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    opened_by_user_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    closed_by_user_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    opening_cash_balance = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    expected_cash_total = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    actual_cash_total = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: true),
                    cash_variance = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: true),
                    close_note = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    opened_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    closed_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_counter_shifts", x => x.id);
                    table.ForeignKey(
                        name: "FK_counter_shifts_users_closed_by_user_id",
                        column: x => x.closed_by_user_id,
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_counter_shifts_users_opened_by_user_id",
                        column: x => x.opened_by_user_id,
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "counter_shift_transactions",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    counter_shift_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    amount = table.Column<decimal>(type: "numeric(18,2)", precision: 18, scale: 2, nullable: false),
                    table_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    invoice_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: true),
                    reason_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    note = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    created_by_user_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_counter_shift_transactions", x => x.id);
                    table.ForeignKey(
                        name: "FK_counter_shift_transactions_counter_shifts_counter_shift_id",
                        column: x => x.counter_shift_id,
                        principalTable: "counter_shifts",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_counter_shift_transactions_users_created_by_user_id",
                        column: x => x.created_by_user_id,
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_counter_shift_transactions_counter_shift_id",
                table: "counter_shift_transactions",
                column: "counter_shift_id");

            migrationBuilder.CreateIndex(
                name: "IX_counter_shift_transactions_table_session_id",
                table: "counter_shift_transactions",
                column: "table_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_counter_shifts_closed_by_user_id",
                table: "counter_shifts",
                column: "closed_by_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_counter_shifts_opened_by_user_id",
                table: "counter_shifts",
                column: "opened_by_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_counter_shifts_status",
                table: "counter_shifts",
                column: "status");
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(name: "counter_shift_transactions");
            migrationBuilder.DropTable(name: "counter_shifts");
        }
    }
}
