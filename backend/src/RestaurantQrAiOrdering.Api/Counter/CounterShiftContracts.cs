namespace RestaurantQrAiOrdering.Api.Counter;

public sealed record OpenCounterShiftRequest(decimal OpeningCashBalance);

public sealed record CloseCounterShiftRequest(decimal ActualCashTotal, string? CloseNote);

public sealed record CounterShiftSummaryResponse(
    string ShiftId,
    string Status,
    decimal OpeningCashBalance,
    decimal ExpectedCashTotal,
    decimal? ActualCashTotal,
    decimal? CashVariance,
    string OpenedByName,
    string? ClosedByName,
    DateTimeOffset OpenedAt,
    DateTimeOffset? ClosedAt);

public sealed record CounterShiftListResponse(IReadOnlyList<CounterShiftSummaryResponse> Items);

public sealed record RecordCounterAdjustmentRequest(
    decimal Amount,
    string ReasonCode,
    string? Note);
