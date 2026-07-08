using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Features;

public sealed class PromotionLoyaltyReportTests
{
    private const string TestTableCode = "T05";
    private const string TestQrToken = "cmc-table-t05-qr";

    [Fact]
    public async Task ValidatePromotion_ReturnsDiscount()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/promotions/validate", new
        {
            code = "GIAM10",
            subtotalAmount = 100000m
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("GIAM10", body.RootElement.GetProperty("code").GetString());
        Assert.Equal(10000m, body.RootElement.GetProperty("discountAmount").GetDecimal());
        Assert.Equal(90000m, body.RootElement.GetProperty("totalAmount").GetDecimal());
    }

    [Fact]
    public async Task ValidatePromotion_CapsAtMaxDiscount()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/promotions/validate", new
        {
            code = "GIAM10",
            subtotalAmount = 1000000m
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(20000m, body.RootElement.GetProperty("discountAmount").GetDecimal());
    }

    [Fact]
    public async Task ValidatePromotion_UnknownCode_ReturnsBadRequest()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/promotions/validate", new
        {
            code = "KHONGCO",
            subtotalAmount = 100000m
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task ValidatePromotion_BelowMinOrder_ReturnsBadRequest()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/promotions/validate", new
        {
            code = "GIAM10",
            subtotalAmount = 10000m
        });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task CreateOrder_WithPromotion_AppliesDiscount()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await CreateOrderAsync(client, factory, promotionCode: "GIAM10");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        // m_001 x2 = 90.000, GIAM10 = 10% = 9.000 (below 20.000 cap, above 50.000 min).
        Assert.Equal(90000m, body.RootElement.GetProperty("subtotalAmount").GetDecimal());
        Assert.Equal(9000m, body.RootElement.GetProperty("discountAmount").GetDecimal());
        Assert.Equal(81000m, body.RootElement.GetProperty("totalAmount").GetDecimal());
        Assert.Equal("GIAM10", body.RootElement.GetProperty("promotionCode").GetString());
    }

    [Fact]
    public async Task CreateOrder_WithInvalidPromotion_ReturnsBadRequest()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await CreateOrderAsync(client, factory, promotionCode: "KHONGCO");

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task ConfirmPayment_AccruesLoyaltyPoints()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        const string phone = "0909123456";
        using var createResponse = await CreateOrderAsync(client, factory, customerPhoneNumber: phone);
        using var created = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var orderCode = created.RootElement.GetProperty("orderCode").GetString()!;

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { note = "Thu tien mat" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        using var lookupClient = factory.CreateClient();
        using var lookupResponse = await lookupClient.GetAsync($"/api/loyalty/lookup?phone={phone}");
        using var lookup = await JsonDocument.ParseAsync(await lookupResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, lookupResponse.StatusCode);
        // Total 90.000 -> floor(90000 / 10000) = 9 points.
        Assert.Equal(9, lookup.RootElement.GetProperty("points").GetInt32());
    }

    [Fact]
    public async Task LoyaltyLookup_UnknownPhone_ReturnsZeroPoints()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/loyalty/lookup?phone=0900000000");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(0, body.RootElement.GetProperty("points").GetInt32());
    }

    [Fact]
    public async Task ReportSummary_AggregatesPaidOrders()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var createResponse = await CreateOrderAsync(client, factory);
        using var created = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var orderCode = created.RootElement.GetProperty("orderCode").GetString()!;

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { note = "Thu tien" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        using var adminClient = factory.CreateClient();
        adminClient.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Admin);
        using var reportResponse = await adminClient.GetAsync("/api/admin/reports/summary");
        using var report = await JsonDocument.ParseAsync(await reportResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, reportResponse.StatusCode);
        Assert.True(report.RootElement.GetProperty("paidOrders").GetInt32() >= 1);
        Assert.True(report.RootElement.GetProperty("netRevenue").GetDecimal() >= 90000m);
        Assert.True(report.RootElement.GetProperty("topItems").GetArrayLength() >= 1);
    }

    [Fact]
    public async Task CompletingLastTableOrder_DeletesChatMemoryForTableSession()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        var sessionId = await OpenTableSessionAsync(client, factory);
        using var chatResponse = await client.PostAsJsonAsync("/api/chat/sessions", new
        {
            tableCode = TestTableCode,
            tableSessionId = sessionId
        });
        using var chatBody = await JsonDocument.ParseAsync(await chatResponse.Content.ReadAsStreamAsync());
        var chatSessionId = chatBody.RootElement.GetProperty("chatSessionId").GetString()!;

        Assert.Equal(HttpStatusCode.Created, chatResponse.StatusCode);

        using var createResponse = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = TestTableCode,
            qrToken = TestQrToken,
            tableSessionId = sessionId,
            paymentMethod = "COD",
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 1 }
            }
        });
        using var created = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var orderCode = created.RootElement.GetProperty("orderCode").GetString()!;

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { note = "Thu tien tai ban" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        foreach (var status in new[] { "Preparing", "Ready", "Completed" })
        {
            using var statusResponse = await client.PatchAsJsonAsync(
                $"/api/orders/{orderCode}/status",
                new { status });
            Assert.Equal(HttpStatusCode.OK, statusResponse.StatusCode);
        }

        using var historyResponse = await client.GetAsync($"/api/chat/sessions/{chatSessionId}/messages");
        Assert.Equal(HttpStatusCode.NotFound, historyResponse.StatusCode);
    }

    [Fact]
    public async Task ReportSummary_RequiresStaffOrAdmin()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/admin/reports/summary");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task AdminPromotions_RequireAuthentication()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/admin/promotions");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    private static async Task<HttpResponseMessage> CreateOrderAsync(
        HttpClient client,
        TestWebApplicationFactory factory,
        string? promotionCode = null,
        string? customerPhoneNumber = null)
    {
        var sessionId = await OpenTableSessionAsync(client, factory);
        return await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = TestTableCode,
            qrToken = TestQrToken,
            tableSessionId = sessionId,
            paymentMethod = "COD",
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 2 }
            },
            promotionCode,
            customerPhoneNumber
        });
    }

    private static async Task<string> OpenTableSessionAsync(HttpClient client, TestWebApplicationFactory factory)
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
