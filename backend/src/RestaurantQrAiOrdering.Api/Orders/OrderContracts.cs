namespace RestaurantQrAiOrdering.Api.Orders;

public sealed record CreateOrderRequest(
    string? OrderType,
    string? TableCode,
    string? QrToken,
    string? TableSessionId,
    IReadOnlyList<CreateOrderItemRequest>? Items,
    string? PromotionCode = null,
    string? CustomerPhoneNumber = null);

public sealed record CreateOrderItemRequest(
    string? MenuItemId,
    int Quantity);

public sealed record UpdateOrderStatusRequest(string? Status);

public sealed record UpdateOrderItemStatusRequest(string? Status);

public sealed record OrderListResponse(
    IReadOnlyList<OrderResponse> Orders,
    int Total);

public sealed record OrderResponse(
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
    IReadOnlyList<OrderItemResponse> Items,
    IReadOnlyList<OrderStatusEventResponse> Events);

public sealed record CreateOrderResponse(
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
    IReadOnlyList<OrderItemResponse> Items,
    IReadOnlyList<OrderStatusEventResponse> Events,
    string CustomerAccessToken);

public sealed record OrderItemResponse(
    string OrderItemId,
    string MenuItemId,
    string Name,
    decimal UnitPrice,
    int Quantity,
    string Status,
    decimal LineTotal,
    DateTimeOffset UpdatedAt);

public sealed record OrderStatusEventResponse(
    string Status,
    string Source,
    string? ChangedByRole,
    string? Note,
    DateTimeOffset CreatedAt);
