#nullable enable

using System;

namespace RestaurantQrAiOrdering.Entities;

/// <summary>
/// Server-side cart line scoped to a table session (shared across devices).
/// </summary>
public class TableSessionCartItem
{
    public string Id { get; set; } = string.Empty;

    public string TableSessionId { get; set; } = string.Empty;

    public TableSession? TableSession { get; set; }

    public string MenuItemId { get; set; } = string.Empty;

    public MenuItem? MenuItem { get; set; }

    public int Quantity { get; set; }

    public string? Note { get; set; }

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
