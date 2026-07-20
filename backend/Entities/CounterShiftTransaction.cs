#nullable enable

using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class CounterShiftTransaction
{
    public string Id { get; set; } = string.Empty;

    public string CounterShiftId { get; set; } = string.Empty;

    public CounterShift? CounterShift { get; set; }

    public CounterTransactionType Type { get; set; }

    public decimal Amount { get; set; }

    public string? TableSessionId { get; set; }

    public string? InvoiceCode { get; set; }

    public string? ReasonCode { get; set; }

    public string? Note { get; set; }

    public string CreatedByUserId { get; set; } = string.Empty;

    public User? CreatedByUser { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}
