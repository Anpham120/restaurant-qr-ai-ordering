using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class OrderCartClearTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public OrderCartClearTests(RestaurantApiFactory factory) => this.factory = factory;

    [Fact]
    public async Task CreateOrderRound_ClearsSharedServerCart()
    {
        using var client = factory.CreateClient();
        var tableCode = "T77";
        var qrToken = $"cart-clear-{Guid.NewGuid():N}";
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.RestaurantTables.Add(new RestaurantTable
            {
                Id = $"table-{Guid.NewGuid():N}",
                TableCode = tableCode,
                DisplayName = "Cart clear test",
                QrToken = qrToken,
                IsActive = true,
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
        var menuItemId = menu.RootElement.GetProperty("items").EnumerateArray()
            .First(item => item.GetProperty("isAvailable").GetBoolean())
            .GetProperty("id").GetString()!;

        using var addCart = new HttpRequestMessage(HttpMethod.Post, $"/api/table-sessions/{sessionId}/cart/items")
        {
            Content = JsonContent.Create(new { menuItemId, delta = 2 }),
        };
        addCart.Headers.Add("X-Table-Session-Token", sessionToken);
        using var addCartResponse = await client.SendAsync(addCart);
        addCartResponse.EnsureSuccessStatusCode();

        using var orderRequest = new HttpRequestMessage(HttpMethod.Post, "/api/orders")
        {
            Content = JsonContent.Create(new
            {
                orderType = "DineIn",
                tableCode,
                qrToken,
                tableSessionId = sessionId,
                items = new[] { new { menuItemId, quantity = 2 } },
            }),
        };
        orderRequest.Headers.Add("Idempotency-Key", Guid.NewGuid().ToString("N"));
        orderRequest.Headers.Add("X-Table-Session-Token", sessionToken);
        using var orderResponse = await client.SendAsync(orderRequest);
        orderResponse.EnsureSuccessStatusCode();

        using var cartRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/table-sessions/{sessionId}/cart");
        cartRequest.Headers.Add("X-Table-Session-Token", sessionToken);
        using var cartResponse = await client.SendAsync(cartRequest);
        cartResponse.EnsureSuccessStatusCode();
        using var cart = await ReadJsonAsync(cartResponse);
        Assert.Equal(0, cart.RootElement.GetProperty("items").GetArrayLength());
        Assert.Equal(0, cart.RootElement.GetProperty("itemCount").GetInt32());
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        var json = await response.Content.ReadAsStringAsync();
        return JsonDocument.Parse(json);
    }
}
