using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class TableSessionLifecycleTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public TableSessionLifecycleTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task TestV5_ClosedTableSessionInvalidatesItsChatCapability()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var tableSession = await OpenTableSessionAsync(client);
        using var createChatResponse = await client.PostAsJsonAsync("/api/chat/sessions", new
        {
            tableSessionId = tableSession.Id,
            tableCode = tableSession.TableCode
        });
        createChatResponse.EnsureSuccessStatusCode();
        using var chat = await ReadJsonAsync(createChatResponse);
        var chatSessionId = chat.RootElement.GetProperty("chatSessionId").GetString()!;
        var chatAccessToken = chat.RootElement.GetProperty("accessToken").GetString()!;

        using var closeResponse = await client.PostAsync($"/api/table-sessions/{tableSession.Id}/close", null);
        closeResponse.EnsureSuccessStatusCode();

        using var historyRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/chat/sessions/{chatSessionId}/messages");
        historyRequest.Headers.Add("X-Chat-Session-Token", chatAccessToken);
        using var historyResponse = await client.SendAsync(historyRequest);

        Assert.Equal(HttpStatusCode.NotFound, historyResponse.StatusCode);
    }

    private static async Task<string> SignInAsAdminAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email = RestaurantApiFactory.AdminEmail,
            password = RestaurantApiFactory.AdminPassword
        });
        response.EnsureSuccessStatusCode();

        using var body = await ReadJsonAsync(response);
        return body.RootElement.GetProperty("accessToken").GetString()!;
    }

    private static async Task<TableSession> OpenTableSessionAsync(HttpClient client)
    {
        using var tablesResponse = await client.GetAsync("/api/admin/tables");
        tablesResponse.EnsureSuccessStatusCode();
        using var tables = await ReadJsonAsync(tablesResponse);
        var table = tables.RootElement.GetProperty("items")[0];
        var tableCode = table.GetProperty("tableCode").GetString()!;
        var qrToken = table.GetProperty("qrToken").GetString()!;

        using var sessionResponse = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken,
            tableCode
        });
        sessionResponse.EnsureSuccessStatusCode();
        using var session = await ReadJsonAsync(sessionResponse);
        return new TableSession(
            session.RootElement.GetProperty("sessionId").GetString()!,
            session.RootElement.GetProperty("tableCode").GetString()!);
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    private sealed record TableSession(string Id, string TableCode);
}
