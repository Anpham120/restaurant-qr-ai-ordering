using System.Security.Cryptography;
using System.Text;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Orders;

public static class OrderAccessGuard
{
    public const string TokenHeaderName = "X-Order-Token";

    // Operators (Kitchen/Staff/Admin) may read any order. A customer must present the
    // per-order access token issued at creation via the X-Order-Token header. A missing or
    // mismatched token is treated as "not found" by callers so the sequential order codes
    // (ORD-1001, 1002, ...) can't be enumerated to probe which orders exist or leak PII.
    public static bool CanRead(HttpContext http, string? accessToken)
    {
        if (http.User.IsInRole(UserRole.Kitchen)
            || http.User.IsInRole(UserRole.Staff)
            || http.User.IsInRole(UserRole.Admin))
        {
            return true;
        }

        if (string.IsNullOrEmpty(accessToken))
        {
            return false;
        }

        var provided = http.Request.Headers[TokenHeaderName].ToString();
        if (string.IsNullOrEmpty(provided))
        {
            return false;
        }

        return CryptographicOperations.FixedTimeEquals(
            Encoding.UTF8.GetBytes(provided),
            Encoding.UTF8.GetBytes(accessToken));
    }
}
