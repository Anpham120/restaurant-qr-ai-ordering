using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class ChatMenuCatalogTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public ChatMenuCatalogTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    private static Task<ChatAssistantReply> ReplyAsync(
        IChatAssistantService assistant,
        string message,
        IReadOnlyList<ChatMessageSnapshot>? history = null,
        IReadOnlySet<string>? excluded = null) =>
        assistant.GenerateReplyAsync(
            message,
            history ?? [],
            tableCode: null,
            chatSessionId: "chat_test",
            tableSessionId: null,
            rollingSummary: null,
            excludedMenuItemIds: excluded ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase),
            facts: [],
            CancellationToken.None);

    [Fact]
    public async Task PureCatalog_Seafood_DoesNotRequireProvider()
    {
        using var scope = factory.Services.CreateScope();
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        var reply = await ReplyAsync(assistant, "cho xem nhóm hải sản");

        Assert.Contains("nhóm Hải sản", reply.Content);
        Assert.Contains("Cua rang me", reply.Content);
        Assert.DoesNotContain("Gỏi cuốn tôm thịt", reply.Content);
        Assert.DoesNotContain("AI_PROVIDER_UNAVAILABLE", reply.GuardrailFlags);
    }

    [Fact]
    public async Task PureCatalog_RespectsLedgerExclusions()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var seafoodCategory = await db.Categories.SingleAsync(category => category.Name == "Hải sản");
        var seafoodItems = await db.MenuItems
            .Where(item => item.CategoryId == seafoodCategory.Id && item.IsAvailable)
            .OrderBy(item => item.Name)
            .Take(2)
            .ToListAsync();
        Assert.True(seafoodItems.Count >= 2);

        var excluded = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { seafoodItems[0].Id };
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        var reply = await ReplyAsync(assistant, "cho xem nhóm hải sản", excluded: excluded);

        Assert.DoesNotContain(seafoodItems[0].Name, reply.Content);
        Assert.DoesNotContain(
            seafoodItems[0].Id,
            reply.SuggestedCartActions.Select(a => a.MenuItemId));
    }

    [Fact]
    public async Task SoftCriteria_DoesNotUseCatalogFastPathAlone()
    {
        using var scope = factory.Services.CreateScope();
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        // Soft criteria forces LLM path; without Python provider this surfaces unavailable flag.
        var reply = await ReplyAsync(assistant, "gợi ý món hải sản thanh đạm cho người lớn tuổi");

        // Must not falsely claim a deterministic catalog listing without LLM.
        Assert.False(reply.Content.StartsWith("Đây là các món thuộc nhóm", StringComparison.Ordinal));
    }

    [Fact]
    public async Task UnavailableItem_NoLongerHardBlocksEntireReply()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var item = await db.MenuItems.FirstAsync(menuItem => menuItem.IsAvailable);
        item.IsAvailable = false;
        await db.SaveChangesAsync();

        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();
        var reply = await ReplyAsync(assistant, item.Name);

        // Soft context: do not hard-fail the whole turn with MENU_ITEM_UNAVAILABLE.
        Assert.DoesNotContain("MENU_ITEM_UNAVAILABLE", reply.GuardrailFlags);
    }

    [Fact]
    public async Task AlcoholCatalogBrowse_UsesBeerAndWineCategory()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var category = await db.Categories.SingleAsync(item => item.Name == "Bia & Rượu");
        var allowedIds = await db.MenuItems
            .Where(item => item.CategoryId == category.Id && item.IsAvailable)
            .Select(item => item.Id)
            .ToListAsync();
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        var reply = await ReplyAsync(assistant, "cho xem nhóm bia & rượu");

        Assert.NotEmpty(reply.SuggestedCartActions);
        Assert.All(reply.SuggestedCartActions, action => Assert.Contains(action.MenuItemId, allowedIds));
    }
}
