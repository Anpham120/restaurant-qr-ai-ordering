namespace RestaurantQrAiOrdering.Api.Orders;

public sealed record CreateOrderRequest(
    string? OrderType,
    string? TableCode,
    string? PaymentMethod,
    DeliveryInfoRequest? DeliveryInfo,
    IReadOnlyList<CreateOrderItemRequest>? Items);

public sealed record DeliveryInfoRequest(
    string? RecipientName,
    string? PhoneNumber,
    string? Address,
    string? Note);

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
    string Status,
    string PaymentStatus,
    string PaymentMethod,
    DeliveryInfoResponse? DeliveryInfo,
    decimal SubtotalAmount,
    decimal TotalAmount,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<OrderItemResponse> Items,
    IReadOnlyList<OrderStatusEventResponse> Events);

public sealed record DeliveryInfoResponse(
    string RecipientName,
    string PhoneNumber,
    string Address,
    string? Note);

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
    DateTimeOffset CreatedAt);
