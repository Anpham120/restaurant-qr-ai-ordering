using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace RestaurantQrAiOrdering.Api.Auth;

public sealed class HmacJwtAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public const string SchemeName = "Bearer";

    private readonly IJwtTokenService jwtTokenService;

    public HmacJwtAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder,
        IJwtTokenService jwtTokenService)
        : base(options, logger, encoder)
    {
        this.jwtTokenService = jwtTokenService;
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var authorization = Request.Headers.Authorization.ToString();
        if (string.IsNullOrWhiteSpace(authorization))
        {
            return Task.FromResult(AuthenticateResult.NoResult());
        }

        if (!authorization.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(AuthenticateResult.Fail("Authorization header must use Bearer scheme."));
        }

        var token = authorization["Bearer ".Length..].Trim();
        var principal = jwtTokenService.ValidateAccessToken(token);
        if (principal is null)
        {
            return Task.FromResult(AuthenticateResult.Fail("Invalid access token."));
        }

        var ticket = new AuthenticationTicket(principal, HmacJwtAuthenticationHandler.SchemeName);
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}
