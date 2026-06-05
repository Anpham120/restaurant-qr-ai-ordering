using Microsoft.AspNetCore.Authentication;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Auth;

public static class AuthServiceRegistration
{
    public static IServiceCollection AddRestaurantAuth(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddRestaurantUsers();
        services.Configure<JwtOptions>(configuration.GetSection(JwtOptions.SectionName));
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
            options.AddPolicy("StaffOnly", policy => policy.RequireRole(UserRole.Staff));
            options.AddPolicy("KitchenOnly", policy => policy.RequireRole(UserRole.Kitchen));
            options.AddPolicy("AdminOnly", policy => policy.RequireRole(UserRole.Admin));
            options.AddPolicy("StaffOrAdmin", policy => policy.RequireRole(UserRole.Staff, UserRole.Admin));
            options.AddPolicy("KitchenOrAdmin", policy => policy.RequireRole(UserRole.Kitchen, UserRole.Admin));
        });

        return services;
    }
}
