using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class TableInvoiceTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public TableInvoiceTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task InvoiceAggregatesMultipleOrderRoundsInOneTableSession()
    {
        using var client = factory.CreateClient();
        var tableCode = "T90";
        var qrToken = $"invoice-test-{Guid.NewGuid():N}";
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.RestaurantTables.Add(new RestaurantTable
            {
                Id = $"table-invoice-{Guid.NewGuid():N}",
                TableCode = tableCode,
                DisplayName = "Table Invoice Test",
                QrToken = qrToken,
                IsActive = true
            });
            await db.SaveChangesAsync();
        }

        using var sessionResponse = await client.PostAsJsonAsync("/api/table-sessions", new { qrToken, tableCode });
        sessionResponse.EnsureSuccessStatusCode();
        using var session = await ReadJsonAsync(sessionResponse);
        var sessionId = session.RootElement.GetProperty("sessionId").GetString()!;
        var sessionToken = session.RootElement.GetProperty("tableSessionToken").GetString()!;

        using var menuResponse = await client.GetAsync("/api/menu");
        menuResponse.EnsureSuccessStatusCode();
        using var menu = await ReadJsonAsync(menuResponse);
        var menuItem = menu.RootElement.GetProperty("items")
            .EnumerateArray()
            .First(item => item.GetProperty("isAvailable").GetBoolean());
        var menuItemId = menuItem.GetProperty("id").GetString()!;
        var unitPrice = menuItem.GetProperty("price").GetDecimal();

        await CreateOrderRoundAsync(client, tableCode, qrToken, sessionId, menuItemId, 1);
        await CreateOrderRoundAsync(client, tableCode, qrToken, sessionId, menuItemId, 2);

        using var invoiceRequest = new HttpRequestMessage(
            HttpMethod.Get,
            $"/api/table-sessions/{sessionId}/invoice");
        invoiceRequest.Headers.Add("X-Table-Session-Token", sessionToken);
        using var invoiceResponse = await client.SendAsync(invoiceRequest);
        invoiceResponse.EnsureSuccessStatusCode();
        using var invoice = await ReadJsonAsync(invoiceResponse);

        Assert.Equal(2, invoice.RootElement.GetProperty("orderRounds").GetArrayLength());
        Assert.Equal(unitPrice * 3, invoice.RootElement.GetProperty("subtotalAmount").GetDecimal());
        Assert.Equal(unitPrice * 3, invoice.RootElement.GetProperty("totalAmount").GetDecimal());
        Assert.Equal(3, invoice.RootElement.GetProperty("items")[0].GetProperty("quantity").GetInt32());
        Assert.Equal("NotRequested", invoice.RootElement.GetProperty("status").GetString());
    }

    private static async Task CreateOrderRoundAsync(
        HttpClient client,
        string tableCode,
        string qrToken,
        string sessionId,
        string menuItemId,
        int quantity)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/orders")
        {
            Content = JsonContent.Create(new
            {
                orderType = "DineIn",
                tableCode,
                qrToken,
                tableSessionId = sessionId,
                promotionCode = (string?)null,
                customerPhoneNumber = (string?)null,
                items = new[] { new { menuItemId, quantity } }
            })
        };
        request.Headers.Add("Idempotency-Key", $"table-invoice-{Guid.NewGuid():N}");
        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        return JsonDocument.Parse(await response.Content.ReadAsStringAsync());
    }
}
