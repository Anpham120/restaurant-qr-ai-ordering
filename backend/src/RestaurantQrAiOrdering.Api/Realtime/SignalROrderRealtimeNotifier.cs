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

    public async Task PaymentRequestedAsync(
        PaymentRequestedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        await SendToOrderAndOperationsAsync(
            OrderRealtimeEvents.PaymentRequested,
            payload,
            payload.OrderCode,
            tableCode,
            cancellationToken);
    }

    public async Task NotifyCartUpdatedAsync(CartUpdatedEvent payload, CancellationToken cancellationToken)
    {
        await hubContext.Clients
            .Group(OrderRealtimeGroups.Operations)
            .SendAsync(OrderRealtimeEvents.CartUpdated, payload, cancellationToken);

        if (!string.IsNullOrWhiteSpace(payload.TableCode))
        {
            await hubContext.Clients
                .Group(OrderRealtimeGroups.Table(payload.TableCode))
                .SendAsync(OrderRealtimeEvents.CartUpdated, payload, cancellationToken);
        }
    }

    public async Task NotifyAssistanceRequestedAsync(
        string tableCode,
        string? tableSessionId,
        string? note,
        CancellationToken cancellationToken)
    {
        var payload = new AssistanceRequestedEvent(
            tableCode,
            tableSessionId,
            note,
            DateTimeOffset.UtcNow);

        await hubContext.Clients
            .Group(OrderRealtimeGroups.Operations)
            .SendAsync(OrderRealtimeEvents.AssistanceRequested, payload, cancellationToken);

        if (!string.IsNullOrWhiteSpace(tableCode))
        {
            await hubContext.Clients
                .Group(OrderRealtimeGroups.Table(tableCode))
                .SendAsync(OrderRealtimeEvents.AssistanceRequested, payload, cancellationToken);
        }
    }

    public async Task NotifyMenuAvailabilityChangedAsync(
        MenuAvailabilityChangedEvent payload,
        CancellationToken cancellationToken)
    {
        await hubContext.Clients
            .Group(OrderRealtimeGroups.Operations)
            .SendAsync(OrderRealtimeEvents.MenuAvailabilityChanged, payload, cancellationToken);

        // Broadcast to all table groups would require tracking; ops + a global group is enough
        // for customers who WatchTableSession — they also need a broadcast. Use Clients.All for menu.
        await hubContext.Clients.All.SendAsync(
            OrderRealtimeEvents.MenuAvailabilityChanged,
            payload,
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
