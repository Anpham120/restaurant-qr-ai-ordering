using Microsoft.EntityFrameworkCore;
using System.Text.Json;
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
        store.AddMessage(
            created.Session.Id,
            "assistant",
            "Gợi ý món",
            [
                new SuggestedCartActionResponse("m_001", "Phở", 45000, 1, "ngon", true)
            ]);
        store.UpsertFacts(created.Session.Id, [("allergen", "hải sản", 0.9, null)]);

        var deleted = store.DeleteSessionsByTableSession("ts_t01");

        Assert.Equal(1, deleted);
        Assert.Null(store.GetSession(created.Session.Id));
        Assert.Empty(db.ChatMessages);
        Assert.Empty(db.ChatRecommendations);
        Assert.Empty(db.ChatSessionFacts);
    }

    [Fact]
    public void DbStore_LedgerExcludesSuggestedItems()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        using var db = new RestaurantDbContext(options);
        SeedOpenTableSession(db, "ts_t02");
        var store = new DbChatStore(db);
        var created = store.CreateOrGetSession("T01", "ts_t02");
        store.AddMessage(
            created.Session.Id,
            "assistant",
            "Gợi ý",
            [
                new SuggestedCartActionResponse("m_001", "Phở", 45000, 1, "ngon", true),
                new SuggestedCartActionResponse("m_002", "Cơm", 50000, 1, "no", true)
            ]);
        store.UpsertRecommendations(created.Session.Id, [("m_002", "rejected", null)]);

        var excluded = store.GetExcludedMenuItemIds(created.Session.Id);

        Assert.Contains("m_001", excluded);
        Assert.Contains("m_002", excluded);
    }

    [Fact]
    public void SessionStatePersistence_AppliesSafeV2StateAndPreservesBackendOwnedTransitions()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        using var db = new RestaurantDbContext(options);
        SeedOpenTableSession(db, "ts_v2_state");
        var store = new DbChatStore(db);
        var created = store.CreateOrGetSession("T01", "ts_v2_state");
        var constraints = new Dictionary<string, JsonElement>
        {
            ["budget_vnd"] = JsonSerializer.SerializeToElement(500_000),
            ["diet"] = JsonSerializer.SerializeToElement(new[] { "vegetarian" })
        };
        var updates = new ChatSessionUpdates(
            [new ChatFactToPersist("party_size", "6", 0.98)],
            constraints,
            ["m_ref"],
            ["m_suggested"],
            ["m_rejected"],
            ["m_accepted"],
            ["m_cart"],
            "Six guests, vegetarian, budget 500k.",
            "v2",
            new ChatConversationFrame(
                "menu",
                "recommendation",
                ["m_ref"],
                "Noodles",
                ["vegetarian"],
                4,
                null,
                new Dictionary<string, JsonElement>
                {
                    ["diet"] = JsonSerializer.SerializeToElement(new
                    {
                        source = "user",
                        turn = 4
                    })
                }));
        var reply = new ChatAssistantReply(
            "Reply",
            [],
            [],
            SessionUpdates: updates);
        store.UpsertRecommendations(
            created.Session.Id,
            [
                ("m_trusted_accepted", "accepted", (string?)"trusted-user-turn"),
                ("m_trusted_cart", "added_to_cart", (string?)"trusted-cart-turn")
            ]);

        ChatSessionStatePersistence.ApplyAssistantReply(
            store,
            created.Session.Id,
            reply,
            assistantTurnId: "assistant-turn",
            userTurnId: "user-turn");

        var state = Assert.IsType<ChatSessionStateSnapshot>(store.GetSessionState(created.Session.Id));
        Assert.Equal("v2", state.MemoryVersion);
        Assert.Equal("Six guests, vegetarian, budget 500k.", state.RollingSummary);
        Assert.Equal(500_000, state.Constraints["budget_vnd"].GetInt32());
        Assert.Equal("vegetarian", state.Constraints["diet"][0].GetString());
        Assert.Equal(["m_ref"], state.ReferencedMenuItemIds);
        Assert.Equal(["m_suggested"], state.SuggestedMenuItemIds);
        Assert.Equal(["m_rejected"], state.RejectedMenuItemIds);
        Assert.Equal(["m_trusted_accepted"], state.AcceptedMenuItemIds);
        Assert.Equal(["m_trusted_cart"], state.AddedToCartMenuItemIds);
        Assert.DoesNotContain("m_accepted", state.AcceptedMenuItemIds);
        Assert.DoesNotContain("m_cart", state.AddedToCartMenuItemIds);
        var frame = Assert.IsType<ChatConversationFrame>(state.ConversationFrame);
        Assert.Equal("recommendation", frame.ActiveIntent);
        Assert.Equal(["m_ref"], frame.FocusMenuItemIds);
        Assert.Equal(4, frame.TurnSequence);
        Assert.Equal("user", frame.ConstraintProvenance["diet"].GetProperty("source").GetString());
        var fact = Assert.Single(state.Facts);
        Assert.Equal("party_size", fact.Kind);
        Assert.Equal("6", fact.Value);
        Assert.Equal("assistant-turn", fact.SourceTurnId);
    }

    [Fact]
    public void SessionStatePersistence_KeepsLegacyReplyFallbackForOneRelease()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        using var db = new RestaurantDbContext(options);
        SeedOpenTableSession(db, "ts_legacy_state");
        var store = new DbChatStore(db);
        var created = store.CreateOrGetSession("T01", "ts_legacy_state");
        var reply = new ChatAssistantReply(
            "Legacy reply",
            [],
            [],
            FactsToPersist: [new ChatFactToPersist("allergen", "peanut", 0.99)],
            RejectedMenuItemIds: ["m_legacy_rejected"],
            UpdatedRollingSummary: "Legacy summary");

        ChatSessionStatePersistence.ApplyAssistantReply(
            store,
            created.Session.Id,
            reply,
            assistantTurnId: "assistant-legacy",
            userTurnId: "user-legacy");

        var state = Assert.IsType<ChatSessionStateSnapshot>(store.GetSessionState(created.Session.Id));
        Assert.Equal("v1", state.MemoryVersion);
        Assert.Equal("Legacy summary", state.RollingSummary);
        Assert.Equal(["m_legacy_rejected"], state.RejectedMenuItemIds);
        var fact = Assert.Single(state.Facts);
        Assert.Equal("allergen", fact.Kind);
        Assert.Equal("peanut", fact.Value);
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
