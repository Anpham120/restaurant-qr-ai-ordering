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
    PickupInfoSnapshot? PickupInfo,
    decimal SubtotalAmount,
    decimal TotalAmount,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<OrderItemSnapshot> Items,
    IReadOnlyList<OrderStatusEventSnapshot> Events,
    string? CustomerAccessToken);

public sealed record PickupInfoSnapshot(
    string CustomerName,
    string PhoneNumber,
    DateTimeOffset? RequestedAt);

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
    string PaymentMethod,
    PickupInfoRequest? PickupInfo,
    IReadOnlyList<CreateOrderItemRequest> Items);

public sealed record UpdateOrderStatusResult(bool IsFound, OrderSnapshot? Order, string? ErrorCode = null);

public sealed record UpdateOrderItemStatusResult(bool IsOrderFound, bool IsItemFound, OrderSnapshot? Order, OrderItemSnapshot? Item);
