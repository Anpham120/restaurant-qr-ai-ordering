using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Tables;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class TableSessionResumeStateTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public TableSessionResumeStateTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    public static TheoryData<int, OrderStatus[], PaymentStatus?, TableSessionResumeState> ResumeCases => new()
    {
        { 0, [], null, TableSessionResumeState.New },
        { 2, [], null, TableSessionResumeState.CartPending },
        { 0, [OrderStatus.Cancelled], null, TableSessionResumeState.New },
        { 0, [OrderStatus.Placed], null, TableSessionResumeState.OrderInProgress },
        { 0, [OrderStatus.Served, OrderStatus.Ready], null, TableSessionResumeState.OrderInProgress },
        { 0, [OrderStatus.Served, OrderStatus.Completed], PaymentStatus.Failed, TableSessionResumeState.ReadyForPayment },
        { 0, [OrderStatus.Preparing], PaymentStatus.Pending, TableSessionResumeState.PaymentPending },
        { 0, [OrderStatus.Preparing], PaymentStatus.Confirmed, TableSessionResumeState.Paid }
    };

    [Theory]
    [MemberData(nameof(ResumeCases))]
    public void TestV51_ResumeStateUsesDeterministicPrecedence(
        int cartItemCount,
        OrderStatus[] orderStatuses,
        PaymentStatus? invoiceStatus,
        TableSessionResumeState expected)
    {
        Assert.Equal(
            expected,
            TableSessionResumeStateResolver.Resolve(cartItemCount, orderStatuses, invoiceStatus));
    }

    [Fact]
    public async Task TestV51_RepeatedScansReuseOneOpenSessionAndReturnResumeState()
    {
        using var client = factory.CreateClient();
        var suffix = Guid.NewGuid().ToString("N");
        var tableId = $"table-resume-{suffix}";
        const string tableCode = "T98";
        var qrToken = $"resume-{suffix}";

        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.RestaurantTables.Add(new RestaurantTable
            {
                Id = tableId,
                TableCode = tableCode,
                DisplayName = "Resume state test table",
                IsActive = true,
                QrToken = qrToken
            });
            await db.SaveChangesAsync();
        }

        using var firstResponse = await client.PostAsJsonAsync(
            "/api/table-sessions",
            new { qrToken, tableCode });
        using var secondResponse = await client.PostAsJsonAsync(
            "/api/table-sessions",
            new { qrToken, tableCode });
        firstResponse.EnsureSuccessStatusCode();
        secondResponse.EnsureSuccessStatusCode();
        using var first = await ReadJsonAsync(firstResponse);
        using var second = await ReadJsonAsync(secondResponse);

        var sessionId = first.RootElement.GetProperty("sessionId").GetString();
        Assert.Equal(sessionId, second.RootElement.GetProperty("sessionId").GetString());
        Assert.Equal("New", first.RootElement.GetProperty("resumeState").GetString());
        Assert.Equal("New", second.RootElement.GetProperty("resumeState").GetString());

        using var verificationScope = factory.Services.CreateScope();
        var verificationDb = verificationScope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        Assert.Equal(
            1,
            await verificationDb.TableSessions.CountAsync(session =>
                session.RestaurantTableId == tableId &&
                session.Status == TableSessionStatus.Open));
    }

    [Fact]
    public async Task TestV51_ConcurrentScansStillCreateAtMostOneOpenSession()
    {
        var suffix = Guid.NewGuid().ToString("N");
        var tableId = $"table-concurrent-resume-{suffix}";
        const string tableCode = "T97";
        var qrToken = $"concurrent-resume-{suffix}";
        using (var scope = factory.Services.CreateScope())
        {
            var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
            db.RestaurantTables.Add(new RestaurantTable
            {
                Id = tableId,
                TableCode = tableCode,
                DisplayName = "Concurrent resume state test table",
                IsActive = true,
                QrToken = qrToken
            });
            await db.SaveChangesAsync();
        }

        var clients = Enumerable.Range(0, 6).Select(_ => factory.CreateClient()).ToList();
        try
        {
            var responses = await Task.WhenAll(clients.Select(client => client.PostAsJsonAsync(
                "/api/table-sessions",
                new { qrToken, tableCode })));
            try
            {
                foreach (var response in responses)
                {
                    response.EnsureSuccessStatusCode();
                }

                var payloads = await Task.WhenAll(responses.Select(ReadJsonAsync));
                using var first = payloads[0];
                var sessionId = first.RootElement.GetProperty("sessionId").GetString();
                Assert.All(
                    payloads.Skip(1),
                    payload => Assert.Equal(sessionId, payload.RootElement.GetProperty("sessionId").GetString()));
                foreach (var payload in payloads.Skip(1))
                {
                    payload.Dispose();
                }
            }
            finally
            {
                foreach (var response in responses)
                {
                    response.Dispose();
                }
            }
        }
        finally
        {
            foreach (var client in clients)
            {
                client.Dispose();
            }
        }

        using var verificationScope = factory.Services.CreateScope();
        var verificationDb = verificationScope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        Assert.Equal(
            1,
            await verificationDb.TableSessions.CountAsync(session =>
                session.RestaurantTableId == tableId &&
                session.Status == TableSessionStatus.Open));
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }
}
