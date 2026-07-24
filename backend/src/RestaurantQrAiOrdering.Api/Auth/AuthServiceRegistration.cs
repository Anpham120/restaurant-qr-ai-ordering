using Microsoft.AspNetCore.Authentication;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Auth;

public static class AuthServiceRegistration
{
    public static IServiceCollection AddRestaurantAuth(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddRestaurantUsers();
        services.AddOptions<JwtOptions>()
            .Bind(configuration.GetSection(JwtOptions.SectionName))
            .Validate(
                options => !string.IsNullOrWhiteSpace(options.SigningKey) && options.SigningKey.Length >= 32,
                "Jwt:SigningKey must be supplied through environment configuration and contain at least 32 characters.")
            .Validate(options => options.AccessTokenMinutes is >= 1 and <= 1440, "JWT lifetime must be between 1 and 1440 minutes.")
            .ValidateOnStart();
        services.AddSingleton<IJwtTokenService, JwtTokenService>();

        services
            .AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = HmacJwtAuthenticationHandler.SchemeName;
                options.DefaultChallengeScheme = HmacJwtAuthenticationHandler.SchemeName;
            })
            .AddScheme<AuthenticationSchemeOptions, HmacJwtAuthenticationHandler>(
                HmacJwtAuthenticationHandler.SchemeName,
                options => { });

        services.AddAuthorization(options =>
        {
            options.AddPolicy("CustomerOnly", policy => policy.RequireRole(UserRole.Customer));
            options.AddPolicy("StaffOnly", policy => policy.RequireRole(UserRole.Staff, UserRole.CounterStaff));
            options.AddPolicy("KitchenOnly", policy => policy.RequireRole(UserRole.Kitchen));
            options.AddPolicy("AdminOnly", policy => policy.RequireRole(UserRole.Admin));
            options.AddPolicy("StaffOrAdmin", policy => policy.RequireRole(UserRole.Staff, UserRole.CounterStaff, UserRole.Admin));
            options.AddPolicy("CounterOrAdmin", policy => policy.RequireRole(UserRole.Staff, UserRole.CounterStaff, UserRole.Admin));
            options.AddPolicy("KitchenOrAdmin", policy => policy.RequireRole(UserRole.Kitchen, UserRole.Admin));
        });

        return services;
    }
}
