#nullable enable

using System;
using System.Collections.Generic;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class Order
{
    public string Id { get; set; } = string.Empty;

    public string OrderCode { get; set; } = string.Empty;

    // Unguessable per-order token issued at creation. Customers present it (X-Order-Token)
    // to read their own order/payment so sequential order codes can't be enumerated.
    public string? CustomerAccessToken { get; set; }

    public OrderType OrderType { get; set; }

    public OrderStatus Status { get; set; } = OrderStatus.Draft;

    public string? RestaurantTableId { get; set; }

    public RestaurantTable? RestaurantTable { get; set; }

    public string? TableCode { get; set; }

    // Open dine-in session this order belongs to; closed when the table's last active order completes.
    // Dine-in orders always have a session; legacy rows may have null.
    public string? TableSessionId { get; set; }

    public TableSession? TableSession { get; set; }

    public string? PickupCustomerName { get; set; }

    public string? PickupCustomerPhoneNumber { get; set; }

    public DateTimeOffset? PickupRequestedAt { get; set; }

    public decimal SubtotalAmount { get; set; }

    public decimal DiscountAmount { get; set; }

    public decimal TotalAmount { get; set; }

    public string? PromotionId { get; set; }

    public Promotion? Promotion { get; set; }

    public string? PromotionCode { get; set; }

    public string? CustomerPhoneNumber { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    public ICollection<OrderItem> OrderItems { get; set; } = new List<OrderItem>();

    public Payment? Payment { get; set; }

    public ICollection<OrderStatusHistory> StatusHistory { get; set; } = new List<OrderStatusHistory>();
}
