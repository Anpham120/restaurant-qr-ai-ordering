#nullable enable

using System;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

// Append-only audit trail of an order's lifecycle: every status transition and every
// payment confirm/fail, with the actor who caused it. Replaces the previously
// synthesized single-status event list on the order response.
public class OrderStatusHistory
{
    public string Id { get; set; } = string.Empty;

    public string OrderId { get; set; } = string.Empty;

    public Order? Order { get; set; }

    public OrderStatus? FromStatus { get; set; }

    public OrderStatus ToStatus { get; set; }

    public OrderStatusChangeSource Source { get; set; }

    public string? ChangedByUserId { get; set; }

    public string? ChangedByRole { get; set; }

    public string? Note { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}
