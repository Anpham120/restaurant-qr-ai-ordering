namespace RestaurantQrAiOrdering.Api.Cart;

public sealed record CartItemResponse(
    string Id,
    string MenuItemId,
    string Name,
    string Description,
    decimal Price,
    string CategoryId,
    string CategoryName,
    string? ImageUrl,
    bool IsAvailable,
    int Quantity,
    string? Note,
    decimal LineTotal,
    DateTimeOffset UpdatedAt);

public sealed record CartResponse(
    string TableSessionId,
    IReadOnlyList<CartItemResponse> Items,
    int ItemCount,
    decimal Subtotal,
    DateTimeOffset UpdatedAt);

public sealed record UpdateCartItemRequest(
    string? MenuItemId,
    int Delta,
    string? Note = null);
