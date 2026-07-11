using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Enums;
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

    [Fact]
    public async Task TestV5_ExpiredTableSessionInvalidatesItsChatCapability()
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

        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var persistedSession = await db.TableSessions.SingleAsync(session => session.Id == tableSession.Id);
            persistedSession.ExpiresAt = DateTimeOffset.UtcNow.AddMinutes(-1);
            await db.SaveChangesAsync();
        }

        using var historyRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/chat/sessions/{chatSessionId}/messages");
        historyRequest.Headers.Add("X-Chat-Session-Token", chatAccessToken);
        using var historyResponse = await client.SendAsync(historyRequest);

        Assert.Equal(HttpStatusCode.NotFound, historyResponse.StatusCode);
    }

    [Fact]
    public async Task TestV5_ChatSessionCannotBeCreatedForClosedTableSession()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var tableSession = await OpenTableSessionAsync(client);
        using var closeResponse = await client.PostAsync($"/api/table-sessions/{tableSession.Id}/close", null);
        closeResponse.EnsureSuccessStatusCode();

        using var createChatResponse = await client.PostAsJsonAsync("/api/chat/sessions", new
        {
            tableSessionId = tableSession.Id,
            tableCode = tableSession.TableCode
        });

        Assert.Equal(HttpStatusCode.Gone, createChatResponse.StatusCode);
    }

    [Fact]
    public async Task TestV11_ActiveTableSessionRestoresItsExistingChatSession()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var tableSession = await OpenTableSessionAsync(client);
        using var firstResponse = await client.PostAsJsonAsync("/api/chat/sessions", new
        {
            tableSessionId = tableSession.Id,
            tableCode = tableSession.TableCode
        });
        firstResponse.EnsureSuccessStatusCode();
        using var firstChat = await ReadJsonAsync(firstResponse);
        var firstChatSessionId = firstChat.RootElement.GetProperty("chatSessionId").GetString()!;

        using var secondResponse = await client.PostAsJsonAsync("/api/chat/sessions", new
        {
            tableSessionId = tableSession.Id,
            tableCode = tableSession.TableCode
        });
        Assert.Equal(HttpStatusCode.OK, secondResponse.StatusCode);
        using var secondChat = await ReadJsonAsync(secondResponse);

        Assert.Equal(firstChatSessionId, secondChat.RootElement.GetProperty("chatSessionId").GetString());
        Assert.True(secondChat.RootElement.GetProperty("reused").GetBoolean());

        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        Assert.Equal(1, await db.ChatSessions.CountAsync(session => session.TableSessionId == tableSession.Id));
    }

    [Fact]
    public async Task TestV4_ReopeningAfterExpiryClosesTheOldSessionAndItsChats()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var expiredSession = await OpenTableSessionAsync(client);
        using var createChatResponse = await client.PostAsJsonAsync("/api/chat/sessions", new
        {
            tableSessionId = expiredSession.Id,
            tableCode = expiredSession.TableCode
        });
        createChatResponse.EnsureSuccessStatusCode();
        using var chat = await ReadJsonAsync(createChatResponse);
        var chatSessionId = chat.RootElement.GetProperty("chatSessionId").GetString()!;

        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var persistedSession = await db.TableSessions.SingleAsync(session => session.Id == expiredSession.Id);
            persistedSession.ExpiresAt = DateTimeOffset.UtcNow.AddMinutes(-1);
            await db.SaveChangesAsync();
        }

        var reopenedSession = await OpenTableSessionAsync(client);

        Assert.NotEqual(expiredSession.Id, reopenedSession.Id);
        using var verificationScope = factory.Services.CreateScope();
        var verificationDb = verificationScope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var oldSession = await verificationDb.TableSessions.SingleAsync(session => session.Id == expiredSession.Id);
        Assert.Equal(TableSessionStatus.Expired, oldSession.Status);
        Assert.False(await verificationDb.ChatSessions.AnyAsync(session => session.Id == chatSessionId));
    }

    [Fact]
    public void TestV4_ActiveTableSessionHasDatabaseUniquenessGuard()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var entityType = db.Model.FindEntityType(typeof(RestaurantQrAiOrdering.Entities.TableSession));
        var activeSessionIndex = entityType!
            .GetIndexes()
            .SingleOrDefault(index =>
                index.GetDatabaseName() == "UX_table_sessions_active_restaurant_table");

        Assert.NotNull(activeSessionIndex);
        Assert.True(activeSessionIndex!.IsUnique);
        Assert.Equal("\"status\" = 'Open' AND \"closed_at\" IS NULL", activeSessionIndex.GetFilter());
    }

    [Fact]
    public async Task TestV12_TableSessionOrderHistoryRequiresItsOwnCapability()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var tableSession = await OpenTableSessionAsync(client);
        var initialTotal = await GetTableSessionOrderTotalAsync(client, tableSession);
        await CreateDineInOrderAsync(client, tableSession);
        await CreateDineInOrderAsync(client, tableSession);

        using var historyRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/table-sessions/{tableSession.Id}/orders");
        historyRequest.Headers.Add("X-Table-Session-Token", tableSession.Token);
        using var historyResponse = await client.SendAsync(historyRequest);
        historyResponse.EnsureSuccessStatusCode();
        using var history = await ReadJsonAsync(historyResponse);
        Assert.True(history.RootElement.GetProperty("total").GetInt32() >= initialTotal + 2);

        using var rejectedRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/table-sessions/{tableSession.Id}/orders");
        rejectedRequest.Headers.Add("X-Table-Session-Token", "not-a-valid-table-session-capability");
        using var rejectedResponse = await client.SendAsync(rejectedRequest);
        Assert.Equal(HttpStatusCode.Unauthorized, rejectedResponse.StatusCode);
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
            session.RootElement.GetProperty("tableCode").GetString()!,
            qrToken,
            session.RootElement.GetProperty("tableSessionToken").GetString()!);
    }

    private static async Task CreateDineInOrderAsync(HttpClient client, TableSession tableSession)
    {
        using var menuResponse = await client.GetAsync("/api/menu");
        menuResponse.EnsureSuccessStatusCode();
        using var menu = await ReadJsonAsync(menuResponse);
        var menuItem = menu.RootElement.GetProperty("items")
            .EnumerateArray()
            .First(item => item.GetProperty("isAvailable").GetBoolean());

        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/orders")
        {
            Content = JsonContent.Create(new
            {
                orderType = "DineIn",
                tableCode = tableSession.TableCode,
                qrToken = tableSession.QrToken,
                tableSessionId = tableSession.Id,
                items = new[] { new { menuItemId = menuItem.GetProperty("id").GetString(), quantity = 1 } }
            })
        };
        request.Headers.Add("Idempotency-Key", $"session-order-history-{Guid.NewGuid():N}");
        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private static async Task<int> GetTableSessionOrderTotalAsync(HttpClient client, TableSession tableSession)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, $"/api/table-sessions/{tableSession.Id}/orders");
        request.Headers.Add("X-Table-Session-Token", tableSession.Token);
        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
        using var payload = await ReadJsonAsync(response);
        return payload.RootElement.GetProperty("total").GetInt32();
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    private sealed record TableSession(string Id, string TableCode, string QrToken, string Token);
}
