using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using RestaurantQrAiOrdering.Api.Data;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class PaymentLifecycleTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public PaymentLifecycleTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Theory]
    [InlineData("confirm")]
    [InlineData("fail")]
    public async Task TestV1_RefundedPaymentRejectsManualTransitionsWithoutNewTransaction(string command)
    {
        using var client = factory.CreateClient();
        var adminToken = await SignInAsAdminAsync(client);
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);

        var tableIndex = command == "confirm" ? 0 : 1;
        var order = await CreateDineInOrderAsync(client, tableIndex);
        await RequestPaymentAsync(client, order.OrderCode, order.AccessToken);
        await ConfirmPaymentAsync(client, order.OrderCode, "Initial confirmation.");
        await RefundPaymentAsync(client, order.OrderCode, "Refund before regression check.");

        var refunded = await GetPaymentSnapshotAsync(client, order.OrderCode, order.AccessToken);
        using var rejected = command == "confirm"
            ? await ConfirmPaymentAsync(client, order.OrderCode, "Confirmation after refund must fail.")
            : await FailPaymentAsync(client, order.OrderCode, "Failure after refund must fail.");
        var afterRejectedConfirmation = await GetPaymentSnapshotAsync(client, order.OrderCode, order.AccessToken);

        Assert.Equal(HttpStatusCode.BadRequest, rejected.StatusCode);
        Assert.Equal("Refunded", refunded.Status);
        Assert.Equal(refunded.Status, afterRejectedConfirmation.Status);
        Assert.Equal(refunded.TransactionCount, afterRejectedConfirmation.TransactionCount);
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

    private static async Task<(string OrderCode, string AccessToken)> CreateDineInOrderAsync(
        HttpClient client,
        int tableIndex)
    {
        var tableSession = await TableSessionTestHelpers.OpenFreshTableSessionAsync(client, tableIndex);

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
                tableCode = tableSession.TableCode,
                qrToken = tableSession.QrToken,
                tableSessionId = tableSession.Id,
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
        createRequest.Headers.Add("Idempotency-Key", $"payment-lifecycle-{Guid.NewGuid():N}");

        using var createResponse = await client.SendAsync(createRequest);
        createResponse.EnsureSuccessStatusCode();
        using var order = await ReadJsonAsync(createResponse);
        return (
            order.RootElement.GetProperty("orderCode").GetString()!,
            order.RootElement.GetProperty("customerAccessToken").GetString()!);
    }

    private static async Task RequestPaymentAsync(HttpClient client, string orderCode, string accessToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, $"/api/orders/{orderCode}/payment/request")
        {
            Content = JsonContent.Create(new { method = "COD" })
        };
        request.Headers.Add("X-Order-Token", accessToken);
        request.Headers.Add("Idempotency-Key", $"payment-request-{Guid.NewGuid():N}");

        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private static async Task<HttpResponseMessage> ConfirmPaymentAsync(HttpClient client, string orderCode, string note)
    {
        return await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/confirm",
            new { note });
    }

    private static async Task<HttpResponseMessage> FailPaymentAsync(HttpClient client, string orderCode, string note)
    {
        return await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/fail",
            new { note });
    }

    private static async Task RefundPaymentAsync(HttpClient client, string orderCode, string note)
    {
        using var response = await client.PostAsJsonAsync(
            $"/api/orders/{orderCode}/payment/refund",
            new { note });
        response.EnsureSuccessStatusCode();
    }

    private static async Task<PaymentSnapshot> GetPaymentSnapshotAsync(HttpClient client, string orderCode, string accessToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, $"/api/orders/{orderCode}/payment");
        request.Headers.Add("X-Order-Token", accessToken);
        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
        using var payment = await ReadJsonAsync(response);
        return new PaymentSnapshot(
            payment.RootElement.GetProperty("status").GetString()!,
            payment.RootElement.GetProperty("transactions").GetArrayLength());
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    private sealed record PaymentSnapshot(string Status, int TransactionCount);
}

public sealed class RestaurantApiFactory : WebApplicationFactory<Program>
{
    public const string AdminEmail = "payment-test-admin@local.test";
    public const string AdminPassword = "PaymentTestPass!2026";
    private readonly string databaseName = $"RestaurantTests-{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");
        builder.ConfigureAppConfiguration((_, configuration) =>
        {
            configuration.AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["Jwt:SigningKey"] = "payment-lifecycle-test-signing-key-32-bytes",
                ["BOOTSTRAP_ADMIN_EMAIL"] = AdminEmail,
                ["BOOTSTRAP_ADMIN_PASSWORD"] = AdminPassword,
                ["Payments:VietQr:BankId"] = "970436",
                ["Payments:VietQr:AccountNumber"] = "1234567890",
                ["Payments:VietQr:AccountName"] = "CMC TEST"
            });
        });
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<DbContextOptions<RestaurantDbContext>>();
            services.RemoveAll<RestaurantDbContext>();
            services.AddDbContext<RestaurantDbContext>(options =>
                options.UseInMemoryDatabase(databaseName));
        });
    }
}
