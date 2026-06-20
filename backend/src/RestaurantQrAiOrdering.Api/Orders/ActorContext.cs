using System.Security.Claims;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Orders;

// Who initiated a state change, captured for the order status-history audit trail.
// Anonymous callers (QR customers placing their own orders) resolve to the Customer role.
public sealed record ActorContext(string? UserId, string? Role)
{
    public static readonly ActorContext Customer = new(null, UserRole.Customer);

    public static ActorContext FromPrincipal(ClaimsPrincipal? principal)
    {
        if (principal?.Identity?.IsAuthenticated != true)
        {
            return Customer;
        }

        return new ActorContext(
            principal.FindFirstValue(ClaimTypes.NameIdentifier),
            principal.FindFirstValue(ClaimTypes.Role) ?? UserRole.Customer);
    }
}
