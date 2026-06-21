using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Payments;

public sealed class PaymentEndpointTests
{
    [Fact]
    public async Task GenerateVietQr_ReturnsConfiguredPayloadAndMarksPaymentPending()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, accessToken) = await CreateOrderAsync(client, factory, "VietQR");
        client.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, accessToken);

        using var response = await client.PostAsync($"/api/orders/{orderCode}/payment/vietqr", content: null);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(orderCode, body.RootElement.GetProperty("orderCode").GetString());
        Assert.Equal(90000, body.RootElement.GetProperty("amount").GetDecimal());
        Assert.Equal("970436", body.RootElement.GetProperty("bankId").GetString());
        Assert.Equal("1234567890", body.RootElement.GetProperty("accountNumber").GetString());
        Assert.Equal("CMC Restaurant", body.RootElement.GetProperty("accountName").GetString());
        Assert.Contains(orderCode, body.RootElement.GetProperty("transferContent").GetString());
        Assert.Contains("img.vietqr.io", body.RootElement.GetProperty("quickLink").GetString());
        Assert.StartsWith("data:image/png;base64,", body.RootElement.GetProperty("qrImageDataUri").GetString());
        Assert.Equal("Pending", body.RootElement.GetProperty("paymentStatus").GetString());

        using var paymentResponse = await client.GetAsync($"/api/orders/{orderCode}/payment");
        using var paymentBody = await JsonDocument.ParseAsync(await paymentResponse.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, paymentResponse.StatusCode);
        Assert.Equal("VietQR", paymentBody.RootElement.GetProperty("method").GetString());
        Assert.Equal("Pending", paymentBody.RootElement.GetProperty("status").GetString());
        Assert.Single(paymentBody.RootElement.GetProperty("transactions").EnumerateArray());
    }

    [Fact]
    public async Task ConfirmCodPayment_RequiresStaffAndPersistsTransaction()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(client, factory, "COD");

        using var unauthorizedResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "cash-receipt-001", note = "Thu tien mat tai quay" });
        Assert.Equal(HttpStatusCode.Unauthorized, unauthorizedResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var response = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "cash-receipt-001", note = "Thu tien mat tai quay" });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("COD", body.RootElement.GetProperty("method").GetString());
        Assert.Equal("Confirmed", body.RootElement.GetProperty("status").GetString());
        Assert.Equal("cash-receipt-001", body.RootElement.GetProperty("providerTransactionId").GetString());
        Assert.Equal(JsonValueKind.String, body.RootElement.GetProperty("paidAt").ValueKind);

        var transaction = Assert.Single(body.RootElement.GetProperty("transactions").EnumerateArray());
        Assert.Equal("COD", transaction.GetProperty("method").GetString());
        Assert.Equal("Confirmed", transaction.GetProperty("status").GetString());
        Assert.Equal("cash-receipt-001", transaction.GetProperty("providerTransactionId").GetString());
    }

    [Fact]
    public async Task ConfirmPayment_AppendsPaymentEventToOrderStatusHistory()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, accessToken) = await CreateOrderAsync(client, factory, "COD");

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "cash-001", note = "Thu tien mat tai quay" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = null;
        client.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, accessToken);
        using var orderResponse = await client.GetAsync($"/api/orders/{orderCode}");
        using var body = await JsonDocument.ParseAsync(await orderResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, orderResponse.StatusCode);
        var paymentEvent = Assert.Single(
            body.RootElement.GetProperty("events").EnumerateArray(),
            element => element.GetProperty("source").GetString() == "Payment");
        Assert.Equal("Staff", paymentEvent.GetProperty("changedByRole").GetString());
        Assert.Equal("Thu tien mat tai quay", paymentEvent.GetProperty("note").GetString());
    }

    [Fact]
    public async Task ConfirmPayment_RejectsFailedPayment()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(client, factory, "VietQR");
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var failResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/fail",
            new { note = "Khong doi soat duoc giao dich" });
        Assert.Equal(HttpStatusCode.OK, failResponse.StatusCode);

        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "bank-001", note = "Thu lai sau fail" });
        using var body = await JsonDocument.ParseAsync(await confirmResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, confirmResponse.StatusCode);
        Assert.Equal("PAYMENT_ALREADY_FAILED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task GetPayment_WithoutAccessToken_Returns404()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var probeClient = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(createClient, factory, "COD");

        using var response = await probeClient.GetAsync($"/api/orders/{orderCode}/payment");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("PAYMENT_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task GetPayment_WithCorrectAccessToken_Returns200()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var probeClient = factory.CreateClient();
        var (orderCode, accessToken) = await CreateOrderAsync(createClient, factory, "COD");
        probeClient.DefaultRequestHeaders.Add(OrderAccessGuard.TokenHeaderName, accessToken);

        using var response = await probeClient.GetAsync($"/api/orders/{orderCode}/payment");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(orderCode, body.RootElement.GetProperty("orderCode").GetString());
    }

    [Fact]
    public async Task GetPayment_AsOperatorWithoutToken_Returns200()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var staffClient = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(createClient, factory, "COD");
        staffClient.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var response = await staffClient.GetAsync($"/api/orders/{orderCode}/payment");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task GenerateVietQr_WithoutAccessToken_Returns404()
    {
        await using var factory = new TestWebApplicationFactory();
        using var createClient = factory.CreateClient();
        using var probeClient = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(createClient, factory, "VietQR");

        using var response = await probeClient.PostAsync($"/api/orders/{orderCode}/payment/vietqr", content: null);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("PAYMENT_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task RefundConfirmedPayment_RequiresStaffAndMarksRefunded()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(client, factory, "COD");

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "cash-001", note = "Thu tien mat tai quay" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = null;
        using var unauthorizedResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/refund",
            new { note = "Hoan tien cho khach" });
        Assert.Equal(HttpStatusCode.Unauthorized, unauthorizedResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);
        using var response = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/refund",
            new { note = "Hoan tien cho khach" });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Refunded", body.RootElement.GetProperty("status").GetString());
        Assert.Contains(
            body.RootElement.GetProperty("transactions").EnumerateArray(),
            transaction => transaction.GetProperty("status").GetString() == "Refunded");
    }

    [Fact]
    public async Task RefundPayment_RejectsUnconfirmedPayment()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(client, factory, "COD");
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var response = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/refund",
            new { note = "Hoan tien khi chua thu" });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("PAYMENT_NOT_REFUNDABLE", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task RefundPayment_RejectsNoteLongerThanLimit()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var (orderCode, _) = await CreateOrderAsync(client, factory, "COD");
        client.DefaultRequestHeaders.Authorization = CreateAuthorization(factory, UserRole.Staff);

        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { providerTransactionId = "cash-001", note = "Thu tien mat tai quay" });
        Assert.Equal(HttpStatusCode.OK, confirmResponse.StatusCode);

        using var response = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/refund",
            new { note = new string('x', 501) });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("PAYMENT_NOTE_TOO_LONG", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    private static async Task<(string OrderCode, string AccessToken)> CreateOrderAsync(
        HttpClient client,
        TestWebApplicationFactory factory,
        string paymentMethod)
    {
        await factory.SeedDatabaseAsync();

        using var response = await client.PostAsJsonAsync("/api/orders", new
        {
            orderType = "DineIn",
            tableCode = "T05",
            paymentMethod,
            deliveryInfo = (object?)null,
            items = new[]
            {
                new { menuItemId = "m_001", quantity = 2 }
            }
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return (
            body.RootElement.GetProperty("orderCode").GetString()!,
            body.RootElement.GetProperty("customerAccessToken").GetString()!);
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
