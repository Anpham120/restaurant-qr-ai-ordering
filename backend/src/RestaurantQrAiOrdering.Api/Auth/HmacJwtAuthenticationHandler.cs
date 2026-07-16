using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Auth;

public sealed class HmacJwtAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public const string SchemeName = "Bearer";

    private readonly IJwtTokenService jwtTokenService;
    private readonly IUserStore users;

    public HmacJwtAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder,
        IJwtTokenService jwtTokenService,
        IUserStore users)
        : base(options, logger, encoder)
    {
        this.jwtTokenService = jwtTokenService;
        this.users = users;
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var authorization = Request.Headers.Authorization.ToString();
        if (string.IsNullOrWhiteSpace(authorization)
            && Request.Path.StartsWithSegments("/hubs/orders")
            && Request.Query.TryGetValue("access_token", out var queryTokens)
            && queryTokens.Count == 1
            && !string.IsNullOrWhiteSpace(queryTokens[0]))
        {
            authorization = $"Bearer {queryTokens[0]}";
        }

        if (string.IsNullOrWhiteSpace(authorization))
        {
            Logger.LogDebug(
                "Authentication skipped because no Authorization header was provided for {Path}.",
                Request.Path);

            return Task.FromResult(AuthenticateResult.NoResult());
        }

        if (!authorization.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            Logger.LogWarning(
                "Authentication failed because Authorization header used an unsupported scheme for {Path}.",
                Request.Path);

            return Task.FromResult(AuthenticateResult.Fail("Authorization header must use Bearer scheme."));
        }

        var token = authorization["Bearer ".Length..].Trim();
        var principal = jwtTokenService.ValidateAccessToken(token);
        if (principal is null)
        {
            Logger.LogWarning("Authentication failed because the access token is invalid for {Path}.", Request.Path);

            return Task.FromResult(AuthenticateResult.Fail("Invalid access token."));
        }


        var userId = principal.FindFirstValue(ClaimTypes.NameIdentifier);
        var authVersionText = principal.FindFirstValue("auth_version");
        if (!long.TryParse(authVersionText, out var authVersion)
            || (authVersion != 0 && users.GetSecurityStampTicks(userId ?? string.Empty) != authVersion))
        {
            return Task.FromResult(AuthenticateResult.Fail("Access token has been revoked."));
        }

        Logger.LogInformation(
            "Authenticated user {UserId} with role {Role} for {Path}.",
            principal.FindFirstValue(ClaimTypes.NameIdentifier),
            principal.FindFirstValue(ClaimTypes.Role),
            Request.Path);

        var ticket = new AuthenticationTicket(principal, HmacJwtAuthenticationHandler.SchemeName);
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }

    protected override async Task HandleChallengeAsync(AuthenticationProperties properties)
    {
        Logger.LogWarning(
            "Authorization challenge returned 401 for {Path}.",
            Request.Path);

        await ApiErrorFactory.WriteAsync(
            Response,
            StatusCodes.Status401Unauthorized,
            "AUTHENTICATION_REQUIRED",
            "A valid bearer token is required.");
    }

    protected override async Task HandleForbiddenAsync(AuthenticationProperties properties)
    {
        Logger.LogWarning(
            "Authorization returned 403 for user {UserId} on {Path}.",
            Context.User.FindFirstValue(ClaimTypes.NameIdentifier),
            Request.Path);

        await ApiErrorFactory.WriteAsync(
            Response,
            StatusCodes.Status403Forbidden,
            "FORBIDDEN",
            "The current user does not have permission to perform this action.");
    }
}
