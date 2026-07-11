namespace RestaurantQrAiOrdering.Api.Realtime;

public interface IOrderRealtimeNotifier
{
    Task OrderCreatedAsync(OrderCreatedEvent payload, CancellationToken cancellationToken);

    Task OrderStatusChangedAsync(OrderStatusChangedEvent payload, string? tableCode, CancellationToken cancellationToken);

    Task OrderItemStatusChangedAsync(OrderItemStatusChangedEvent payload, string? tableCode, CancellationToken cancellationToken);

    Task PaymentRequestedAsync(PaymentRequestedEvent payload, string? tableCode, CancellationToken cancellationToken);
}
