using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace RestaurantQrAiOrdering.Api.Tests.Tables;

public sealed class TableEndpointTests
{
    [Fact]
    public async Task GetTable_ReturnsActiveTableByCode()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/tables/T05");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("T05", body.RootElement.GetProperty("tableCode").GetString());
        Assert.Equal("Ban 05", body.RootElement.GetProperty("displayName").GetString());
        Assert.True(body.RootElement.GetProperty("isActive").GetBoolean());
    }

    [Fact]
    public async Task GetTable_RejectsInvalidTableCode()
    {
        await using var factory = new TestWebApplicationFactory();
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
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/tables/T99");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("TABLE_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }
}
