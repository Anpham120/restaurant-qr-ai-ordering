#nullable enable

using System;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class TableInvoice
{
    public string Id { get; set; } = string.Empty;

    public string InvoiceCode { get; set; } = string.Empty;

    public string TableSessionId { get; set; } = string.Empty;

    public TableSession? TableSession { get; set; }

    public PaymentStatus Status { get; set; } = PaymentStatus.NotRequested;

    public decimal SubtotalAmount { get; set; }

    public decimal DiscountAmount { get; set; }

    public decimal TotalAmount { get; set; }

    public string? PromotionId { get; set; }

    public Promotion? Promotion { get; set; }

    public string? PromotionCode { get; set; }

    public string? CustomerPhoneNumber { get; set; }

    public PaymentMethod Method { get; set; } = PaymentMethod.Unselected;

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
