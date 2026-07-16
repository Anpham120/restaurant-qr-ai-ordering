namespace RestaurantQrAiOrdering.Api.Tables;

public sealed record TableResponse(
    string TableCode,
    string DisplayName,
    bool IsActive,
    string? QrToken,
    string CustomerPath);

public sealed record TableQrResponse(
    string TableCode,
    string DisplayName,
    string QrToken,
    string CustomerPath);

public sealed record OpenTableSessionRequest(
    string? QrToken,
    string? TableCode);

public sealed record TableSessionResponse(
    string SessionId,
    string OrderType,
    string Status,
    string? TableCode,
    string? TableDisplayName,
    string? QrToken,
    string CustomerPath,
    DateTimeOffset OpenedAt,
    DateTimeOffset ExpiresAt,
    DateTimeOffset? ClosedAt,
    bool IsExpired);

public sealed record TableListResponse(
    IReadOnlyList<TableResponse> Items,
    int Total);

public sealed record AdminTableSessionSummaryResponse(
    string SessionId,
    string TableCode,
    string? TableDisplayName,
    string Status,
    DateTimeOffset OpenedAt,
    DateTimeOffset ExpiresAt,
    DateTimeOffset? ClosedAt,
    bool IsExpired,
    int ActiveOrderCount);

public sealed record AdminTableSessionListResponse(
    IReadOnlyList<AdminTableSessionSummaryResponse> Items,
    int Total);
