#nullable enable

using System;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class OrderItem
{
    public string Id { get; set; } = string.Empty;

    public string OrderId { get; set; } = string.Empty;

    public Order? Order { get; set; }

    public string MenuItemId { get; set; } = string.Empty;

    public MenuItem? MenuItem { get; set; }

    public string MenuItemName { get; set; } = string.Empty;

    public decimal UnitPrice { get; set; }

    public int Quantity { get; set; }

    public string? Note { get; set; }

    public OrderItemStatus Status { get; set; } = OrderItemStatus.Pending;

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
