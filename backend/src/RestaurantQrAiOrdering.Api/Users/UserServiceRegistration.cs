namespace RestaurantQrAiOrdering.Api.Users;

public static class UserServiceRegistration
{
    public static IServiceCollection AddRestaurantUsers(this IServiceCollection services)
    {
        services.AddSingleton<IRoleCatalog, RoleCatalog>();
        services.AddSingleton<IPasswordHasher, PasswordHasher>();
        services.AddSingleton<IUserStore, UserStore>();

        return services;
    }
}
