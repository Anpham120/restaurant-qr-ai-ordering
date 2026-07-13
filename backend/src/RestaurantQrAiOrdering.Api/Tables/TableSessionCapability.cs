using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Tables;

public static class TableSessionCapability
{
    private const string CurrentPurpose = "restaurant-qr-ai-ordering:table-session-capability:v2";
    private const string LegacyPurpose = "restaurant-qr-ai-ordering:table-session-capability:v1";

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
        => CapabilityTokenSigner.IsValid(
            suppliedToken,
            signingKey,
            (CurrentPurpose, session.Id),
            (LegacyPurpose, CreateLegacyPayload(session)));

    public static string CreateToken(TableSession session, string signingKey) =>
        CapabilityTokenSigner.CreateToken(signingKey, CurrentPurpose, session.Id);

    public static IResult Unauthorized() =>
        ApiErrorFactory.Result(
            StatusCodes.Status401Unauthorized,
            "TABLE_SESSION_TOKEN_INVALID",
            "A valid table session token is required.");

    private static string CreateLegacyPayload(TableSession session) =>
        $"{session.Id}\n{session.OpenedAt.UtcDateTime.Ticks}\n{session.ExpiresAt.UtcDateTime.Ticks}";
}
