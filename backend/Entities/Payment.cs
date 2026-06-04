#nullable enable

using System;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class Payment
{
    public string Id { get; set; } = string.Empty;

    public string OrderId { get; set; } = string.Empty;

    public Order? Order { get; set; }

    public PaymentMethod Method { get; set; } = PaymentMethod.COD;

    public PaymentStatus Status { get; set; } = PaymentStatus.Unpaid;

    public decimal Amount { get; set; }

    public string? ProviderTransactionId { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset? PaidAt { get; set; }

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
