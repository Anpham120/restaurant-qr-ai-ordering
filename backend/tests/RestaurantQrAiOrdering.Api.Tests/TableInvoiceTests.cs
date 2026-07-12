using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;
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
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var cancelledItem = db.Orders
                .Include(order => order.OrderItems)
                .First(order => order.TableSessionId == sessionId)
                .OrderItems.First();
            cancelledItem.Status = OrderItemStatus.Cancelled;
            await db.SaveChangesAsync();
        }

        using var invoiceRequest = new HttpRequestMessage(
            HttpMethod.Get,
            $"/api/table-sessions/{sessionId}/invoice");
        invoiceRequest.Headers.Add("X-Table-Session-Token", sessionToken);
        using var invoiceResponse = await client.SendAsync(invoiceRequest);
        invoiceResponse.EnsureSuccessStatusCode();
        using var invoice = await ReadJsonAsync(invoiceResponse);

        Assert.Equal(2, invoice.RootElement.GetProperty("orderRounds").GetArrayLength());
        Assert.Equal(unitPrice * 2, invoice.RootElement.GetProperty("subtotalAmount").GetDecimal());
        Assert.Equal(unitPrice * 2, invoice.RootElement.GetProperty("totalAmount").GetDecimal());
        Assert.Equal(2, invoice.RootElement.GetProperty("items")[0].GetProperty("quantity").GetInt32());
        Assert.Equal("NotRequested", invoice.RootElement.GetProperty("status").GetString());
    }

    [Fact]
    public async Task TestV14_V17_V18_V19_PaymentRequestSettlesWholeSession()
    {
        using var client = factory.CreateClient();
        var suffix = Guid.NewGuid().ToString("N")[..6].ToUpperInvariant();
        var tableCode = "T91";
        var qrToken = $"invoice-payment-{Guid.NewGuid():N}";
        var promotionCode = $"P{suffix}";
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.RestaurantTables.Add(new RestaurantTable
            {
                Id = $"table-invoice-payment-{Guid.NewGuid():N}",
                TableCode = tableCode,
                DisplayName = "Table Invoice Payment Test",
                QrToken = qrToken,
                IsActive = true
            });
            db.Promotions.Add(new Promotion
            {
                Id = $"promo_{Guid.NewGuid():N}",
                Code = promotionCode,
                Name = "Table invoice test promotion",
                Type = PromotionType.Percentage,
                DiscountValue = 10m,
                IsActive = true
            });
            await db.SaveChangesAsync();
        }

        using var sessionResponse = await client.PostAsJsonAsync("/api/table-sessions", new { qrToken, tableCode });
        Assert.True(
            sessionResponse.IsSuccessStatusCode,
            await sessionResponse.Content.ReadAsStringAsync());
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

        var paymentPayload = new
        {
            method = "VietQR",
            promotionCode,
            customerPhoneNumber = "0909000111"
        };
        var idempotencyKey = $"invoice-payment-{Guid.NewGuid():N}";
        using var paymentRequest = CreateInvoicePaymentRequest(sessionId, sessionToken, idempotencyKey, paymentPayload);
        using var paymentResponse = await client.SendAsync(paymentRequest);
        Assert.True(
            paymentResponse.IsSuccessStatusCode,
            await paymentResponse.Content.ReadAsStringAsync());
        using var payment = await ReadJsonAsync(paymentResponse);
        var invoice = payment.RootElement.GetProperty("invoice");
        var subtotal = unitPrice * 3;

        Assert.Equal(2, invoice.GetProperty("orderRounds").GetArrayLength());
        Assert.Equal(subtotal, invoice.GetProperty("subtotalAmount").GetDecimal());
        Assert.Equal(subtotal * 0.1m, invoice.GetProperty("discountAmount").GetDecimal());
        Assert.Equal(subtotal * 0.9m, invoice.GetProperty("totalAmount").GetDecimal());
        Assert.Equal(promotionCode, invoice.GetProperty("promotionCode").GetString());
        Assert.Equal("0909000111", invoice.GetProperty("customerPhoneNumber").GetString());
        Assert.Equal("Pending", invoice.GetProperty("status").GetString());
        Assert.Equal("VietQR", invoice.GetProperty("method").GetString());
        Assert.Equal(JsonValueKind.Object, invoice.GetProperty("vietQr").ValueKind);
        var paymentId = payment.RootElement.GetProperty("payment").GetProperty("paymentId").GetString();

        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.Promotions.Single(item => item.Code == promotionCode).IsActive = false;
            await db.SaveChangesAsync();
        }
        using var replayRequest = CreateInvoicePaymentRequest(sessionId, sessionToken, idempotencyKey, paymentPayload);
        using var replayResponse = await client.SendAsync(replayRequest);
        replayResponse.EnsureSuccessStatusCode();
        using var replay = await ReadJsonAsync(replayResponse);
        Assert.Equal(paymentId, replay.RootElement.GetProperty("payment").GetProperty("paymentId").GetString());
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.Promotions.Single(item => item.Code == promotionCode).IsActive = true;
            await db.SaveChangesAsync();
        }

        using var blockedOrder = CreateOrderRoundRequest(tableCode, qrToken, sessionId, menuItemId, 1);
        using var blockedResponse = await client.SendAsync(blockedOrder);
        Assert.Equal(HttpStatusCode.Conflict, blockedResponse.StatusCode);
        using var blockedError = await ReadJsonAsync(blockedResponse);
        Assert.Equal(
            "TABLE_INVOICE_PAYMENT_PENDING",
            blockedError.RootElement.GetProperty("error").GetProperty("code").GetString());

        using var refreshedInvoiceRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/table-sessions/{sessionId}/invoice");
        refreshedInvoiceRequest.Headers.Add("X-Table-Session-Token", sessionToken);
        using var refreshedInvoiceResponse = await client.SendAsync(refreshedInvoiceRequest);
        refreshedInvoiceResponse.EnsureSuccessStatusCode();
        using var refreshedInvoice = await ReadJsonAsync(refreshedInvoiceResponse);
        Assert.Equal(JsonValueKind.Object, refreshedInvoice.RootElement.GetProperty("vietQr").ValueKind);

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", await SignInAsAdminAsync(client));
        using var sessionOrdersRequest = new HttpRequestMessage(HttpMethod.Get, $"/api/table-sessions/{sessionId}/orders");
        sessionOrdersRequest.Headers.Add("X-Table-Session-Token", sessionToken);
        using var sessionOrdersResponse = await client.SendAsync(sessionOrdersRequest);
        sessionOrdersResponse.EnsureSuccessStatusCode();
        using var sessionOrders = await ReadJsonAsync(sessionOrdersResponse);
        var firstOrder = sessionOrders.RootElement.GetProperty("orders")[0];
        var firstOrderCode = firstOrder.GetProperty("orderCode").GetString()!;
        var firstOrderItemId = firstOrder.GetProperty("items")[0].GetProperty("orderItemId").GetString()!;
        using var blockedItemCancellation = await client.PatchAsJsonAsync(
            $"/api/orders/{firstOrderCode}/items/{firstOrderItemId}/status",
            new { status = "Cancelled" });
        Assert.Equal(HttpStatusCode.Conflict, blockedItemCancellation.StatusCode);
        using var blockedOrderCancellation = await client.PatchAsJsonAsync(
            $"/api/orders/{firstOrderCode}/status",
            new { status = "Cancelled" });
        Assert.Equal(HttpStatusCode.Conflict, blockedOrderCancellation.StatusCode);

        using var cancelResponse = await client.PostAsJsonAsync(
            $"/api/table-sessions/{sessionId}/invoice/payment/cancel",
            new { note = "Khách muốn gọi thêm món." });
        cancelResponse.EnsureSuccessStatusCode();
        using var cancelledInvoice = await ReadJsonAsync(cancelResponse);
        Assert.Equal("Cancelled", cancelledInvoice.RootElement.GetProperty("status").GetString());
        Assert.Equal("Unselected", cancelledInvoice.RootElement.GetProperty("method").GetString());
        Assert.Equal(JsonValueKind.Null, cancelledInvoice.RootElement.GetProperty("promotionCode").ValueKind);
        Assert.Equal(JsonValueKind.Null, cancelledInvoice.RootElement.GetProperty("customerPhoneNumber").ValueKind);
        Assert.Equal(0m, cancelledInvoice.RootElement.GetProperty("discountAmount").GetDecimal());

        await CreateOrderRoundAsync(client, tableCode, qrToken, sessionId, menuItemId, 1);
        var finalPaymentPayload = new
        {
            method = "COD",
            promotionCode,
            customerPhoneNumber = "0909000111"
        };
        using var finalPaymentRequest = CreateInvoicePaymentRequest(
            sessionId,
            sessionToken,
            $"invoice-payment-{Guid.NewGuid():N}",
            finalPaymentPayload);
        using var finalPaymentResponse = await client.SendAsync(finalPaymentRequest);
        finalPaymentResponse.EnsureSuccessStatusCode();
        using (var finalPayment = await ReadJsonAsync(finalPaymentResponse))
        {
            Assert.Equal("COD", finalPayment.RootElement.GetProperty("invoice").GetProperty("method").GetString());
            Assert.Equal(JsonValueKind.Null, finalPayment.RootElement.GetProperty("vietQr").ValueKind);
        }

        using var confirmResponse = await client.PostAsJsonAsync(
            $"/api/table-sessions/{sessionId}/invoice/payment/confirm",
            new { note = "Đã thu đủ tiền." });
        confirmResponse.EnsureSuccessStatusCode();
        using var confirmedInvoice = await ReadJsonAsync(confirmResponse);
        Assert.Equal("Confirmed", confirmedInvoice.RootElement.GetProperty("status").GetString());
        Assert.Equal(unitPrice * 4 * 0.9m, confirmedInvoice.RootElement.GetProperty("totalAmount").GetDecimal());

        using var invoiceListResponse = await client.GetAsync("/api/table-invoices?status=Confirmed");
        Assert.True(
            invoiceListResponse.IsSuccessStatusCode,
            await invoiceListResponse.Content.ReadAsStringAsync());
        using var invoiceList = await ReadJsonAsync(invoiceListResponse);
        Assert.Contains(
            invoiceList.RootElement.EnumerateArray(),
            item => item.GetProperty("tableSessionId").GetString() == sessionId);

        using var reportResponse = await client.GetAsync("/api/admin/reports/summary?from=2026-01-01&to=2027-01-01");
        reportResponse.EnsureSuccessStatusCode();
        using var report = await ReadJsonAsync(reportResponse);
        Assert.True(report.RootElement.GetProperty("netRevenue").GetDecimal() >= unitPrice * 4 * 0.9m);
        Assert.Equal(1, report.RootElement.GetProperty("paidOrders").GetInt32());
        Assert.Equal(1, report.RootElement.GetProperty("dailyRevenue")[0].GetProperty("orderCount").GetInt32());

        int awardedPoints;
        decimal lifetimeSpend;
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var persistedSession = await db.TableSessions.FindAsync(sessionId);
            var member = db.LoyaltyMembers.Single(item => item.PhoneNumber == "0909000111");
            var completedOrders = db.Orders
                .Include(order => order.StatusHistory)
                .Where(order => order.TableSessionId == sessionId)
                .ToList();
            Assert.Equal(TableSessionStatus.Closed, persistedSession!.Status);
            Assert.All(completedOrders, order =>
            {
                Assert.Equal(OrderStatus.Completed, order.Status);
                Assert.Contains(order.StatusHistory, history => history.ToStatus == OrderStatus.Completed);
            });
            awardedPoints = member.Points;
            lifetimeSpend = member.LifetimeSpend;
        }

        using var duplicateConfirmResponse = await client.PostAsJsonAsync(
            $"/api/table-sessions/{sessionId}/invoice/payment/confirm",
            new { note = "Không được cộng điểm lần hai." });
        Assert.Equal(HttpStatusCode.Conflict, duplicateConfirmResponse.StatusCode);
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            var member = db.LoyaltyMembers.Single(item => item.PhoneNumber == "0909000111");
            Assert.Equal(awardedPoints, member.Points);
            Assert.Equal(lifetimeSpend, member.LifetimeSpend);
        }
    }

    [Fact]
    public void TestV16_V20_SettlementAndLoyaltyUseConcurrencyTokens()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();

        Assert.True(db.Model.FindEntityType(typeof(TableSession))!
            .FindProperty("xmin")!.IsConcurrencyToken);
        Assert.True(db.Model.FindEntityType(typeof(LoyaltyMember))!
            .FindProperty("xmin")!.IsConcurrencyToken);
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

    private static async Task CreateOrderRoundAsync(
        HttpClient client,
        string tableCode,
        string qrToken,
        string sessionId,
        string menuItemId,
        int quantity)
    {
        using var request = CreateOrderRoundRequest(tableCode, qrToken, sessionId, menuItemId, quantity);
        using var response = await client.SendAsync(request);
        response.EnsureSuccessStatusCode();
    }

    private static HttpRequestMessage CreateOrderRoundRequest(
        string tableCode,
        string qrToken,
        string sessionId,
        string menuItemId,
        int quantity)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, "/api/orders")
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
        return request;
    }

    private static HttpRequestMessage CreateInvoicePaymentRequest(
        string sessionId,
        string sessionToken,
        string idempotencyKey,
        object payload)
    {
        var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"/api/table-sessions/{sessionId}/invoice/payment-request")
        {
            Content = JsonContent.Create(payload)
        };
        request.Headers.Add("X-Table-Session-Token", sessionToken);
        request.Headers.Add("Idempotency-Key", idempotencyKey);
        return request;
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        return JsonDocument.Parse(await response.Content.ReadAsStringAsync());
    }
}
