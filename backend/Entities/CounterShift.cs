#nullable enable

using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class CounterShift
{
    public string Id { get; set; } = string.Empty;

    public string OpenedByUserId { get; set; } = string.Empty;

    public User? OpenedByUser { get; set; }

    public string? ClosedByUserId { get; set; }

    public User? ClosedByUser { get; set; }

    public CounterShiftStatus Status { get; set; } = CounterShiftStatus.Open;

    public decimal OpeningCashBalance { get; set; }

    public decimal ExpectedCashTotal { get; set; }

    public decimal? ActualCashTotal { get; set; }

    public decimal? CashVariance { get; set; }

    public string? CloseNote { get; set; }

    public DateTimeOffset OpenedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset? ClosedAt { get; set; }

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    public ICollection<CounterShiftTransaction> Transactions { get; set; } = [];
}
