using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Orders;

public sealed class OrderEndpointTests
{
    [Fact]
    public async Task CreateOrder_EmitsOrderCreatedEvent()
    {
        var realtime = new RecordingOrderRealtimeNotifier();
        await using var factory = CreateFactory(realtime);
        using var client = factory.CreateClient();

        using var response = await CreateDineInOrderAsync(client);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.Single(realtime.Created);
        Assert.Equal(body.RootElement.GetProperty("orderCode").GetString(), realtime.Created[0].OrderCode);
        Assert.Equal("DineIn", realtime.Created[0].OrderType);
        Assert.Equal("T05", realtime.Created[0].TableCode);
        Assert.Equal("Placed", realtime.Created[0].Status);
    }

    [Fact]
    public async Task UpdateOrderStatus_RequiresStaffOrAdminAndEmitsEvent()
    {
        var realtime = new RecordingOrderRealtimeNotifier();
        await using var factory = CreateFactory(realtime);
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new
        {
            status = "Preparing"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Preparing", body.RootElement.GetProperty("status").GetString());
        Assert.Single(realtime.StatusChanged);
        Assert.Equal(orderCode, realtime.StatusChanged[0].Payload.OrderCode);
        Assert.Equal("Preparing", realtime.StatusChanged[0].Payload.Status);
        Assert.Equal("T05", realtime.StatusChanged[0].TableCode);
    }

    [Fact]
    public async Task UpdateOrderItemStatus_RequiresOperationsRoleAndEmitsEvent()
    {
        var realtime = new RecordingOrderRealtimeNotifier();
        await using var factory = CreateFactory(realtime);
        using var client = factory.CreateClient();
        var order = await CreateOrderAsync(client);
        var orderCode = order.RootElement.GetProperty("orderCode").GetString()!;
        var orderItemId = order.RootElement.GetProperty("items")[0].GetProperty("orderItemId").GetString()!;

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Kitchen);
        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/items/{orderItemId}/status", new
        {
            status = "Ready"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Ready", body.RootElement.GetProperty("items")[0].GetProperty("status").GetString());
        Assert.Single(realtime.ItemStatusChanged);
        Assert.Equal(orderCode, realtime.ItemStatusChanged[0].Payload.OrderCode);
        Assert.Equal(orderItemId, realtime.ItemStatusChanged[0].Payload.OrderItemId);
        Assert.Equal("Ready", realtime.ItemStatusChanged[0].Payload.Status);
        Assert.Equal("T05", realtime.ItemStatusChanged[0].TableCode);
    }

    [Fact]
    public async Task UpdateOrderItemStatus_RejectsCustomerRole()
    {
        var realtime = new RecordingOrderRealtimeNotifier();
        await using var factory = CreateFactory(realtime);
        using var client = factory.CreateClient();
        var order = await CreateOrderAsync(client);
        var orderCode = order.RootElement.GetProperty("orderCode").GetString()!;
        var orderItemId = order.RootElement.GetProperty("items")[0].GetProperty("orderItemId").GetString()!;

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Customer);
        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/items/{orderItemId}/status", new
        {
            status = "Ready"
        });

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
        Assert.Empty(realtime.ItemStatusChanged);
    }

    [Fact]
    public async Task CreateOrder_RejectsUnavailableMenuItem()
    {
        var realtime = new RecordingOrderRealtimeNotifier();
        await using var factory = CreateFactory(realtime);
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod = "COD",
            deliveryInfo = (object?)null,
            items = new[]
            {
                new { menuItemId = "m_004", quantity = 1 }
            }
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("MENU_ITEM_UNAVAILABLE", body.RootElement.GetProperty("error").GetProperty("code").GetString());
        Assert.Empty(realtime.Created);
    }

    private static WebApplicationFactory<Program> CreateFactory(RecordingOrderRealtimeNotifier realtime)
    {
        return new WebApplicationFactory<Program>()
            .WithWebHostBuilder(builder =>
            {
                builder.ConfigureTestServices(services =>
                {
                    services.RemoveAll<IOrderRealtimeNotifier>();
                    services.AddSingleton<IOrderRealtimeNotifier>(realtime);
                });
            });
    }

    private static async Task<HttpResponseMessage> CreateDineInOrderAsync(HttpClient client)
    {
        return await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod = "COD",
            deliveryInfo = (object?)null,
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 2 }
            }
        });
    }

    private static async Task<string> CreateOrderCodeAsync(HttpClient client)
    {
        using var order = await CreateOrderAsync(client);
        return order.RootElement.GetProperty("orderCode").GetString()!;
    }

    private static async Task<JsonDocument> CreateOrderAsync(HttpClient client)
    {
        using var response = await CreateDineInOrderAsync(client);
        var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        return body;
    }

    private static AuthenticationHeaderValue CreateAuthorization(WebApplicationFactory<Program> factory, string role)
    {
        var tokenService = factory.Services.GetRequiredService<IJwtTokenService>();
        var login = tokenService.CreateLoginResponse(new UserAccount
        {
            Id = $"usr_{role.ToLowerInvariant()}",
            FullName = $"{role} User",
            Email = $"{role.ToLowerInvariant()}@example.com",
            PasswordHash = "test-hash",
            CreatedAt = DateTimeOffset.UtcNow,
            Role = role
        });

        return new AuthenticationHeaderValue("Bearer", login.AccessToken);
    }

    private sealed class RecordingOrderRealtimeNotifier : IOrderRealtimeNotifier
    {
        public List<OrderCreatedEvent> Created { get; } = [];

        public List<(OrderStatusChangedEvent Payload, string? TableCode)> StatusChanged { get; } = [];

        public List<(OrderItemStatusChangedEvent Payload, string? TableCode)> ItemStatusChanged { get; } = [];

        public Task OrderCreatedAsync(OrderCreatedEvent payload, CancellationToken cancellationToken)
        {
            Created.Add(payload);
            return Task.CompletedTask;
        }

        public Task OrderStatusChangedAsync(
            OrderStatusChangedEvent payload,
            string? tableCode,
            CancellationToken cancellationToken)
        {
            StatusChanged.Add((payload, tableCode));
            return Task.CompletedTask;
        }

        public Task OrderItemStatusChangedAsync(
            OrderItemStatusChangedEvent payload,
            string? tableCode,
            CancellationToken cancellationToken)
        {
            ItemStatusChanged.Add((payload, tableCode));
            return Task.CompletedTask;
        }
    }
}
