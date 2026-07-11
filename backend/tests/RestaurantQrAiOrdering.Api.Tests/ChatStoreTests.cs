using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class ChatStoreTests
{
    [Fact]
    public void DbStore_ReusesTableSessionAndRestoresHistory()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        using var db = new RestaurantDbContext(options);
        SeedOpenTableSession(db, "ts_t01");
        var store = new DbChatStore(db);
        var created = store.CreateOrGetSession("T01", "ts_t01");
        store.AddMessage(created.Session.Id, "user", "Tôi dị ứng hải sản");

        var restored = store.CreateOrGetSession("T01", "ts_t01");

        Assert.False(created.Reused);
        Assert.True(restored.Reused);
        Assert.Equal(created.Session.Id, restored.Session.Id);
        Assert.Single(restored.Session.Messages);
        Assert.Equal("Tôi dị ứng hải sản", restored.Session.Messages[0].Content);
    }

    [Fact]
    public void DbStore_DeletesHistoryWhenTableSessionCloses()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        using var db = new RestaurantDbContext(options);
        SeedOpenTableSession(db, "ts_t01");
        var store = new DbChatStore(db);
        var created = store.CreateOrGetSession("T01", "ts_t01");
        store.AddMessage(created.Session.Id, "user", "Khách muốn món không hải sản");

        var deleted = store.DeleteSessionsByTableSession("ts_t01");

        Assert.Equal(1, deleted);
        Assert.Null(store.GetSession(created.Session.Id));
        Assert.Empty(db.ChatMessages);
    }

    private static void SeedOpenTableSession(RestaurantDbContext db, string sessionId)
    {
        var now = DateTimeOffset.UtcNow;
        var table = new RestaurantTable
        {
            Id = $"table_{sessionId}",
            TableCode = "T01",
            DisplayName = "Bàn T01",
            QrToken = $"qr_{sessionId}",
            IsActive = true,
            CreatedAt = now,
            UpdatedAt = now
        };
        db.RestaurantTables.Add(table);
        db.TableSessions.Add(new TableSession
        {
            Id = sessionId,
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
        });
        db.SaveChanges();
    }
}
