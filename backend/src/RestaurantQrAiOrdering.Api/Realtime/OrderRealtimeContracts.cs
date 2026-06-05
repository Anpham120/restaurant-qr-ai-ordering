namespace RestaurantQrAiOrdering.Api.Realtime;

public static class OrderRealtimeEvents
{
    public const string OrderCreated = "order.created";
    public const string OrderStatusChanged = "order.statusChanged";
    public const string OrderItemStatusChanged = "order.itemStatusChanged";
}

public static class OrderRealtimeGroups
{
    public const string Operations = "orders:operations";

    public static string Order(string orderCode)
    {
        return $"order:{orderCode.Trim().ToUpperInvariant()}";
    }

    public static string Table(string tableCode)
    {
        return $"table:{tableCode.Trim().ToUpperInvariant()}";
    }
}

public sealed record OrderCreatedEvent(
    string OrderId,
    string OrderCode,
    string OrderType,
    string? TableCode,
    string Status,
    DateTimeOffset CreatedAt);

public sealed record OrderStatusChangedEvent(
    string OrderId,
    string OrderCode,
    string Status,
    DateTimeOffset UpdatedAt);

public sealed record OrderItemStatusChangedEvent(
    string OrderId,
    string OrderCode,
    string OrderItemId,
    string MenuItemName,
    string Status,
    DateTimeOffset UpdatedAt);
