using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Menu;
using RestaurantQrAiOrdering.Api.Tables;

public static class MenuTableApiRegistration
{
    public static IServiceCollection AddRestaurantMenuTableApis(this IServiceCollection services)
    {
        services.AddSingleton<RestaurantDataStore>();

        return services;
    }

    public static IEndpointRouteBuilder MapRestaurantMenuTableApis(this IEndpointRouteBuilder app)
    {
        app.MapMenuEndpoints();
        app.MapCategoryEndpoints();
        app.MapTableEndpoints();

        return app;
    }
}
