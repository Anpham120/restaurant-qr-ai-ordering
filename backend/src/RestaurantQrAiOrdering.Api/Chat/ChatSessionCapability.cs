using RestaurantQrAiOrdering.Api.Auth;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatSessionCapability
{
    private const string CurrentPurpose = "restaurant-qr-ai-ordering:chat-session-capability:v2";
    private const string LegacyPurpose = "restaurant-qr-ai-ordering:chat-session-capability:v1";

    public static string CreateToken(ChatSessionSnapshot session, string signingKey) =>
        CapabilityTokenSigner.CreateToken(signingKey, CurrentPurpose, session.Id);

    public static bool IsValid(ChatSessionSnapshot session, string suppliedToken, string signingKey) =>
        CapabilityTokenSigner.IsValid(
            suppliedToken,
            signingKey,
            (CurrentPurpose, session.Id),
            (LegacyPurpose, $"{session.Id}\n{session.CreatedAt.UtcDateTime.Ticks}"));
}
