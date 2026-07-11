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
}
