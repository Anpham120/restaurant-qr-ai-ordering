using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Chat;

namespace RestaurantQrAiOrdering.Api.Tests.Chat;

public sealed class ChatEndpointTests
{
    [Fact]
    public async Task ChatFlow_CreatesSessionStoresMessagesAndReturnsSuggestedAction()
    {
        await using var factory = CreateFactoryWithProvider(new AvailableChatAiProvider());
        using var client = factory.CreateClient();

        using var createResponse = await client.PostAsync("/api/chat/sessions", content: null);
        using var createBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var chatSessionId = createBody.RootElement.GetProperty("chatSessionId").GetString();

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.False(string.IsNullOrWhiteSpace(chatSessionId));

        using var sendResponse = await client.PostAsJsonAsync($"/api/chat/sessions/{chatSessionId}/messages", new
        {
            content = "Goi y mon cho 2 nguoi",
            tableCode = "T05"
        });
        using var sendBody = await JsonDocument.ParseAsync(await sendResponse.Content.ReadAsStreamAsync());

        var root = sendBody.RootElement;
        var actions = root.GetProperty("suggestedCartActions").EnumerateArray().ToList();
        var flags = root.GetProperty("guardrailFlags").EnumerateArray().Select(flag => flag.GetString()).ToList();

        Assert.Equal(HttpStatusCode.OK, sendResponse.StatusCode);
        Assert.Equal("assistant", root.GetProperty("message").GetProperty("role").GetString());
        Assert.Single(actions);
        Assert.Equal("m_001", actions[0].GetProperty("menuItemId").GetString());
        Assert.Equal(65000, actions[0].GetProperty("price").GetDecimal());
        Assert.True(actions[0].GetProperty("requiresCustomerConfirmation").GetBoolean());
        Assert.Contains("CUSTOMER_CONFIRMATION_REQUIRED", flags);

        using var historyResponse = await client.GetAsync($"/api/chat/sessions/{chatSessionId}/messages");
        using var historyBody = await JsonDocument.ParseAsync(await historyResponse.Content.ReadAsStreamAsync());
        var messages = historyBody.RootElement.GetProperty("messages").EnumerateArray().ToList();

        Assert.Equal(HttpStatusCode.OK, historyResponse.StatusCode);
        Assert.Equal(2, messages.Count);
        Assert.Equal("user", messages[0].GetProperty("role").GetString());
        Assert.Equal("assistant", messages[1].GetProperty("role").GetString());
    }

    [Fact]
    public async Task SendMessage_WhenProviderMissing_ReturnsSafeFallbackAndStoresHistory()
    {
        await using var factory = CreateFactoryWithMockUnavailable();
        using var client = factory.CreateClient();

        var chatSessionId = await CreateSessionAsync(client);

        using var response = await client.PostAsJsonAsync($"/api/chat/sessions/{chatSessionId}/messages", new
        {
            content = "Xin chao"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        var flags = body.RootElement.GetProperty("guardrailFlags").EnumerateArray().Select(flag => flag.GetString()).ToList();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Empty(body.RootElement.GetProperty("suggestedCartActions").EnumerateArray());
        Assert.Contains("AI_PROVIDER_UNAVAILABLE", flags);

        using var historyResponse = await client.GetAsync($"/api/chat/sessions/{chatSessionId}/messages");
        using var historyBody = await JsonDocument.ParseAsync(await historyResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, historyResponse.StatusCode);
        Assert.Equal(2, historyBody.RootElement.GetProperty("messages").EnumerateArray().Count());
    }

    [Fact]
    public async Task SendMessage_ValidatesEmptyContentAndMissingSession()
    {
        await using var factory = CreateFactoryWithProvider(new AvailableChatAiProvider());
        using var client = factory.CreateClient();
        var chatSessionId = await CreateSessionAsync(client);

        using var emptyResponse = await client.PostAsJsonAsync($"/api/chat/sessions/{chatSessionId}/messages", new
        {
            content = "   "
        });
        using var emptyBody = await JsonDocument.ParseAsync(await emptyResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, emptyResponse.StatusCode);
        Assert.Equal(
            "CHAT_MESSAGE_EMPTY",
            emptyBody.RootElement.GetProperty("error").GetProperty("code").GetString());

        using var missingResponse = await client.PostAsJsonAsync("/api/chat/sessions/chat_missing/messages", new
        {
            content = "Goi y mon"
        });
        using var missingBody = await JsonDocument.ParseAsync(await missingResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
        Assert.Equal(
            "CHAT_SESSION_NOT_FOUND",
            missingBody.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task SendMessage_RejectsMissingBodyWithStandardError()
    {
        await using var factory = CreateFactoryWithProvider(new AvailableChatAiProvider());
        using var client = factory.CreateClient();
        var chatSessionId = await CreateSessionAsync(client);

        using var response = await client.PostAsync($"/api/chat/sessions/{chatSessionId}/messages", content: null);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("REQUEST_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    private static TestWebApplicationFactory CreateFactoryWithProvider(IChatAiProvider provider)
    {
        return new ChatTestWebApplicationFactory(provider);
    }

    private static TestWebApplicationFactory CreateFactoryWithMockUnavailable()
    {
        return new ChatTestWebApplicationFactory(new MockUnavailableChatAiProvider());
    }

    private static async Task<string> CreateSessionAsync(HttpClient client)
    {
        using var response = await client.PostAsync("/api/chat/sessions", content: null);
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return body.RootElement.GetProperty("chatSessionId").GetString()!;
    }

    private sealed class AvailableChatAiProvider : IChatAiProvider
    {
        public Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken)
        {
            return Task.FromResult(new ChatAiResult(
                "Ban co the chon Goi cuon tom thit. Minh chi de xuat va can ban xac nhan truoc khi them vao gio.",
                ProviderAvailable: true));
        }
    }

    private sealed class MockUnavailableChatAiProvider : IChatAiProvider
    {
        public Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken)
        {
            return Task.FromResult(new ChatAiResult(
                "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống.",
                ProviderAvailable: false));
        }
    }
}

internal sealed class ChatTestWebApplicationFactory(IChatAiProvider provider) : TestWebApplicationFactory
{
    protected override void ConfigureWebHost(Microsoft.AspNetCore.Hosting.IWebHostBuilder builder)
    {
        base.ConfigureWebHost(builder);
        builder.ConfigureServices(services =>
        {
            var descriptors = services.Where(d => d.ServiceType == typeof(IChatAiProvider)).ToList();
            foreach (var d in descriptors)
            {
                services.Remove(d);
            }
            services.AddSingleton(provider);
        });
    }
}
