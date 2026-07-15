using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations;

[DbContext(typeof(RestaurantDbContext))]
[Migration("20260715190000_ReconcileLegacyKitchenStatuses")]
public partial class ReconcileLegacyKitchenStatuses : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql(
            """
            WITH target_status AS (
                SELECT
                    order_row.id,
                    order_row.status AS from_status,
                    CASE
                        WHEN BOOL_AND(item.status = 'Served') THEN 'Served'
                        WHEN BOOL_AND(item.status IN ('Ready', 'Served')) THEN 'Ready'
                        WHEN order_row.status IN ('Placed', 'Confirmed')
                            AND BOOL_OR(item.status IN ('Preparing', 'Ready', 'Served')) THEN 'Preparing'
                        ELSE order_row.status
                    END AS to_status
                FROM orders AS order_row
                INNER JOIN order_items AS item ON item.order_id = order_row.id
                WHERE order_row.status IN ('Placed', 'Confirmed', 'Preparing', 'Ready')
                    AND item.status <> 'Cancelled'
                GROUP BY order_row.id, order_row.status
            ),
            changed_status AS (
                SELECT id, from_status, to_status
                FROM target_status
                WHERE from_status <> to_status
            ),
            updated_order AS (
                UPDATE orders AS order_row
                SET status = changed_status.to_status,
                    updated_at = NOW()
                FROM changed_status
                WHERE order_row.id = changed_status.id
                RETURNING
                    order_row.id,
                    changed_status.from_status,
                    changed_status.to_status,
                    order_row.updated_at
            )
            INSERT INTO order_status_history (
                id,
                order_id,
                from_status,
                to_status,
                source,
                changed_by_user_id,
                changed_by_role,
                note,
                created_at)
            SELECT
                CONCAT('osh_', MD5(id || ':' || from_status || ':' || to_status)),
                id,
                from_status,
                to_status,
                'Status',
                NULL,
                NULL,
                'Reconciled legacy Kitchen aggregate status from item statuses.',
                updated_at
            FROM updated_order;
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        // Data reconciliation is intentionally irreversible.
    }
}
