using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.E2E;

public sealed class MultiDeviceE2ETests
{
    private const string TestTableCode = "T05";
    private const string TestQrToken = "cmc-table-t05-qr";

    [Fact]
    public async Task CustomerKitchenStaffAndChatFlow_UsesBackendStateAcrossSeparateClients()
    {
        await using var factory = new E2EWebApplicationFactory(new AvailableE2EChatAiProvider());
        await factory.SeedDatabaseAsync();

        using var customerDevice = factory.CreateClient();
        using var kitchenDevice = factory.CreateClient();
        using var staffDevice = factory.CreateClient();
        using var trackingDevice = factory.CreateClient();
        kitchenDevice.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Kitchen);
        staffDevice.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        var order = await CreateDineInOrderAsync(customerDevice, paymentMethod: "VietQR");
        var orderCode = order.RootElement.GetProperty("orderCode").GetString()!;
        var orderItemId = order.RootElement.GetProperty("items")[0].GetProperty("orderItemId").GetString()!;
        var customerAccessToken = order.RootElement.GetProperty("customerAccessToken").GetString()!;
        // Customer devices replay the per-order token the backend issued at creation.
        customerDevice.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, customerAccessToken);
        trackingDevice.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, customerAccessToken);

        using var kitchenListResponse = await kitchenDevice.GetAsync("/api/orders?tableCode=T05");
        using var kitchenListBody = await JsonDocument.ParseAsync(await kitchenListResponse.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, kitchenListResponse.StatusCode);
        Assert.Contains(
            kitchenListBody.RootElement.GetProperty("orders").EnumerateArray(),
            element => element.GetProperty("orderCode").GetString() == orderCode);

        using var itemStatusResponse = await kitchenDevice.PatchAsJsonAsync(
            $"/api/orders/{orderCode}/items/{orderItemId}/status",
            new { status = "Ready" });
        using var itemStatusBody = await JsonDocument.ParseAsync(await itemStatusResponse.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, itemStatusResponse.StatusCode);
        Assert.Equal("Ready", itemStatusBody.RootElement.GetProperty("items")[0].GetProperty("status").GetString());

        using var vietQrResponse = await customerDevice.PostAsync($"/api/orders/{orderCode}/payment/vietqr", content: null);
        using var vietQrBody = await JsonDocument.ParseAsync(await vietQrResponse.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, vietQrResponse.StatusCode);
        Assert.Equal("Pending", vietQrBody.RootElement.GetProperty("paymentStatus").GetString());

        using var paymentConfirmResponse = await staffDevice.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "e2e-bank-001", note = "E2E staff reconciliation" });
        using var paymentConfirmBody = await JsonDocument.ParseAsync(await paymentConfirmResponse.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, paymentConfirmResponse.StatusCode);
        Assert.Equal("Confirmed", paymentConfirmBody.RootElement.GetProperty("status").GetString());

        using var trackingResponse = await trackingDevice.GetAsync($"/api/orders/{orderCode}");
        using var trackingBody = await JsonDocument.ParseAsync(await trackingResponse.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, trackingResponse.StatusCode);
        Assert.Equal(orderCode, trackingBody.RootElement.GetProperty("orderCode").GetString());
        Assert.Equal("Confirmed", trackingBody.RootElement.GetProperty("paymentStatus").GetString());
        Assert.Equal("Ready", trackingBody.RootElement.GetProperty("items")[0].GetProperty("status").GetString());

        var chatSessionId = await CreateChatSessionAsync(customerDevice);
        using var chatResponse = await customerDevice.PostAsJsonAsync($"/api/chat/sessions/{chatSessionId}/messages", new
        {
            content = "Goi y mon cho ban T05 nhung khong tu them vao gio hang"
        });
        using var chatBody = await JsonDocument.ParseAsync(await chatResponse.Content.ReadAsStreamAsync());
        var suggestedActions = chatBody.RootElement.GetProperty("suggestedCartActions").EnumerateArray().ToList();
        var guardrailFlags = chatBody.RootElement.GetProperty("guardrailFlags")
            .EnumerateArray()
            .Select(flag => flag.GetString())
            .ToList();

        Assert.Equal(HttpStatusCode.OK, chatResponse.StatusCode);
        Assert.NotEmpty(suggestedActions);
        Assert.All(
            suggestedActions,
            action => Assert.True(action.GetProperty("requiresCustomerConfirmation").GetBoolean()));
        Assert.Contains("CUSTOMER_CONFIRMATION_REQUIRED", guardrailFlags);
    }

    private static async Task<JsonDocument> CreateDineInOrderAsync(HttpClient client, string paymentMethod)
    {
        var tableSessionId = await OpenTableSessionAsync(client);

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = TestTableCode,
            qrToken = TestQrToken,
            tableSessionId,
            paymentMethod,
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 2 }
            }
        });
        var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return body;
    }

    private static async Task<string> OpenTableSessionAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken = TestQrToken,
            tableCode = TestTableCode
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return body.RootElement.GetProperty("sessionId").GetString()!;
    }

    private static async Task<string> CreateChatSessionAsync(HttpClient client)
    {
        using var response = await client.PostAsync("/api/chat/sessions", content: null);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return body.RootElement.GetProperty("chatSessionId").GetString()!;
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

    private sealed class AvailableE2EChatAiProvider : IChatAiProvider
    {
        public Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken)
        {
            return Task.FromResult(new ChatAiResult(
                "Đề xuất Gỏi cuốn tôm thịt. Hệ thống chỉ đề xuất, khách cần xác nhận trước khi thêm vào giỏ.",
                ServiceAvailable: true,
                LlmProviderAvailable: true,
                Model: "test-model",
                RetrievalMethod: "tfidf",
                FastPath: null,
                SuggestedActions: [new AiSuggestedAction("m_001", 1, "Phù hợp yêu cầu")],
                GuardrailFlags: ["CUSTOMER_CONFIRMATION_REQUIRED"],
                RetrievedSources: [new RetrievedSourceResponse("live-menu", "Gỏi cuốn tôm thịt", 1.0)],
                LatencyMs: new Dictionary<string, double>()));
        }
    }

    private sealed class E2EWebApplicationFactory(IChatAiProvider provider) : TestWebApplicationFactory
    {
        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            base.ConfigureWebHost(builder);
            builder.ConfigureServices(services =>
            {
                var descriptors = services.Where(d => d.ServiceType == typeof(IChatAiProvider)).ToList();
                foreach (var descriptor in descriptors)
                {
                    services.Remove(descriptor);
                }

                services.AddSingleton(provider);
            });
        }
    }
}
