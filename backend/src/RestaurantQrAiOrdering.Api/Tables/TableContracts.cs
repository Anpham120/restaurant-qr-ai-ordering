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
