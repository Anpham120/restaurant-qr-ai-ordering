namespace RestaurantQrAiOrdering.Api.Tables;

public sealed record TableResponse(
    string TableCode,
    string DisplayName,
    bool IsActive);

public sealed record AdminTableResponse(
    string TableCode,
    string DisplayName,
    bool IsActive,
    string? QrToken,
    string CustomerPath);

public sealed record TableQrResponse(
    string TableCode,
    string DisplayName);

public sealed record OpenTableSessionRequest(
    string? QrToken,
    string? TableCode);

public sealed record TableSessionResponse(
    string SessionId,
    string OrderType,
    string Status,
    string? TableCode,
    string? TableDisplayName,
    DateTimeOffset OpenedAt,
    DateTimeOffset ExpiresAt,
    DateTimeOffset? ClosedAt,
    bool IsExpired);

public sealed record OpenTableSessionResponse(
    string SessionId,
    string OrderType,
    string Status,
    string? TableCode,
    string? TableDisplayName,
    DateTimeOffset OpenedAt,
    DateTimeOffset ExpiresAt,
    DateTimeOffset? ClosedAt,
    bool IsExpired,
    string TableSessionToken);

public sealed record TableListResponse(
    IReadOnlyList<AdminTableResponse> Items,
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
