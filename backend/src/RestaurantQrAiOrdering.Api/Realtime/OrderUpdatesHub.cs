using System.Security.Claims;
using Microsoft.AspNetCore.SignalR;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Realtime;

public sealed class OrderUpdatesHub : Hub
{
    private readonly IOrderStore orders;
    private readonly RestaurantDataStore restaurantData;

    public OrderUpdatesHub(IOrderStore orders, RestaurantDataStore restaurantData)
    {
        this.orders = orders;
        this.restaurantData = restaurantData;
    }

    public override async Task OnConnectedAsync()
    {
        if (IsOperationsRole())
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Operations);
        }

        await base.OnConnectedAsync();
    }

    public async Task WatchOrder(string orderCode, string? tableCode = null)
    {
        var order = orders.GetOrder(orderCode);
        if (order is null)
        {
            throw new HubException("ORDER_NOT_FOUND");
        }

        if (!IsOperationsRole() && !CustomerCanWatchOrder(order, tableCode))
        {
            throw new HubException("ORDER_ACCESS_DENIED");
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Order(order.OrderCode));
    }

    public async Task WatchTable(string tableCode)
    {
        var table = restaurantData.GetActiveTable(tableCode);
        if (table is null)
        {
            throw new HubException("TABLE_NOT_FOUND");
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Table(table.TableCode));
    }

    private bool CustomerCanWatchOrder(OrderSnapshot order, string? tableCode)
    {
        if (string.IsNullOrWhiteSpace(order.TableCode))
        {
            return true;
        }

        return !string.IsNullOrWhiteSpace(tableCode)
            && order.TableCode.Equals(tableCode.Trim(), StringComparison.OrdinalIgnoreCase);
    }

    private bool IsOperationsRole()
    {
        return Context.User?.IsInRole(UserRole.Staff) == true
            || Context.User?.IsInRole(UserRole.Kitchen) == true
            || Context.User?.IsInRole(UserRole.Admin) == true
            || HasRoleClaim(UserRole.Staff)
            || HasRoleClaim(UserRole.Kitchen)
            || HasRoleClaim(UserRole.Admin);
    }

    private bool HasRoleClaim(string role)
    {
        return Context.User?.Claims.Any(claim =>
            (claim.Type == ClaimTypes.Role || claim.Type == "role")
            && claim.Value.Equals(role, StringComparison.OrdinalIgnoreCase)) == true;
    }
}
