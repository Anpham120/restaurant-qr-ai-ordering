using RestaurantQrAiOrdering.Api.Cart;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Menu;
using RestaurantQrAiOrdering.Api.Tables;

public static class MenuTableApiRegistration
{
    public static IServiceCollection AddRestaurantMenuTableApis(this IServiceCollection services)
    {
        return services;
    }

    public static IEndpointRouteBuilder MapRestaurantMenuTableApis(this IEndpointRouteBuilder app)
    {
        app.MapMenuEndpoints();
        app.MapCategoryEndpoints();
        app.MapTableEndpoints();
        app.MapTableInvoiceEndpoints();
        app.MapRestaurantCartApis();

        return app;
    }
}
