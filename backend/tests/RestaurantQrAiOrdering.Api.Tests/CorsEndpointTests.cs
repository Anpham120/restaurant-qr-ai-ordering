using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class CorsEndpointTests
{
    [Theory]
    [InlineData("https://cmcrestaurant.app")]
    [InlineData("https://customer.cmcrestaurant.app")]
    [InlineData("https://admin.cmcrestaurant.app")]
    public async Task OptionsChatEndpoint_FromPublicFrontendDomain_AllowsCorsPreflight(string origin)
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        using var request = new HttpRequestMessage(HttpMethod.Options, "/api/chat/sessions/chat_001/messages");

        request.Headers.Add("Origin", origin);
        request.Headers.Add("Access-Control-Request-Method", "POST");
        request.Headers.Add("Access-Control-Request-Headers", "content-type");

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);
        Assert.Equal(
            origin,
            response.Headers.GetValues("Access-Control-Allow-Origin").Single());
        Assert.Contains(
            "POST",
            response.Headers.GetValues("Access-Control-Allow-Methods").Single());
    }
}
