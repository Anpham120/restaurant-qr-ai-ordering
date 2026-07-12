namespace RestaurantQrAiOrdering.Api.Tables;

public sealed record TableInvoiceLineResponse(
    string MenuItemId,
    string Name,
    decimal UnitPrice,
    int Quantity,
    decimal LineTotal);

public sealed record TableInvoiceOrderRoundResponse(
    string OrderCode,
    string Status,
    decimal SubtotalAmount,
    DateTimeOffset CreatedAt);

public sealed record TableInvoiceResponse(
    string TableSessionId,
    string? TableCode,
    string Status,
    decimal SubtotalAmount,
    decimal DiscountAmount,
    decimal TotalAmount,
    string? PromotionCode,
    string? CustomerPhoneNumber,
    string Method,
    IReadOnlyList<TableInvoiceOrderRoundResponse> OrderRounds,
    IReadOnlyList<TableInvoiceLineResponse> Items);
