using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Orders;

public sealed class OrderEndpointTests
{
    [Fact]
    public async Task CreateOrder_EmitsOrderCreatedEvent()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();

        using var response = await CreateDineInOrderAsync(client, factory);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.Single(realtime.Created);
        Assert.Equal(body.RootElement.GetProperty("orderCode").GetString(), realtime.Created[0].OrderCode);
        Assert.Equal("DineIn", realtime.Created[0].OrderType);
        Assert.Equal("T05", realtime.Created[0].TableCode);
        Assert.Equal("Placed", realtime.Created[0].Status);
    }

    [Fact]
    public async Task CreateOrder_PersistsOrderSoAnotherClientCanReadIt()
    {
        await using var factory = new TestWebApplicationFactory();
        using var firstClient = factory.CreateClient();
        using var secondClient = factory.CreateClient();

        using var createResponse = await CreateDineInOrderAsync(firstClient, factory);
        using var createBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var orderCode = createBody.RootElement.GetProperty("orderCode").GetString();

        using var getResponse = await secondClient.GetAsync($"/api/orders/{orderCode}");
        using var getBody = await JsonDocument.ParseAsync(await getResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, getResponse.StatusCode);
        Assert.Equal(orderCode, getBody.RootElement.GetProperty("orderCode").GetString());
        Assert.Equal("T05", getBody.RootElement.GetProperty("tableCode").GetString());
        Assert.Equal(90000, getBody.RootElement.GetProperty("subtotalAmount").GetDecimal());
    }

    [Fact]
    public async Task ListOrders_ReturnsDatabaseOrdersForKitchenPollingFallback()
    {
        await using var factory = new TestWebApplicationFactory();
        using var customerClient = factory.CreateClient();
        using var kitchenClient = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(customerClient, factory);
        kitchenClient.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Kitchen);

        using var response = await kitchenClient.GetAsync("/api/orders?tableCode=T05");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.True(body.RootElement.GetProperty("total").GetInt32() >= 1);
        var order = body.RootElement.GetProperty("orders")
            .EnumerateArray()
            .Single(element => element.GetProperty("orderCode").GetString() == orderCode);
        Assert.Equal("T05", order.GetProperty("tableCode").GetString());
        Assert.Equal("Placed", order.GetProperty("status").GetString());
        Assert.Equal("Unpaid", order.GetProperty("paymentStatus").GetString());
    }

    [Fact]
    public async Task ListOrders_FiltersByUpdatedSinceAfterKitchenStatusChange()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);
        var updatedSince = DateTimeOffset.UtcNow.AddMinutes(-1);
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Kitchen);

        using var updateResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new
        {
            status = "Preparing"
        });
        Assert.Equal(HttpStatusCode.OK, updateResponse.StatusCode);

        using var response = await client.GetAsync($"/api/orders?status=Preparing&updatedSince={Uri.EscapeDataString(updatedSince.ToString("O"))}");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var order = Assert.Single(body.RootElement.GetProperty("orders").EnumerateArray());
        Assert.Equal(orderCode, order.GetProperty("orderCode").GetString());
        Assert.Equal("Preparing", order.GetProperty("status").GetString());
    }

    [Fact]
    public async Task ListOrders_RequiresOperationsRole()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        await CreateOrderCodeAsync(client, factory);

        using var anonymousResponse = await client.GetAsync("/api/orders");
        Assert.Equal(HttpStatusCode.Unauthorized, anonymousResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Customer);
        using var customerResponse = await client.GetAsync("/api/orders");
        Assert.Equal(HttpStatusCode.Forbidden, customerResponse.StatusCode);
    }

    [Fact]
    public async Task UpdateOrderStatus_RequiresStaffOrAdminAndEmitsEvent()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);

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
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        var order = await CreateOrderAsync(client, factory);
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
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        var order = await CreateOrderAsync(client, factory);
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
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

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

    [Fact]
    public async Task CreateOrder_RejectsMalformedJsonWithStandardError()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();

        using var response = await client.PostAsync(
            "/api/orders",
            new StringContent("{", Encoding.UTF8, "application/json"));
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("REQUEST_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
        Assert.True(body.RootElement.GetProperty("error").TryGetProperty("details", out var details));
        Assert.Equal(JsonValueKind.Object, details.ValueKind);
        Assert.Empty(realtime.Created);
    }

    [Fact]
    public async Task CreateOrder_RejectsMissingItemsWithStandardError()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod = "COD",
            deliveryInfo = (object?)null,
            items = Array.Empty<object>()
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("ORDER_ITEMS_REQUIRED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
        Assert.Empty(realtime.Created);
    }

    [Fact]
    public async Task UpdateOrderStatus_RejectsNullBody()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var response = await client.PatchAsync($"/api/orders/{orderCode}/status", content: null);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("REQUEST_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
        Assert.Empty(realtime.StatusChanged);
    }

    [Fact]
    public async Task UpdateOrderStatus_RejectsCancellationAfterPreparing()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var preparingResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new
        {
            status = "Preparing"
        });

        Assert.Equal(HttpStatusCode.OK, preparingResponse.StatusCode);

        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new
        {
            status = "Cancelled"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("ORDER_CANCEL_NOT_ALLOWED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
        Assert.Single(realtime.StatusChanged);
        Assert.Equal("Preparing", realtime.StatusChanged[0].Payload.Status);
    }

    [Fact]
    public async Task UpdateOrderStatus_RejectsCancellationWhenItemIsPreparing()
    {
        await using var factory = new TestWebApplicationFactory();
        var realtime = factory.GetRealtimeNotifier();
        realtime.Clear();
        using var client = factory.CreateClient();
        var order = await CreateOrderAsync(client, factory);
        var orderCode = order.RootElement.GetProperty("orderCode").GetString()!;
        var orderItemId = order.RootElement.GetProperty("items")[0].GetProperty("orderItemId").GetString()!;

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Kitchen);
        using var itemPreparingResponse = await client.PatchAsJsonAsync(
            $"/api/orders/{orderCode}/items/{orderItemId}/status",
            new
            {
                status = "Preparing"
            });

        Assert.Equal(HttpStatusCode.OK, itemPreparingResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new
        {
            status = "Cancelled"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("ORDER_CANCEL_NOT_ALLOWED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
        Assert.Empty(realtime.StatusChanged);
        Assert.Single(realtime.ItemStatusChanged);
        Assert.Equal("Preparing", realtime.ItemStatusChanged[0].Payload.Status);
    }

    private static async Task<HttpResponseMessage> CreateDineInOrderAsync(
        HttpClient client,
        TestWebApplicationFactory factory)
    {
        await factory.SeedDatabaseAsync();

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

    private static async Task<string> CreateOrderCodeAsync(HttpClient client, TestWebApplicationFactory factory)
    {
        using var order = await CreateOrderAsync(client, factory);
        return order.RootElement.GetProperty("orderCode").GetString()!;
    }

    private static async Task<JsonDocument> CreateOrderAsync(HttpClient client, TestWebApplicationFactory factory)
    {
        using var response = await CreateDineInOrderAsync(client, factory);
        var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);

        return body;
    }

    private static AuthenticationHeaderValue CreateAuthorization(TestWebApplicationFactory factory, string role)
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
}
