namespace RestaurantQrAiOrdering.Api.Orders;

public static class OrderApiRegistration
{
    public static IServiceCollection AddRestaurantOrderApis(this IServiceCollection services)
    {
        services.AddSingleton<IOrderStore, OrderStore>();

        return services;
    }
}
