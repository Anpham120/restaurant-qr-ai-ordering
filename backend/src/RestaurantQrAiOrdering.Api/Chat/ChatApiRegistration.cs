namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatApiRegistration
{
    public static IServiceCollection AddRestaurantChatApis(this IServiceCollection services)
    {
        services.AddMemoryCache();
        services.AddScoped<IChatStore, DbChatStore>();
        services.AddScoped<IChatAssistantService, ChatAssistantService>();
        services.AddSingleton<IChatRateLimiter, ChatRateLimiter>();
        services.AddHttpClient<IChatAiProvider, PythonRagChatProvider>();

        return services;
    }

    public static IEndpointRouteBuilder MapRestaurantChatApis(this IEndpointRouteBuilder app)
    {
        app.MapChatEndpoints();
        app.MapChatStreamEndpoints();
        app.MapChatAdminEndpoints();

        return app;
    }
}
