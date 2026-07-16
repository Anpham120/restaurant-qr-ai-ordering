using Microsoft.EntityFrameworkCore;
using Npgsql;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class PostgresOrderingRegressionTests : IClassFixture<PostgresOrderingFixture>
{
    private readonly PostgresOrderingFixture fixture;

    public PostgresOrderingRegressionTests(PostgresOrderingFixture fixture)
    {
        this.fixture = fixture;
    }

    [Fact]
    public async Task TestV24_OrderRoundCreationRunsInsideRetryExecutionStrategy()
    {
        if (!fixture.IsAvailable)
        {
            return;
        }

        await using var db = fixture.CreateContext();
        var table = await db.RestaurantTables.SingleAsync(candidate => candidate.TableCode == "T01");
        var menuItem = await db.MenuItems.FirstAsync(candidate => candidate.IsAvailable);
        var session = CreateOpenSession(table, "ts_v24");
        db.TableSessions.Add(session);
        await db.SaveChangesAsync();

        var store = new OrderStore(db);
        var order = store.CreateOrder(
            new CreateOrderCommand(
                OrderType.DineIn.ToString(),
                table.TableCode,
                table.QrToken,
                session.Id,
                [new CreateOrderItemRequest(menuItem.Id, 1)],
                $"test-v24-{Guid.NewGuid():N}",
                "v24-request"),
            ActorContext.Customer);

        Assert.Equal(session.Id, order.TableSessionId);
        Assert.Equal(OrderStatus.Placed.ToString(), order.Status);
        Assert.Single(order.Items);
        Assert.Equal(1, await db.Orders.CountAsync(candidate => candidate.Id == order.OrderId));
    }

    [Fact]
    public async Task TestV25_ChatLookupTranslatesAndRestoresCommittedHistory()
    {
        if (!fixture.IsAvailable)
        {
            return;
        }

        string chatSessionId;
        await using (var db = fixture.CreateContext())
        {
            var table = await db.RestaurantTables.SingleAsync(candidate => candidate.TableCode == "T02");
            var session = CreateOpenSession(table, "ts_v25");
            db.TableSessions.Add(session);
            await db.SaveChangesAsync();

            var store = new DbChatStore(db);
            var created = store.CreateOrGetSession(table.TableCode, session.Id);
            chatSessionId = created.Session.Id;
            Assert.NotNull(store.AddMessage(chatSessionId, "user", "Tôi muốn món thanh mát"));
        }

        await using (var refreshedDb = fixture.CreateContext())
        {
            var restored = new DbChatStore(refreshedDb).GetSession(chatSessionId);

            Assert.NotNull(restored);
            Assert.Single(restored.Messages);
            Assert.Equal("Tôi muốn món thanh mát", restored.Messages[0].Content);
        }
    }

    private static TableSession CreateOpenSession(RestaurantTable table, string prefix)
    {
        var now = DateTimeOffset.UtcNow;
        return new TableSession
        {
            Id = $"{prefix}_{Guid.NewGuid():N}",
            RestaurantTableId = table.Id,
            RestaurantTable = table,
            TableCode = table.TableCode,
            QrToken = table.QrToken,
            OrderType = OrderType.DineIn,
            Status = TableSessionStatus.Open,
            OpenedAt = now,
            ExpiresAt = now.AddHours(1),
            CreatedAt = now,
            UpdatedAt = now
        };
    }
}

public sealed class PostgresOrderingFixture : IAsyncLifetime
{
    private string? adminConnectionString;
    private string? databaseName;

    public bool IsAvailable => ConnectionString is not null;

    public string? ConnectionString { get; private set; }

    public async Task InitializeAsync()
    {
        var configured = Environment.GetEnvironmentVariable("TEST_POSTGRES_CONNECTION_STRING");
        if (string.IsNullOrWhiteSpace(configured))
        {
            if (string.Equals(Environment.GetEnvironmentVariable("CI"), "true", StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(
                    "TEST_POSTGRES_CONNECTION_STRING is required in CI for PostgreSQL regression coverage.");
            }

            return;
        }

        var adminBuilder = new NpgsqlConnectionStringBuilder(configured);
        adminConnectionString = adminBuilder.ConnectionString;
        databaseName = $"restaurant_regression_{Guid.NewGuid():N}";

        await using (var admin = new NpgsqlConnection(adminConnectionString))
        {
            await admin.OpenAsync();
            await using var create = admin.CreateCommand();
            create.CommandText = $"CREATE DATABASE \"{databaseName}\"";
            await create.ExecuteNonQueryAsync();
        }

        var testBuilder = new NpgsqlConnectionStringBuilder(configured)
        {
            Database = databaseName
        };
        ConnectionString = testBuilder.ConnectionString;

        await using var db = CreateContext();
        await db.Database.MigrateAsync();
    }

    public RestaurantDbContext CreateContext()
    {
        if (ConnectionString is null)
        {
            throw new InvalidOperationException("PostgreSQL regression fixture is not configured.");
        }

        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseNpgsql(ConnectionString, npgsql => npgsql.EnableRetryOnFailure(3))
            .Options;
        return new RestaurantDbContext(options);
    }

    public async Task DisposeAsync()
    {
        if (adminConnectionString is null || databaseName is null)
        {
            return;
        }

        await using var admin = new NpgsqlConnection(adminConnectionString);
        await admin.OpenAsync();
        await using var drop = admin.CreateCommand();
        drop.CommandText = $"DROP DATABASE IF EXISTS \"{databaseName}\" WITH (FORCE)";
        await drop.ExecuteNonQueryAsync();
    }
}
