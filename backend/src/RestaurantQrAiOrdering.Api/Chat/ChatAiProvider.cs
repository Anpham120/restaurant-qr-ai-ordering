using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using RestaurantQrAiOrdering.Api.Data;

namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record ChatMenuItemContext(
    string Id,
    string CategoryId,
    string CategoryName,
    string Name,
    string Description,
    decimal PriceVnd,
    IReadOnlyList<string> Tags,
    bool IsAvailable);

public sealed record ChatAiRequest(
    string UserMessage,
    IReadOnlyList<ChatMessageSnapshot> History,
    string? SessionMemory,
    IReadOnlyList<ChatMenuItemContext> MenuItems,
    string? TableCode);

public sealed record AiSuggestedAction(string MenuItemId, int Quantity, string Reason);

public sealed record ChatAiResult(
    string Content,
    bool ServiceAvailable,
    bool LlmProviderAvailable,
    string Model,
    string RetrievalMethod,
    string? FastPath,
    IReadOnlyList<AiSuggestedAction> SuggestedActions,
    IReadOnlyList<string> GuardrailFlags,
    IReadOnlyList<RetrievedSourceResponse> RetrievedSources,
    IReadOnlyDictionary<string, double> LatencyMs);

public interface IChatAiProvider
{
    Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken);
}

public interface IChatAssistantService
{
    Task<ChatAssistantReply> GenerateReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? sessionMemory,
        string? tableCode,
        CancellationToken cancellationToken);
}

public sealed record ChatAssistantReply(
    string Content,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions,
    IReadOnlyList<string> GuardrailFlags,
    ChatDiagnosticsResponse Diagnostics);

public sealed class PythonAcademicChatProvider : IChatAiProvider
{
    private readonly HttpClient httpClient;
    private readonly IConfiguration configuration;
    private readonly ILogger<PythonAcademicChatProvider> logger;

    public PythonAcademicChatProvider(
        HttpClient httpClient,
        IConfiguration configuration,
        ILogger<PythonAcademicChatProvider> logger)
    {
        this.httpClient = httpClient;
        this.configuration = configuration;
        this.logger = logger;
    }

    public async Task<ChatAiResult> GenerateAsync(
        ChatAiRequest request,
        CancellationToken cancellationToken)
    {
        var serviceUrl = configuration["AI_SERVICE_URL"] ?? configuration["Ai:ServiceUrl"];
        if (string.IsNullOrWhiteSpace(serviceUrl))
        {
            return Unavailable();
        }
        var timeoutSeconds = ReadPositiveInt("AI_TIMEOUT_SECONDS", 8);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));
        var payload = new
        {
            message = request.UserMessage,
            table_code = request.TableCode,
            session_memory = request.SessionMemory,
            history = request.History.TakeLast(6).Select(item => new { role = item.Role, content = item.Content }),
            menu_items = request.MenuItems.Select(item => new
            {
                id = item.Id,
                category_id = item.CategoryId,
                category_name = item.CategoryName,
                name = item.Name,
                description = item.Description,
                price_vnd = item.PriceVnd,
                tags = item.Tags,
                is_available = item.IsAvailable
            })
        };

        try
        {
            using var requestMessage = new HttpRequestMessage(
                HttpMethod.Post,
                $"{serviceUrl.TrimEnd('/')}/v1/chat")
            {
                Content = JsonContent.Create(payload)
            };
            using var response = await httpClient.SendAsync(
                requestMessage,
                HttpCompletionOption.ResponseHeadersRead,
                timeout.Token);
            response.EnsureSuccessStatusCode();
            using var json = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(timeout.Token), cancellationToken: timeout.Token);
            return Parse(json.RootElement);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            logger.LogWarning(exception, "Academic AI service request failed.");
            return Unavailable();
        }
    }

    private ChatAiResult Parse(JsonElement root)
    {
        var content = GetString(root, "content")?.Trim();
        if (string.IsNullOrWhiteSpace(content))
        {
            return Unavailable();
        }
        return new ChatAiResult(
            content,
            ServiceAvailable: true,
            LlmProviderAvailable: root.TryGetProperty("provider_available", out var provider) && provider.ValueKind == JsonValueKind.True,
            Model: GetString(root, "model") ?? configuration["AI_MODEL"] ?? "unknown",
            RetrievalMethod: GetString(root, "retrieval_method") ?? "unknown",
            FastPath: GetString(root, "fast_path"),
            SuggestedActions: ParseActions(root),
            GuardrailFlags: ParseStrings(root, "guardrail_flags"),
            RetrievedSources: ParseSources(root),
            LatencyMs: ParseLatency(root));
    }

    private static List<AiSuggestedAction> ParseActions(JsonElement root)
    {
        var output = new List<AiSuggestedAction>();
        if (!root.TryGetProperty("suggested_cart_actions", out var array) || array.ValueKind != JsonValueKind.Array)
        {
            return output;
        }
        foreach (var item in array.EnumerateArray())
        {
            var id = GetString(item, "menu_item_id")?.Trim();
            if (string.IsNullOrEmpty(id)) continue;
            var quantity = item.TryGetProperty("quantity", out var quantityValue) && quantityValue.TryGetInt32(out var parsed)
                ? Math.Clamp(parsed, 1, 20)
                : 1;
            output.Add(new AiSuggestedAction(id, quantity, GetString(item, "reason") ?? "Gợi ý theo menu hiện tại."));
        }
        return output;
    }

    private static List<RetrievedSourceResponse> ParseSources(JsonElement root)
    {
        var output = new List<RetrievedSourceResponse>();
        if (!root.TryGetProperty("retrieved_sources", out var array) || array.ValueKind != JsonValueKind.Array)
        {
            return output;
        }
        foreach (var item in array.EnumerateArray())
        {
            output.Add(new RetrievedSourceResponse(
                GetString(item, "source") ?? "unknown",
                GetString(item, "title") ?? "unknown",
                item.TryGetProperty("score", out var score) && score.TryGetDouble(out var value) ? value : 0));
        }
        return output;
    }

    private static Dictionary<string, double> ParseLatency(JsonElement root)
    {
        var output = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
        if (!root.TryGetProperty("latency_ms", out var latency) || latency.ValueKind != JsonValueKind.Object)
        {
            return output;
        }
        foreach (var property in latency.EnumerateObject())
        {
            if (property.Value.TryGetDouble(out var value)) output[property.Name] = value;
        }
        return output;
    }

    private static List<string> ParseStrings(JsonElement root, string propertyName)
    {
        if (!root.TryGetProperty(propertyName, out var array) || array.ValueKind != JsonValueKind.Array)
        {
            return [];
        }
        return array.EnumerateArray()
            .Where(item => item.ValueKind == JsonValueKind.String)
            .Select(item => item.GetString()?.Trim())
            .Where(value => !string.IsNullOrWhiteSpace(value))
            .Select(value => value!)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private int ReadPositiveInt(string key, int defaultValue)
    {
        var raw = configuration[key] ?? configuration[$"Ai:{key[3..]}"];
        return int.TryParse(raw, out var value) && value > 0 ? value : defaultValue;
    }

    private static string? GetString(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private static ChatAiResult Unavailable() => new(
        "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem menu và gọi món trực tiếp.",
        ServiceAvailable: false,
        LlmProviderAvailable: false,
        Model: "unavailable",
        RetrievalMethod: "unavailable",
        FastPath: "service_fallback",
        SuggestedActions: [],
        GuardrailFlags: ["AI_SERVICE_UNAVAILABLE"],
        RetrievedSources: [],
        LatencyMs: new Dictionary<string, double>());
}

public sealed class ChatAssistantService : IChatAssistantService
{
    private const string MenuCacheKey = "chat:menu-context:v1";
    private static readonly TimeSpan MenuCacheDuration = TimeSpan.FromSeconds(2);
    private static readonly string[] ForbiddenCompletionClaims =
    [
        "đã đặt món",
        "đã thêm vào giỏ",
        "đã gửi đơn",
        "đã thanh toán",
        "đơn của bạn đã được tạo"
    ];

    private readonly RestaurantDbContext db;
    private readonly IChatAiProvider provider;
    private readonly IMemoryCache cache;

    public ChatAssistantService(
        RestaurantDbContext db,
        IChatAiProvider provider,
        IMemoryCache cache)
    {
        this.db = db;
        this.provider = provider;
        this.cache = cache;
    }

    public async Task<ChatAssistantReply> GenerateReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? sessionMemory,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        var menu = await cache.GetOrCreateAsync<IReadOnlyList<ChatMenuItemContext>>(
            MenuCacheKey,
            async entry =>
            {
                entry.AbsoluteExpirationRelativeToNow = MenuCacheDuration;
                var categories = await db.Categories.AsNoTracking().ToDictionaryAsync(
                    category => category.Id,
                    category => category.Name,
                    cancellationToken);
                var entities = await db.MenuItems
                    .AsNoTracking()
                    .OrderBy(item => item.Id)
                    .ToListAsync(cancellationToken);
                return entities.Select(item => new ChatMenuItemContext(
                    item.Id,
                    item.CategoryId,
                    categories.GetValueOrDefault(item.CategoryId, item.CategoryId),
                    item.Name,
                    item.Description ?? string.Empty,
                    item.Price,
                    item.Tags.ToList(),
                    item.IsAvailable)).ToList();
            }) ?? [];

        var result = await provider.GenerateAsync(
            new ChatAiRequest(userMessage, history, sessionMemory, menu, tableCode),
            cancellationToken);
        var flags = result.GuardrailFlags.ToList();
        if (!result.ServiceAvailable && !flags.Contains("AI_SERVICE_UNAVAILABLE"))
        {
            flags.Add("AI_SERVICE_UNAVAILABLE");
        }

        var available = menu.Where(item => item.IsAvailable).ToDictionary(item => item.Id);
        var actions = result.SuggestedActions
            .Where(action => available.ContainsKey(action.MenuItemId))
            .GroupBy(action => action.MenuItemId)
            .Select(group => group.First())
            .Take(3)
            .Select(action =>
            {
                var item = available[action.MenuItemId];
                return new SuggestedCartActionResponse(
                    item.Id,
                    item.Name,
                    item.PriceVnd,
                    Math.Clamp(action.Quantity, 1, 20),
                    action.Reason,
                    RequiresCustomerConfirmation: true);
            })
            .ToList();
        if (actions.Count > 0 && !flags.Contains("CUSTOMER_CONFIRMATION_REQUIRED"))
        {
            flags.Add("CUSTOMER_CONFIRMATION_REQUIRED");
        }

        var content = result.Content;
        if (ForbiddenCompletionClaims.Any(claim => content.Contains(claim, StringComparison.OrdinalIgnoreCase)))
        {
            content = "Mình chỉ có thể tư vấn và tạo gợi ý. Bạn phải tự xác nhận trên giao diện trước khi giỏ hàng hoặc đơn hàng thay đổi.";
            flags.Add("AI_OUTPUT_POLICY_VIOLATION");
            actions.Clear();
        }

        return new ChatAssistantReply(
            content,
            actions,
            flags.Distinct(StringComparer.OrdinalIgnoreCase).ToList(),
            new ChatDiagnosticsResponse(
                result.ServiceAvailable,
                result.LlmProviderAvailable,
                result.Model,
                result.RetrievalMethod,
                result.FastPath,
                result.LatencyMs,
                result.RetrievedSources));
    }
}
