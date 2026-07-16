using Microsoft.AspNetCore.SignalR;

namespace RestaurantQrAiOrdering.Api.Realtime;

public sealed class SignalROrderRealtimeNotifier : IOrderRealtimeNotifier
{
    private readonly IHubContext<OrderUpdatesHub> hubContext;

    public SignalROrderRealtimeNotifier(IHubContext<OrderUpdatesHub> hubContext)
    {
        this.hubContext = hubContext;
    }

    public async Task OrderCreatedAsync(OrderCreatedEvent payload, CancellationToken cancellationToken)
    {
        await SendToOrderAndOperationsAsync(
            OrderRealtimeEvents.OrderCreated,
            payload,
            payload.OrderCode,
            payload.TableCode,
            cancellationToken);
    }

    public async Task OrderStatusChangedAsync(
        OrderStatusChangedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        await SendToOrderAndOperationsAsync(
            OrderRealtimeEvents.OrderStatusChanged,
            payload,
            payload.OrderCode,
            tableCode,
            cancellationToken);
    }

    public async Task OrderItemStatusChangedAsync(
        OrderItemStatusChangedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        await SendToOrderAndOperationsAsync(
            OrderRealtimeEvents.OrderItemStatusChanged,
            payload,
            payload.OrderCode,
            tableCode,
            cancellationToken);
    }

    private async Task SendToOrderAndOperationsAsync(
        string eventName,
        object payload,
        string orderCode,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        var targets = hubContext.Clients.Groups(OrderRealtimeGroups.Order(orderCode), OrderRealtimeGroups.Operations);
        await targets.SendAsync(eventName, payload, cancellationToken);

        if (!string.IsNullOrWhiteSpace(tableCode))
        {
            await hubContext.Clients
                .Group(OrderRealtimeGroups.Table(tableCode))
                .SendAsync(eventName, payload, cancellationToken);
        }
    }
}
