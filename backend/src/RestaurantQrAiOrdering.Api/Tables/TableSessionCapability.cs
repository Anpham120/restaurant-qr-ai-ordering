using System.Security.Cryptography;
using System.Text;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Tables;

public static class TableSessionCapability
{
    public static bool TryRead(HttpRequest request, out string token)
    {
        token = string.Empty;
        if (!request.Headers.TryGetValue("X-Table-Session-Token", out var values) || values.Count != 1)
        {
            return false;
        }

        var supplied = values[0];
        if (string.IsNullOrWhiteSpace(supplied))
        {
            return false;
        }

        token = supplied;
        return true;
    }

    public static bool IsValid(TableSession session, string suppliedToken, string signingKey)
    {
        byte[] suppliedSignature;
        try
        {
            suppliedSignature = Base64Url.Decode(suppliedToken);
        }
        catch (FormatException)
        {
            return false;
        }

        var expectedSignature = CreateSignature(session, signingKey);
        return CryptographicOperations.FixedTimeEquals(expectedSignature, suppliedSignature);
    }

    public static string CreateToken(TableSession session, string signingKey) =>
        Base64Url.Encode(CreateSignature(session, signingKey));

    public static IResult Unauthorized() =>
        ApiErrorFactory.Result(
            StatusCodes.Status401Unauthorized,
            "TABLE_SESSION_TOKEN_INVALID",
            "A valid table session token is required.");

    private static byte[] CreateSignature(TableSession session, string signingKey)
    {
        if (string.IsNullOrWhiteSpace(signingKey))
        {
            throw new InvalidOperationException("JWT signing key is required for table session capabilities.");
        }

        var signingKeyBytes = Encoding.UTF8.GetBytes(signingKey);
        var purpose = Encoding.UTF8.GetBytes("restaurant-qr-ai-ordering:table-session-capability:v1");
        var purposeKey = HMACSHA256.HashData(signingKeyBytes, purpose);
        var payload = Encoding.UTF8.GetBytes(
            $"{session.Id}\n{session.OpenedAt.UtcDateTime.Ticks}\n{session.ExpiresAt.UtcDateTime.Ticks}");

        return HMACSHA256.HashData(purposeKey, payload);
    }
}
