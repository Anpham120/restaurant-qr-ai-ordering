namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatApiRegistration
{
    public static IServiceCollection AddRestaurantChatApis(this IServiceCollection services)
    {
        services.AddScoped<IChatStore, DbChatStore>();
        services.AddScoped<IChatAssistantService, ChatAssistantService>();
        services.AddHttpClient<IChatAiProvider, GeminiChatProvider>();

        return services;
    }

    public static IEndpointRouteBuilder MapRestaurantChatApis(this IEndpointRouteBuilder app)
    {
        app.MapChatEndpoints();

        return app;
    }
}
