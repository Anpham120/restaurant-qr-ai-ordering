#nullable enable

using System;
using System.Collections.Generic;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class Order
{
    public string Id { get; set; } = string.Empty;

    public string OrderCode { get; set; } = string.Empty;

    public OrderType OrderType { get; set; }

    public OrderStatus Status { get; set; } = OrderStatus.Draft;

    public string? RestaurantTableId { get; set; }

    public RestaurantTable? RestaurantTable { get; set; }

    public string? TableCode { get; set; }

    public string? PickupCustomerName { get; set; }

    public string? PickupCustomerPhoneNumber { get; set; }

    public DateTimeOffset? PickupRequestedAt { get; set; }

    public string? DeliveryRecipientName { get; set; }

    public string? DeliveryPhoneNumber { get; set; }

    public string? DeliveryAddress { get; set; }

    public string? DeliveryNote { get; set; }

    public decimal MockDeliveryFee { get; set; }

    public decimal SubtotalAmount { get; set; }

    public decimal TotalAmount { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    public ICollection<OrderItem> OrderItems { get; set; } = new List<OrderItem>();

    public Payment? Payment { get; set; }
}
