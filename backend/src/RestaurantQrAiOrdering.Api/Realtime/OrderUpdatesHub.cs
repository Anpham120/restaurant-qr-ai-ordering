using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Tables;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Realtime;

public sealed class OrderUpdatesHub : Hub
{
    private readonly IOrderStore orders;
    private readonly RestaurantDbContext db;
    private readonly string signingKey;

    public OrderUpdatesHub(IOrderStore orders, RestaurantDbContext db, IOptions<JwtOptions> jwtOptions)
    {
        this.orders = orders;
        this.db = db;
        signingKey = jwtOptions.Value.SigningKey;
    }

    public override async Task OnConnectedAsync()
    {
        if (IsOperationsRole())
        {
            await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Operations);
        }

        await base.OnConnectedAsync();
    }

    public async Task WatchOrder(string orderCode, string? orderToken = null)
    {
        var order = orders.GetOrder(orderCode);
        if (order is null)
        {
            throw new HubException("ORDER_NOT_FOUND");
        }

        if (!IsOperationsRole()
            && !OrderAccessGuard.HasCustomerToken(order.CustomerAccessToken, orderToken))
        {
            throw new HubException("ORDER_ACCESS_DENIED");
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Order(order.OrderCode));
    }

    public async Task WatchTable(string tableCode, string? sessionToken = null)
    {
        var normalizedTableCode = tableCode.Trim().ToUpperInvariant();
        if (IsOperationsRole())
        {
            await JoinValidatedTableGroupAsync(normalizedTableCode);
            return;
        }

        if (string.IsNullOrWhiteSpace(sessionToken))
        {
            throw new HubException("TABLE_ACCESS_DENIED");
        }

        if (!await TryJoinTableGroupWithSessionTokenAsync(normalizedTableCode, sessionToken))
        {
            throw new HubException("TABLE_ACCESS_DENIED");
        }
    }

    public async Task WatchTableSession(string tableSessionId, string sessionToken)
    {
        if (string.IsNullOrWhiteSpace(tableSessionId) || string.IsNullOrWhiteSpace(sessionToken))
        {
            throw new HubException("TABLE_SESSION_ACCESS_DENIED");
        }

        var session = await db.TableSessions
            .AsNoTracking()
            .FirstOrDefaultAsync(item => item.Id == tableSessionId.Trim());
        if (session is null)
        {
            throw new HubException("TABLE_SESSION_NOT_FOUND");
        }

        if (!TableSessionCapability.IsValid(session, sessionToken, signingKey))
        {
            throw new HubException("TABLE_SESSION_ACCESS_DENIED");
        }

        var now = DateTimeOffset.UtcNow;
        if (!session.IsActiveAt(now))
        {
            throw new HubException("TABLE_SESSION_INACTIVE");
        }

        if (string.IsNullOrWhiteSpace(session.TableCode))
        {
            throw new HubException("TABLE_SESSION_INVALID");
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Table(session.TableCode));
    }

    private async Task JoinValidatedTableGroupAsync(string normalizedTableCode)
    {
        var table = await db.RestaurantTables
            .AsNoTracking()
            .FirstOrDefaultAsync(table => table.TableCode == normalizedTableCode && table.IsActive);
        if (table is null)
        {
            throw new HubException("TABLE_NOT_FOUND");
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Table(table.TableCode));
    }

    private async Task<bool> TryJoinTableGroupWithSessionTokenAsync(string normalizedTableCode, string sessionToken)
    {
        var now = DateTimeOffset.UtcNow;
        var sessions = await db.TableSessions
            .AsNoTracking()
            .Where(session =>
                session.TableCode == normalizedTableCode &&
                session.Status == TableSessionStatus.Open &&
                session.ClosedAt == null &&
                session.ExpiresAt > now)
            .ToListAsync();

        var matchedSession = sessions.FirstOrDefault(session =>
            TableSessionCapability.IsValid(session, sessionToken, signingKey));
        if (matchedSession is null || string.IsNullOrWhiteSpace(matchedSession.TableCode))
        {
            return false;
        }

        await Groups.AddToGroupAsync(Context.ConnectionId, OrderRealtimeGroups.Table(matchedSession.TableCode));
        return true;
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
