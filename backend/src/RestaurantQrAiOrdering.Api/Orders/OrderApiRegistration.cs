namespace RestaurantQrAiOrdering.Api.Orders;

public static class OrderApiRegistration
{
    public static IServiceCollection AddRestaurantOrderApis(this IServiceCollection services)
    {
        services.AddScoped<IOrderStore, OrderStore>();

        return services;
    }
}
