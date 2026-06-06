namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatApiRegistration
{
    public static IServiceCollection AddRestaurantChatApis(this IServiceCollection services)
    {
        services.AddSingleton<IChatStore, ChatStore>();
        services.AddScoped<IChatAssistantService, ChatAssistantService>();
        services.AddHttpClient<IChatAiProvider, NineRouterChatProvider>();

        return services;
    }

    public static IEndpointRouteBuilder MapRestaurantChatApis(this IEndpointRouteBuilder app)
    {
        app.MapChatEndpoints();

        return app;
    }
}
