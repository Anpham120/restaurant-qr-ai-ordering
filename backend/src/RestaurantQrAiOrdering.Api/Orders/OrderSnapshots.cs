namespace RestaurantQrAiOrdering.Api.Orders;

public sealed record OrderSnapshot(
    string OrderId,
    string OrderCode,
    string OrderType,
    string? TableCode,
    string? TableSessionId,
    string Status,
    string PaymentStatus,
    string PaymentMethod,
    decimal SubtotalAmount,
    decimal DiscountAmount,
    decimal TotalAmount,
    string? PromotionCode,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<OrderItemSnapshot> Items,
    IReadOnlyList<OrderStatusEventSnapshot> Events,
    string? CustomerAccessToken);

public sealed record OrderItemSnapshot(
    string OrderItemId,
    string MenuItemId,
    string Name,
    decimal UnitPrice,
    int Quantity,
    string Status,
    decimal LineTotal,
    DateTimeOffset UpdatedAt);

public sealed record OrderStatusEventSnapshot(
    string Status,
    string Source,
    string? ChangedByRole,
    string? Note,
    DateTimeOffset CreatedAt);

public sealed record CreateOrderCommand(
    string OrderType,
    string? TableCode,
    string? QrToken,
    string? TableSessionId,
    string PaymentMethod,
    IReadOnlyList<CreateOrderItemRequest> Items,
    decimal DiscountAmount = 0m,
    string? PromotionId = null,
    string? PromotionCode = null,
    string? CustomerPhoneNumber = null);

public sealed record UpdateOrderStatusResult(bool IsFound, OrderSnapshot? Order, string? ErrorCode = null);

public sealed record UpdateOrderItemStatusResult(bool IsOrderFound, bool IsItemFound, OrderSnapshot? Order, OrderItemSnapshot? Item, string? ErrorCode = null);
