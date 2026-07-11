#nullable enable

using System;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class PaymentTransaction
{
    public string Id { get; set; } = string.Empty;

    public string PaymentId { get; set; } = string.Empty;

    public Payment? Payment { get; set; }

    public PaymentMethod Method { get; set; }

    public PaymentStatus Status { get; set; }

    public decimal Amount { get; set; }

    public string Provider { get; set; } = string.Empty;

    public string? ProviderTransactionId { get; set; }

    public string? Note { get; set; }

    // Present for customer payment requests. Staff reconciliation transactions may omit it.
    public string? IdempotencyKey { get; set; }

    public string? RequestFingerprint { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}
