using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations;

/// <inheritdoc />
public partial class AddsChatTypedSessionState : Migration
{
    /// <inheritdoc />
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<string>(
            name: "constraints_json",
            table: "chat_sessions",
            type: "jsonb",
            nullable: true);

        migrationBuilder.AddColumn<string>(
            name: "memory_version",
            table: "chat_sessions",
            type: "character varying(50)",
            maxLength: 50,
            nullable: false,
            defaultValue: "v1");

        migrationBuilder.AddColumn<string>(
            name: "referenced_menu_item_ids_json",
            table: "chat_sessions",
            type: "jsonb",
            nullable: true);
    }

    /// <inheritdoc />
    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropColumn(
            name: "constraints_json",
            table: "chat_sessions");

        migrationBuilder.DropColumn(
            name: "memory_version",
            table: "chat_sessions");

        migrationBuilder.DropColumn(
            name: "referenced_menu_item_ids_json",
            table: "chat_sessions");
    }
}
