using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class ChatStoreTests
{
    [Fact]
    public void InMemoryStore_ReusesTableSessionAndRestoresHistory()
    {
        var store = new ChatStore();
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
        var store = new DbChatStore(db);
        var created = store.CreateOrGetSession("T01", "ts_t01");
        store.AddMessage(created.Session.Id, "user", "Khách muốn món không hải sản");

        var deleted = store.DeleteSessionsByTableSession("ts_t01");

        Assert.Equal(1, deleted);
        Assert.Null(store.GetSession(created.Session.Id));
        Assert.Empty(db.ChatMessages);
    }
}
