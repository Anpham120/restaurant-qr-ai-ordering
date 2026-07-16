using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;

namespace RestaurantQrAiOrdering.Api.Tests.Realtime;

public sealed class OrderHubEndpointTests
{
    [Fact]
    public async Task OrdersHub_NegotiateEndpointIsMapped()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsync("/hubs/orders/negotiate?negotiateVersion=1", content: null);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}
