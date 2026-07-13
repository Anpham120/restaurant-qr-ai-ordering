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

    [Fact]
    public async Task TestV6_ChatUsesLiveMenuAvailabilityAfterStartup()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var item = await db.MenuItems.FirstAsync(menuItem => menuItem.IsAvailable);
        item.IsAvailable = false;
        await db.SaveChangesAsync();

        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();
        var reply = await assistant.GenerateReplyAsync(item.Name, [], null, CancellationToken.None);

        Assert.Contains("MENU_ITEM_UNAVAILABLE", reply.GuardrailFlags);
    }

    [Fact]
    public async Task TestV35_ExplicitSeafoodCatalog_DoesNotCallProviderOrLeakOtherCategory()
    {
        using var scope = factory.Services.CreateScope();
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        var reply = await assistant.GenerateReplyAsync(
            "toàn bộ thực đơn về hải sản",
            [],
            null,
            CancellationToken.None);

        Assert.Contains("nhóm Hải sản", reply.Content);
        Assert.Contains("Cua rang me", reply.Content);
        Assert.DoesNotContain("Gỏi cuốn tôm thịt", reply.Content);
        Assert.DoesNotContain("AI_PROVIDER_UNAVAILABLE", reply.GuardrailFlags);
    }

    [Fact]
    public async Task TestV36_AdditionalRecommendation_ExcludesItemsAlreadySuggestedInSession()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var seafoodCategory = await db.Categories.SingleAsync(category => category.Name == "Hải sản");
        var seafoodItems = await db.MenuItems
            .Where(item => item.CategoryId == seafoodCategory.Id && item.IsAvailable)
            .OrderBy(item => item.Name)
            .Take(3)
            .ToListAsync();
        Assert.True(seafoodItems.Count >= 3);

        var alreadySuggested = seafoodItems[0];
        var expectedFirstNewItem = seafoodItems[1];
        var expectedSecondNewItem = seafoodItems[2];
        var history = new ChatMessageSnapshot(
            "assistant-1",
            "chat-1",
            "assistant",
            $"Mình đã gợi ý {alreadySuggested.Name}.",
            DateTimeOffset.UtcNow,
            []);
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        var reply = await assistant.GenerateReplyAsync(
            "gợi ý thêm 2 món hải sản",
            [history],
            null,
            CancellationToken.None);

        Assert.Contains("2 món khác", reply.Content);
        Assert.DoesNotContain(alreadySuggested.Name, reply.Content);
        Assert.Contains(expectedFirstNewItem.Name, reply.Content);
        Assert.Contains(expectedSecondNewItem.Name, reply.Content);
        Assert.Empty(reply.SuggestedCartActions);
    }

    [Fact]
    public async Task TestV36_RequestedRecommendationCount_IsHonoredUpToEight()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        Assert.True(await db.MenuItems.CountAsync(item => item.IsAvailable) >= 5);
        var assistant = scope.ServiceProvider.GetRequiredService<IChatAssistantService>();

        var reply = await assistant.GenerateReplyAsync(
            "gợi ý cho tôi 5 món",
            [],
            null,
            CancellationToken.None);

        Assert.Contains("Mình gợi ý 5 món phù hợp", reply.Content);
        Assert.Empty(reply.SuggestedCartActions);
    }
}
