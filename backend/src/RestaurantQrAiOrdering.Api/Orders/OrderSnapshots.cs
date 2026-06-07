namespace RestaurantQrAiOrdering.Api.Orders;

public sealed record OrderSnapshot(
    string OrderId,
    string OrderCode,
    string OrderType,
    string? TableCode,
    string Status,
    string PaymentStatus,
    string PaymentMethod,
    DeliveryInfoSnapshot? DeliveryInfo,
    decimal SubtotalAmount,
    decimal TotalAmount,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<OrderItemSnapshot> Items,
    IReadOnlyList<OrderStatusEventSnapshot> Events);

public sealed record DeliveryInfoSnapshot(
    string RecipientName,
    string PhoneNumber,
    string Address,
    string? Note);

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
    DateTimeOffset CreatedAt);

public sealed record CreateOrderCommand(
    string OrderType,
    string? TableCode,
    string PaymentMethod,
    DeliveryInfoRequest? DeliveryInfo,
    IReadOnlyList<CreateOrderItemRequest> Items);

public sealed record UpdateOrderStatusResult(bool IsFound, OrderSnapshot? Order);

public sealed record UpdateOrderItemStatusResult(bool IsOrderFound, bool IsItemFound, OrderSnapshot? Order, OrderItemSnapshot? Item);
