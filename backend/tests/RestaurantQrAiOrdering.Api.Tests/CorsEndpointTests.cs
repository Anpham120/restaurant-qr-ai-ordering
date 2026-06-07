using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class CorsEndpointTests
{
    [Fact]
    public async Task OptionsChatEndpoint_FromCustomerDomain_AllowsCorsPreflight()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();
        using var request = new HttpRequestMessage(HttpMethod.Options, "/api/chat/sessions/chat_001/messages");

        request.Headers.Add("Origin", "https://customer.cmcrestaurant.app");
        request.Headers.Add("Access-Control-Request-Method", "POST");
        request.Headers.Add("Access-Control-Request-Headers", "content-type");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);
        Assert.Equal(
            "https://customer.cmcrestaurant.app",
            response.Headers.GetValues("Access-Control-Allow-Origin").Single());
        Assert.Contains(
            "POST",
            response.Headers.GetValues("Access-Control-Allow-Methods").Single());
    }
}
