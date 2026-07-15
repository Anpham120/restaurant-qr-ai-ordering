namespace RestaurantQrAiOrdering.Api.Cart;

public static class CartApiRegistration
{
    public static IEndpointRouteBuilder MapRestaurantCartApis(this IEndpointRouteBuilder app)
    {
        app.MapCartEndpoints();

        return app;
    }
}
