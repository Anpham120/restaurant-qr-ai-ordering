using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;

namespace RestaurantQrAiOrdering.Api.Tests.Tables;

public sealed class TableEndpointTests
{
    [Fact]
    public async Task GetTable_ReturnsActiveTableByCode()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/tables/T05");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("T05", body.RootElement.GetProperty("tableCode").GetString());
        Assert.Equal("Ban 05", body.RootElement.GetProperty("displayName").GetString());
        Assert.True(body.RootElement.GetProperty("isActive").GetBoolean());
        Assert.Equal("cmc-table-t05-qr", body.RootElement.GetProperty("qrToken").GetString());
        Assert.Equal("/table/T05?qr=cmc-table-t05-qr", body.RootElement.GetProperty("customerPath").GetString());
    }

    [Fact]
    public async Task GetTable_RejectsInvalidTableCode()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/tables/table-5");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("TABLE_CODE_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task GetTable_ReturnsNotFoundForMissingActiveTable()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/tables/T99");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("TABLE_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task ResolveTableQr_ReturnsCustomerPathForActiveTable()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/tables/qr/cmc-table-t03-qr");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("T03", body.RootElement.GetProperty("tableCode").GetString());
        Assert.Equal("cmc-table-t03-qr", body.RootElement.GetProperty("qrToken").GetString());
        Assert.Equal("/table/T03?qr=cmc-table-t03-qr", body.RootElement.GetProperty("customerPath").GetString());
    }

    [Fact]
    public async Task OpenTableSession_RestoresSameSessionAcrossClients()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var firstClient = factory.CreateClient();
        using var secondClient = factory.CreateClient();

        using var firstResponse = await firstClient.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken = "cmc-table-t05-qr",
            tableCode = "T05",
            orderType = "DineIn"
        });
        using var firstBody = await JsonDocument.ParseAsync(await firstResponse.Content.ReadAsStreamAsync());
        var sessionId = firstBody.RootElement.GetProperty("sessionId").GetString();

        using var secondResponse = await secondClient.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken = "cmc-table-t05-qr",
            tableCode = "T05",
            orderType = "DineIn"
        });
        using var secondBody = await JsonDocument.ParseAsync(await secondResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, firstResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondResponse.StatusCode);
        Assert.False(string.IsNullOrWhiteSpace(sessionId));
        Assert.Equal(sessionId, secondBody.RootElement.GetProperty("sessionId").GetString());
        Assert.Equal("Open", secondBody.RootElement.GetProperty("status").GetString());
        Assert.Equal("T05", secondBody.RootElement.GetProperty("tableCode").GetString());
    }

    [Fact]
    public async Task OpenTableSession_AllowsPickupWithoutQr()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            orderType = "Pickup"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Pickup", body.RootElement.GetProperty("orderType").GetString());
        Assert.Equal("Open", body.RootElement.GetProperty("status").GetString());
        Assert.Equal("/?orderType=pickup", body.RootElement.GetProperty("customerPath").GetString());
        Assert.True(body.RootElement.GetProperty("tableCode").ValueKind is JsonValueKind.Null);
    }

    [Fact]
    public async Task OpenTableSession_RejectsQrForDifferentTable()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken = "cmc-table-t05-qr",
            tableCode = "T06",
            orderType = "DineIn"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("QR_TABLE_MISMATCH", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task GetTableSession_ReturnsGoneForExpiredSession()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var createResponse = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken = "cmc-table-t02-qr",
            orderType = "DineIn"
        });
        using var createBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var sessionId = createBody.RootElement.GetProperty("sessionId").GetString()!;

        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var session = await db.TableSessions.SingleAsync(s => s.Id == sessionId);
            session.ExpiresAt = DateTimeOffset.UtcNow.AddMinutes(-1);
            await db.SaveChangesAsync();
        }

        using var response = await client.GetAsync($"/api/table-sessions/{sessionId}");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Gone, response.StatusCode);
        Assert.Equal("TABLE_SESSION_EXPIRED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }
}
