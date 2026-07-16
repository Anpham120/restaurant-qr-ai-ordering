using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddsAiSessionLedgerAndServerCart : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "rolling_summary",
                table: "chat_sessions",
                type: "text",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "chat_feedback",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    chat_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    message_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    rating = table.Column<string>(type: "character varying(10)", maxLength: 10, nullable: false),
                    reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_chat_feedback", x => x.id);
                    table.ForeignKey(
                        name: "FK_chat_feedback_chat_messages_message_id",
                        column: x => x.message_id,
                        principalTable: "chat_messages",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_chat_feedback_chat_sessions_chat_session_id",
                        column: x => x.chat_session_id,
                        principalTable: "chat_sessions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "chat_recommendations",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    chat_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    menu_item_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    status = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    turn_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_chat_recommendations", x => x.id);
                    table.ForeignKey(
                        name: "FK_chat_recommendations_chat_sessions_chat_session_id",
                        column: x => x.chat_session_id,
                        principalTable: "chat_sessions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "chat_session_facts",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    chat_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    kind = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    value = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    source_turn_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    confidence = table.Column<double>(type: "double precision", nullable: false),
                    created_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_chat_session_facts", x => x.id);
                    table.ForeignKey(
                        name: "FK_chat_session_facts_chat_sessions_chat_session_id",
                        column: x => x.chat_session_id,
                        principalTable: "chat_sessions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "menu_item_knowledge",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    menu_item_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    ingredients = table.Column<string>(type: "text", nullable: true),
                    allergens = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    spice_level = table.Column<int>(type: "integer", nullable: false),
                    calories_estimate = table.Column<int>(type: "integer", nullable: true),
                    flavor_profile = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    dietary_tags = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    cooking_method = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    serving_size_people = table.Column<int>(type: "integer", nullable: true),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_menu_item_knowledge", x => x.id);
                    table.ForeignKey(
                        name: "FK_menu_item_knowledge_menu_items_menu_item_id",
                        column: x => x.menu_item_id,
                        principalTable: "menu_items",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "table_session_cart_items",
                columns: table => new
                {
                    id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    table_session_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    menu_item_id = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    quantity = table.Column<int>(type: "integer", nullable: false),
                    note = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    updated_at = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_table_session_cart_items", x => x.id);
                    table.ForeignKey(
                        name: "FK_table_session_cart_items_menu_items_menu_item_id",
                        column: x => x.menu_item_id,
                        principalTable: "menu_items",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_table_session_cart_items_table_sessions_table_session_id",
                        column: x => x.table_session_id,
                        principalTable: "table_sessions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_chat_feedback_chat_session_id",
                table: "chat_feedback",
                column: "chat_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_chat_feedback_message_id",
                table: "chat_feedback",
                column: "message_id");

            migrationBuilder.CreateIndex(
                name: "IX_chat_recommendations_chat_session_id",
                table: "chat_recommendations",
                column: "chat_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_chat_recommendations_chat_session_id_menu_item_id_status",
                table: "chat_recommendations",
                columns: new[] { "chat_session_id", "menu_item_id", "status" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_chat_session_facts_chat_session_id",
                table: "chat_session_facts",
                column: "chat_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_chat_session_facts_chat_session_id_kind_value",
                table: "chat_session_facts",
                columns: new[] { "chat_session_id", "kind", "value" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_menu_item_knowledge_menu_item_id",
                table: "menu_item_knowledge",
                column: "menu_item_id",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_table_session_cart_items_menu_item_id",
                table: "table_session_cart_items",
                column: "menu_item_id");

            migrationBuilder.CreateIndex(
                name: "IX_table_session_cart_items_table_session_id",
                table: "table_session_cart_items",
                column: "table_session_id");

            migrationBuilder.CreateIndex(
                name: "IX_table_session_cart_items_table_session_id_menu_item_id",
                table: "table_session_cart_items",
                columns: new[] { "table_session_id", "menu_item_id" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "chat_feedback");

            migrationBuilder.DropTable(
                name: "chat_recommendations");

            migrationBuilder.DropTable(
                name: "chat_session_facts");

            migrationBuilder.DropTable(
                name: "menu_item_knowledge");

            migrationBuilder.DropTable(
                name: "table_session_cart_items");

            migrationBuilder.DropColumn(
                name: "rolling_summary",
                table: "chat_sessions");
        }
    }
}
