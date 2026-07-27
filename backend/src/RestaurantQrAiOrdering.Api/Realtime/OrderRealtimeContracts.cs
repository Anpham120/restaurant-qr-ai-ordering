namespace RestaurantQrAiOrdering.Api.Realtime;

using RestaurantQrAiOrdering.Api.Tables;

public static class OrderRealtimeEvents
{
    public const string OrderCreated = "order.created";
    public const string OrderStatusChanged = "order.statusChanged";
    public const string OrderItemStatusChanged = "order.itemStatusChanged";
    public const string PaymentRequested = "payment.requested";
    public const string TableInvoicePaymentConfirmed = "tableInvoice.paymentConfirmed";
    public const string CartUpdated = "cart.updated";
    public const string AssistanceRequested = "assistance.requested";
    public const string MenuAvailabilityChanged = "menu.availabilityChanged";
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

public sealed record PaymentRequestedEvent(
    string OrderId,
    string OrderCode,
    string Method,
    string Status,
    decimal Amount,
    DateTimeOffset UpdatedAt,
    string? TableCode);

public sealed record CartUpdatedEvent(
    string TableSessionId,
    string? TableCode,
    int ItemCount,
    decimal Subtotal,
    DateTimeOffset UpdatedAt);

public sealed record AssistanceRequestedEvent(
    string TableCode,
    string? TableSessionId,
    string? Note,
    DateTimeOffset RequestedAt);

public sealed record MenuAvailabilityChangedEvent(
    string MenuItemId,
    string Name,
    bool IsAvailable,
    DateTimeOffset UpdatedAt);

public sealed record TableInvoicePaymentConfirmedEvent(
    TableInvoiceResponse Invoice,
    DateTimeOffset PaidAt);
