using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class TableAssistanceTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public TableAssistanceTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task GuestCanRequestAssistanceForOpenTableSession()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var session = await TableSessionTestHelpers.OpenFreshTableSessionAsync(client);

        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"/api/table-sessions/{session.Id}/assistance")
        {
            Content = JsonContent.Create(new { note = "Yêu cầu gọi nhân viên" }),
        };
        request.Headers.Add("X-Table-Session-Token", session.Token);

        using var response = await client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        using var body = await ReadJsonAsync(response);
        Assert.True(body.RootElement.GetProperty("ok").GetBoolean());
        Assert.False(string.IsNullOrWhiteSpace(body.RootElement.GetProperty("tableCode").GetString()));
    }

    [Fact]
    public async Task AssistanceRequiresValidSessionToken()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var session = await TableSessionTestHelpers.OpenFreshTableSessionAsync(client);

        using var response = await client.PostAsJsonAsync(
            $"/api/table-sessions/{session.Id}/assistance",
            new { note = "test" });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    private static async Task<string> SignInAsAdminAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email = RestaurantApiFactory.AdminEmail,
            password = RestaurantApiFactory.AdminPassword,
        });
        response.EnsureSuccessStatusCode();

        using var body = await ReadJsonAsync(response);
        return body.RootElement.GetProperty("accessToken").GetString()!;
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }
}
