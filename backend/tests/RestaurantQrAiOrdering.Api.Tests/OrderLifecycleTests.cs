using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Enums;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class OrderLifecycleTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public OrderLifecycleTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Theory]
    [InlineData(OrderStatus.Completed)]
    [InlineData(OrderStatus.Cancelled)]
    public async Task TestV7_TerminalOrderRejectsItemStatusMutation(OrderStatus terminalStatus)
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var order = await CreateDineInOrderAsync(client);
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var persistedOrder = await db.Orders.SingleAsync(candidate => candidate.OrderCode == order.Code);
            persistedOrder.Status = terminalStatus;
            await db.SaveChangesAsync();
        }

        using var updateResponse = await client.PatchAsJsonAsync(
            $"/api/orders/{order.Code}/items/{order.ItemId}/status",
            new { status = "Preparing" });

        Assert.Equal(HttpStatusCode.Conflict, updateResponse.StatusCode);
        using var verificationScope = factory.Services.CreateScope();
        var verificationDb = verificationScope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var verifiedOrder = await verificationDb.Orders
            .Include(candidate => candidate.OrderItems)
            .SingleAsync(candidate => candidate.OrderCode == order.Code);
        Assert.Equal(terminalStatus, verifiedOrder.Status);
        Assert.Equal(OrderItemStatus.Pending, verifiedOrder.OrderItems.Single().Status);
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

    private static async Task<CreatedOrder> CreateDineInOrderAsync(HttpClient client)
    {
        using var tablesResponse = await client.GetAsync("/api/admin/tables");
        tablesResponse.EnsureSuccessStatusCode();
        using var tables = await ReadJsonAsync(tablesResponse);
        var table = tables.RootElement.GetProperty("items")[0];
        var tableCode = table.GetProperty("tableCode").GetString()!;
        var qrToken = table.GetProperty("qrToken").GetString()!;

        using var sessionResponse = await client.PostAsJsonAsync("/api/table-sessions", new { qrToken, tableCode });
        sessionResponse.EnsureSuccessStatusCode();
        using var session = await ReadJsonAsync(sessionResponse);
        var tableSessionId = session.RootElement.GetProperty("sessionId").GetString()!;

        using var menuResponse = await client.GetAsync("/api/menu");
        menuResponse.EnsureSuccessStatusCode();
        using var menu = await ReadJsonAsync(menuResponse);
        var menuItem = menu.RootElement.GetProperty("items")
            .EnumerateArray()
            .First(item => item.GetProperty("isAvailable").GetBoolean());

        using var createRequest = new HttpRequestMessage(HttpMethod.Post, "/api/orders")
        {
            Content = JsonContent.Create(new
            {
                orderType = "DineIn",
                tableCode,
                qrToken,
                tableSessionId,
                customerPhoneNumber = "0900000000",
                items = new[]
                {
                    new
                    {
                        menuItemId = menuItem.GetProperty("id").GetString(),
                        quantity = 1
                    }
                }
            })
        };
        createRequest.Headers.Add("Idempotency-Key", $"order-lifecycle-{Guid.NewGuid():N}");

        using var createResponse = await client.SendAsync(createRequest);
        createResponse.EnsureSuccessStatusCode();
        using var created = await ReadJsonAsync(createResponse);
        return new CreatedOrder(
            created.RootElement.GetProperty("orderCode").GetString()!,
            created.RootElement.GetProperty("items")[0].GetProperty("orderItemId").GetString()!);
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    private sealed record CreatedOrder(string Code, string ItemId);
}
