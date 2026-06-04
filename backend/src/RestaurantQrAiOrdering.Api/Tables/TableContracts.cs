namespace RestaurantQrAiOrdering.Api.Tables;

public sealed record TableResponse(
    string TableCode,
    string DisplayName,
    bool IsActive);
