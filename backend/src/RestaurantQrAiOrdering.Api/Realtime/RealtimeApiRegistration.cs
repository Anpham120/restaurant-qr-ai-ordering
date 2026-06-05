namespace RestaurantQrAiOrdering.Api.Realtime;

public static class RealtimeApiRegistration
{
    public static IServiceCollection AddRestaurantRealtimeApis(this IServiceCollection services)
    {
        services.AddSignalR();
        services.AddSingleton<IOrderRealtimeNotifier, SignalROrderRealtimeNotifier>();

        return services;
    }

    public static IEndpointRouteBuilder MapRestaurantRealtimeApis(this IEndpointRouteBuilder app)
    {
        app.MapHub<OrderUpdatesHub>("/hubs/orders");

        return app;
    }
}
