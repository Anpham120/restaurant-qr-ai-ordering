using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Orders;

public sealed class OrderEndpointTests
{
    private const string TestTableCode = "T05";
    private const string TestQrToken = "cmc-table-t05-qr";

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
        var accessToken = createBody.RootElement.GetProperty("customerAccessToken").GetString();
        secondClient.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, accessToken);

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
        var tableSessionId = await OpenTableSessionAsync(client, factory);

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = TestTableCode,
            qrToken = TestQrToken,
            tableSessionId,
            paymentMethod = "COD",
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
            tableCode = TestTableCode,
            paymentMethod = "COD",
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

    [Fact]
    public async Task CreateOrder_ReturnsCustomerAccessToken()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        var (_, accessToken) = await CreateOrderWithTokenAsync(client, factory);

        Assert.False(string.IsNullOrWhiteSpace(accessToken));
    }

    [Fact]
    public async Task GetOrder_WithoutAccessToken_Returns404()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var probeClient = factory.CreateClient();
        var (orderCode, _) = await CreateOrderWithTokenAsync(createClient, factory);

        using var response = await probeClient.GetAsync($"/api/orders/{orderCode}");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("ORDER_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task GetOrder_WithWrongAccessToken_Returns404()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var probeClient = factory.CreateClient();
        var (orderCode, _) = await CreateOrderWithTokenAsync(createClient, factory);
        probeClient.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, "not-the-real-token");

        using var response = await probeClient.GetAsync($"/api/orders/{orderCode}");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("ORDER_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task GetOrder_WithCorrectAccessToken_Returns200()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var probeClient = factory.CreateClient();
        var (orderCode, accessToken) = await CreateOrderWithTokenAsync(createClient, factory);
        probeClient.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, accessToken);

        using var response = await probeClient.GetAsync($"/api/orders/{orderCode}");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(orderCode, body.RootElement.GetProperty("orderCode").GetString());
    }

    [Fact]
    public async Task GetOrder_AsOperatorWithoutToken_Returns200()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var staffClient = factory.CreateClient();
        var (orderCode, _) = await CreateOrderWithTokenAsync(createClient, factory);
        staffClient.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var response = await staffClient.GetAsync($"/api/orders/{orderCode}");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(orderCode, body.RootElement.GetProperty("orderCode").GetString());
    }

    [Fact]
    public async Task CompleteOrder_WithoutConfirmedPayment_Returns400()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var preparingResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Preparing" });
        Assert.Equal(HttpStatusCode.OK, preparingResponse.StatusCode);
        using var readyResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Ready" });
        Assert.Equal(HttpStatusCode.OK, readyResponse.StatusCode);

        using var completeResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Completed" });
        using var body = await JsonDocument.ParseAsync(await completeResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, completeResponse.StatusCode);
        Assert.Equal("ORDER_COMPLETE_REQUIRES_PAYMENT", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CompleteOrder_WithConfirmedPayment_Returns200()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "cash-001", note = "Thu tien mat tai quay" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        using var preparingResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Preparing" });
        Assert.Equal(HttpStatusCode.OK, preparingResponse.StatusCode);
        using var readyResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Ready" });
        Assert.Equal(HttpStatusCode.OK, readyResponse.StatusCode);

        using var completeResponse = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Completed" });
        using var body = await JsonDocument.ParseAsync(await completeResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, completeResponse.StatusCode);
        Assert.Equal("Completed", body.RootElement.GetProperty("status").GetString());
    }

    [Fact]
    public async Task CreateOrder_AssignsDistinctSequentialOrderCodes()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        var firstCode = await CreateOrderCodeAsync(client, factory);
        var secondCode = await CreateOrderCodeAsync(client, factory);

        Assert.StartsWith("ORD-", firstCode);
        Assert.StartsWith("ORD-", secondCode);
        Assert.NotEqual(firstCode, secondCode);
    }

    [Fact]
    public async Task UpdateOrderStatus_RejectsNoOpTransition()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Placed" });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(
            "ORDER_STATUS_TRANSITION_INVALID",
            body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task UpdateOrderItemStatus_RejectsBackwardTransition()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var order = await CreateOrderAsync(client, factory);
        var orderCode = order.RootElement.GetProperty("orderCode").GetString()!;
        var orderItemId = order.RootElement.GetProperty("items")[0].GetProperty("orderItemId").GetString()!;
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Kitchen);

        using var forwardResponse = await client.PatchAsJsonAsync(
            $"/api/orders/{orderCode}/items/{orderItemId}/status", new { status = "Ready" });
        Assert.Equal(HttpStatusCode.OK, forwardResponse.StatusCode);

        using var backwardResponse = await client.PatchAsJsonAsync(
            $"/api/orders/{orderCode}/items/{orderItemId}/status", new { status = "Preparing" });
        using var body = await JsonDocument.ParseAsync(await backwardResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, backwardResponse.StatusCode);
        Assert.Equal(
            "ORDER_ITEM_STATUS_TRANSITION_INVALID",
            body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CancelOrder_CascadesItemCancellation()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Cancelled" });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Cancelled", body.RootElement.GetProperty("status").GetString());
        var item = Assert.Single(body.RootElement.GetProperty("items").EnumerateArray());
        Assert.Equal("Cancelled", item.GetProperty("status").GetString());
    }

    [Fact]
    public async Task CreateOrder_RejectsQuantityAboveCap()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod = "COD",
            items = new[] { new { menuItemId = "m_001", quantity = 100 } }
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(
            "ORDER_ITEM_QUANTITY_INVALID",
            body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CreateOrder_RejectsTooManyItemLines()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

        var items = Enumerable.Range(0, 51)
            .Select(index => new { menuItemId = $"m_{index:000}", quantity = 1 })
            .ToArray();
        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod = "COD",
            items
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(
            "ORDER_ITEMS_TOO_MANY",
            body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CreateOrder_RejectsDuplicateMenuItem()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod = "COD",
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 1 },
                new { menuItemId = "m_001", quantity = 2 }
            }
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(
            "ORDER_ITEM_DUPLICATE",
            body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CreateOrder_RejectsPickupOrderType()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "Pickup",
            paymentMethod = "COD",
            pickupInfo = new { customerName = "Nguyen Van A", phoneNumber = "0901234567" },
            items = new[] { new { menuItemId = "m_001", quantity = 1 } }
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(
            "ORDER_TYPE_INVALID",
            body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CreateOrder_RequiresActiveTableSession()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = TestTableCode,
            qrToken = TestQrToken,
            paymentMethod = "COD",
            items = new[] { new { menuItemId = "m_001", quantity = 1 } }
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("TABLE_SESSION_REQUIRED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CreateOrder_DineIn_BindsToTableSession()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await CreateDineInOrderAsync(client, factory);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        Assert.False(string.IsNullOrWhiteSpace(body.RootElement.GetProperty("tableSessionId").GetString()));
    }

    [Fact]
    public async Task UpdateOrderStatus_AppendsHistoryWithActorRole()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var orderCode = await CreateOrderCodeAsync(client, factory);
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var response = await client.PatchAsJsonAsync($"/api/orders/{orderCode}/status", new { status = "Preparing" });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var events = body.RootElement.GetProperty("events").EnumerateArray().ToList();
        // The anonymous create logs Placed as the Customer; the Staff status change adds Preparing.
        Assert.Contains(events, element =>
            element.GetProperty("status").GetString() == "Placed"
            && element.GetProperty("source").GetString() == "Status"
            && element.GetProperty("changedByRole").GetString() == "Customer");
        var preparing = events.First(element => element.GetProperty("status").GetString() == "Preparing");
        Assert.Equal("Status", preparing.GetProperty("source").GetString());
        Assert.Equal("Staff", preparing.GetProperty("changedByRole").GetString());
    }

    [Fact]
    public async Task CompleteOrder_ClosesTableSessionSoNextOrderOpensFresh()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        using var firstCreate = await CreateDineInOrderAsync(client, factory);
        using var firstBody = await JsonDocument.ParseAsync(await firstCreate.Content.ReadAsStreamAsync());
        var firstCode = firstBody.RootElement.GetProperty("orderCode").GetString()!;
        var firstSession = firstBody.RootElement.GetProperty("tableSessionId").GetString();

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var confirm = await client.PostAsJsonAsync(
            $"/api/orders/{firstCode}/payment/confirm",
            new { note = "Thu tien mat tai quay" });
        Assert.Equal(HttpStatusCode.OK, confirm.StatusCode);
        foreach (var status in new[] { "Preparing", "Ready", "Completed" })
        {
            using var step = await client.PatchAsJsonAsync($"/api/orders/{firstCode}/status", new { status });
            Assert.Equal(HttpStatusCode.OK, step.StatusCode);
        }

        // The completed order closed its session, so a new order on the same table opens a fresh one.
        using var secondCreate = await CreateDineInOrderAsync(client, factory);
        using var secondBody = await JsonDocument.ParseAsync(await secondCreate.Content.ReadAsStreamAsync());
        var secondSession = secondBody.RootElement.GetProperty("tableSessionId").GetString();

        Assert.False(string.IsNullOrWhiteSpace(firstSession));
        Assert.False(string.IsNullOrWhiteSpace(secondSession));
        Assert.NotEqual(firstSession, secondSession);
    }

    private static async Task<(string OrderCode, string AccessToken)> CreateOrderWithTokenAsync(
        HttpClient client,
        TestWebApplicationFactory factory)
    {
        using var order = await CreateOrderAsync(client, factory);
        return (
            order.RootElement.GetProperty("orderCode").GetString()!,
            order.RootElement.GetProperty("customerAccessToken").GetString()!);
    }

    private static async Task<HttpResponseMessage> CreateDineInOrderAsync(
        HttpClient client,
        TestWebApplicationFactory factory)
    {
        await factory.SeedDatabaseAsync();

        return await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = TestTableCode,
            qrToken = TestQrToken,
            tableSessionId = await OpenTableSessionAsync(client, factory),
            paymentMethod = "COD",
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 2 }
            }
        });
    }

    private static async Task<string> OpenTableSessionAsync(
        HttpClient client,
        TestWebApplicationFactory factory)
    {
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken = TestQrToken,
            tableCode = TestTableCode
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return body.RootElement.GetProperty("sessionId").GetString()!;
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
