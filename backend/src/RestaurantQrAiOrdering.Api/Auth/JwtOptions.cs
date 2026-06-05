namespace RestaurantQrAiOrdering.Api.Auth;

public sealed class JwtOptions
{
    public const string SectionName = "Jwt";

    public string Issuer { get; init; } = "RestaurantQrAiOrdering";

    public string Audience { get; init; } = "RestaurantQrAiOrdering.Client";

    public string SigningKey { get; init; } = string.Empty;

    public int AccessTokenMinutes { get; init; } = 60;
}
