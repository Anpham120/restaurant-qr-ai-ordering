using System.Diagnostics;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record ChatAiRequest(
    string UserMessage,
    IReadOnlyList<ChatMessageSnapshot> History,
    IReadOnlyList<ChatMenuItemContext> AvailableMenuItems,
    string? TableCode = null,
    string SessionMemory = "",
    string? ChatSessionId = null,
    string? TableSessionId = null,
    string? RollingSummary = null,
    IReadOnlySet<string>? ExcludedMenuItemIds = null,
    IReadOnlyList<ChatSessionFactSnapshot>? Facts = null,
    IReadOnlyList<object>? CartItems = null,
    IReadOnlyList<object>? Orders = null,
    IReadOnlyList<object>? Promotions = null,
    string? LocalTime = null,
    string? MealPeriod = null);

public sealed record ChatAiResult(
    string Content,
    bool ProviderAvailable,
    IReadOnlyList<SuggestedCartActionResponse>? SuggestedCartActions = null,
    IReadOnlyList<string>? GuardrailFlags = null,
    bool SuggestStaffHandoff = false,
    FollowUpHint? FollowUp = null,
    IReadOnlyList<ChatFactToPersist>? Facts = null,
    IReadOnlyList<string>? RejectedMenuItemIds = null,
    string? UpdatedRollingSummary = null);

public sealed record ChatFactToPersist(string Kind, string Value, double Confidence);

public interface IChatAiProvider
{
    Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken);

    IAsyncEnumerable<ChatStreamEvent> GenerateStreamAsync(
        ChatAiRequest request,
        CancellationToken cancellationToken);
}

public sealed record ChatStreamEvent(string EventType, JsonElement? Data);

public interface IChatAssistantService
{
    Task<ChatAssistantReply> GenerateReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        string chatSessionId,
        string? tableSessionId,
        string? rollingSummary,
        IReadOnlySet<string> excludedMenuItemIds,
        IReadOnlyList<ChatSessionFactSnapshot> facts,
        CancellationToken cancellationToken);

    Task StreamReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        string chatSessionId,
        string? tableSessionId,
        string? rollingSummary,
        IReadOnlySet<string> excludedMenuItemIds,
        IReadOnlyList<ChatSessionFactSnapshot> facts,
        Func<ChatAssistantReply, CancellationToken, Task> onCompleteAsync,
        Func<string, CancellationToken, Task> onTokenAsync,
        CancellationToken cancellationToken);
}

public sealed record ChatAssistantReply(
    string Content,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions,
    IReadOnlyList<string> GuardrailFlags,
    bool SuggestStaffHandoff = false,
    FollowUpHint? FollowUp = null,
    IReadOnlyList<ChatFactToPersist>? FactsToPersist = null,
    IReadOnlyList<string>? RejectedMenuItemIds = null,
    string? UpdatedRollingSummary = null);

public sealed class GeminiChatProvider : IChatAiProvider
{
    private readonly HttpClient httpClient;
    private readonly IConfiguration configuration;
    private readonly ILogger<GeminiChatProvider> logger;

    public GeminiChatProvider(
        HttpClient httpClient,
        IConfiguration configuration,
        ILogger<GeminiChatProvider> logger)
    {
        this.httpClient = httpClient;
        this.configuration = configuration;
        this.logger = logger;
    }

    public async Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken)
    {
        return await GenerateWithPythonRagAsync(request, cancellationToken);
    }

    public async IAsyncEnumerable<ChatStreamEvent> GenerateStreamAsync(
        ChatAiRequest request,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var serviceUrl = configuration["AI_SERVICE_URL"] ?? configuration["Ai:ServiceUrl"];
        if (string.IsNullOrWhiteSpace(serviceUrl))
        {
            yield return new ChatStreamEvent("final", JsonDocument.Parse("""
                {"content":"Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống.","provider_available":false,"suggest_staff_handoff":true}
                """).RootElement);
            yield return new ChatStreamEvent("done", JsonDocument.Parse("{\"ok\":true}").RootElement);
            yield break;
        }

        var timeoutSeconds = ReadPositiveInt("BACKEND_AI_TIMEOUT_SECONDS", fallbackKey: "AI_TIMEOUT_SECONDS", defaultValue: 12);
        var endpoint = $"{serviceUrl.TrimEnd('/')}/v1/chat/stream";
        var payload = BuildPayload(request);

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));

        using var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = JsonContent.Create(payload)
        };

        using var response = await httpClient.SendAsync(
            httpRequest,
            HttpCompletionOption.ResponseHeadersRead,
            timeoutCts.Token);

        if (!response.IsSuccessStatusCode)
        {
            logger.LogWarning("Python AI stream returned HTTP {StatusCode}.", (int)response.StatusCode);
            yield return new ChatStreamEvent("final", JsonDocument.Parse("""
                {"content":"Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé.","provider_available":false,"suggest_staff_handoff":true,"guardrail_flags":["AI_PROVIDER_UNAVAILABLE"]}
                """).RootElement);
            yield return new ChatStreamEvent("done", JsonDocument.Parse("{\"ok\":true}").RootElement);
            yield break;
        }

        await using var stream = await response.Content.ReadAsStreamAsync(timeoutCts.Token);
        using var reader = new StreamReader(stream, Encoding.UTF8);

        string? eventName = null;
        while (!reader.EndOfStream && !timeoutCts.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(timeoutCts.Token);
            if (line is null)
            {
                break;
            }

            if (line.StartsWith("event: ", StringComparison.Ordinal))
            {
                eventName = line["event: ".Length..].Trim();
                continue;
            }

            if (!line.StartsWith("data: ", StringComparison.Ordinal) || string.IsNullOrWhiteSpace(eventName))
            {
                continue;
            }

            var dataJson = line["data: ".Length..];
            using var document = JsonDocument.Parse(dataJson);
            var cloned = document.RootElement.Clone();
            yield return new ChatStreamEvent(eventName, cloned);
            eventName = null;

            if (cloned.ValueKind == JsonValueKind.Object
                && cloned.TryGetProperty("ok", out var okElement)
                && okElement.ValueKind == JsonValueKind.True)
            {
                break;
            }
        }
    }

    private async Task<ChatAiResult> GenerateWithPythonRagAsync(ChatAiRequest request, CancellationToken cancellationToken)
    {
        var serviceUrl = configuration["AI_SERVICE_URL"] ?? configuration["Ai:ServiceUrl"];
        if (string.IsNullOrWhiteSpace(serviceUrl))
        {
            return Unavailable();
        }

        var timeoutSeconds = ReadPositiveInt("BACKEND_AI_TIMEOUT_SECONDS", fallbackKey: "AI_TIMEOUT_SECONDS", defaultValue: 12);
        var endpoint = $"{serviceUrl.TrimEnd('/')}/v1/chat";
        var stopwatch = Stopwatch.StartNew();

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));

        var payload = BuildPayload(request);

        try
        {
            using var response = await httpClient.PostAsJsonAsync(endpoint, payload, timeoutCts.Token);
            if (!response.IsSuccessStatusCode)
            {
                logger.LogWarning("Python AI service returned HTTP {StatusCode}.", (int)response.StatusCode);
                return SlowFallback();
            }

            using var json = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(timeoutCts.Token),
                cancellationToken: timeoutCts.Token);

            var content = ExtractPythonRagContent(json.RootElement);
            if (string.IsNullOrWhiteSpace(content))
            {
                return SlowFallback();
            }

            var excluded = request.ExcludedMenuItemIds ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var actions = ExtractPythonSuggestedActions(json.RootElement, request.AvailableMenuItems, excluded);
            var flags = ExtractPythonGuardrailFlags(json.RootElement);
            var handoff = json.RootElement.TryGetProperty("suggest_staff_handoff", out var h)
                          && h.ValueKind == JsonValueKind.True;
            var followUp = ExtractFollowUp(json.RootElement);
            var facts = ExtractFacts(json.RootElement);
            var rejected = ExtractStringArray(json.RootElement, "rejected_menu_item_ids");
            var summary = json.RootElement.TryGetProperty("updated_rolling_summary", out var s)
                          && s.ValueKind == JsonValueKind.String
                ? s.GetString()
                : null;

            logger.LogInformation("Python AI chat completed in {ElapsedMs}ms", stopwatch.ElapsedMilliseconds);

            return new ChatAiResult(
                content.Trim(),
                ProviderAvailable: ExtractProviderAvailable(json.RootElement),
                actions,
                flags,
                handoff,
                followUp,
                facts,
                rejected,
                summary);
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            logger.LogWarning(exception, "Python AI service request failed after {ElapsedMs}ms.", stopwatch.ElapsedMilliseconds);
            return SlowFallback();
        }
    }

    private static object BuildPayload(ChatAiRequest request)
    {
        var excluded = request.ExcludedMenuItemIds ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        return new
        {
            message = request.UserMessage,
            table_code = request.TableCode,
            session_id = request.ChatSessionId,
            table_session_id = request.TableSessionId,
            rolling_summary = request.RollingSummary ?? request.SessionMemory,
            excluded_menu_item_ids = excluded.ToList(),
            facts = (request.Facts ?? []).Select(f => new { kind = f.Kind, value = f.Value, confidence = f.Confidence }),
            cart_items = request.CartItems ?? [],
            orders = request.Orders ?? [],
            promotions = request.Promotions ?? [],
            local_time = request.LocalTime,
            meal_period = request.MealPeriod,
            history = request.History
                .TakeLast(10)
                .Select(message => new
                {
                    role = message.Role,
                    content = message.Content,
                    suggested_cart_actions = message.SuggestedCartActions.Select(action => new
                    {
                        menu_item_id = action.MenuItemId,
                        name = action.Name
                    })
                }),
            session_memory = request.SessionMemory,
            menu_items = request.AvailableMenuItems.Select(item => new
            {
                id = item.Id,
                category_id = item.CategoryId,
                category_name = item.CategoryName,
                name = item.Name,
                description = item.Description,
                price_vnd = item.Price,
                tags = item.Tags,
                is_available = item.IsAvailable
            })
        };
    }

    private int ReadPositiveInt(string key, string fallbackKey, int defaultValue)
    {
        var rawValue = configuration[key]
            ?? configuration[fallbackKey]
            ?? configuration[$"Ai:{key[3..]}"];
        return int.TryParse(rawValue, out var value) && value > 0 ? value : defaultValue;
    }

    private static string? ExtractPythonRagContent(JsonElement root)
    {
        return root.TryGetProperty("content", out var content) && content.ValueKind == JsonValueKind.String
            ? content.GetString()
            : null;
    }

    private static bool ExtractProviderAvailable(JsonElement root)
    {
        return root.TryGetProperty("provider_available", out var providerAvailable)
            && providerAvailable.ValueKind == JsonValueKind.True;
    }

    private static List<SuggestedCartActionResponse> ExtractPythonSuggestedActions(
        JsonElement root,
        IReadOnlyList<ChatMenuItemContext> availableMenuItems,
        IReadOnlySet<string> excluded)
    {
        var results = new List<SuggestedCartActionResponse>();
        if (!root.TryGetProperty("suggested_cart_actions", out var actionsElement)
            || actionsElement.ValueKind != JsonValueKind.Array)
        {
            return results;
        }

        var availableIds = new HashSet<string>(availableMenuItems.Select(m => m.Id), StringComparer.OrdinalIgnoreCase);
        var menuLookup = availableMenuItems.ToDictionary(m => m.Id, StringComparer.OrdinalIgnoreCase);

        foreach (var action in actionsElement.EnumerateArray())
        {
            var menuItemId = action.TryGetProperty("menu_item_id", out var mid) ? mid.GetString() ?? "" : "";
            if (!availableIds.Contains(menuItemId) || excluded.Contains(menuItemId)) continue;
            if (!menuLookup.TryGetValue(menuItemId, out var menuItem) || !menuItem.IsAvailable) continue;

            var name = action.TryGetProperty("name", out var n) && n.ValueKind == JsonValueKind.String
                ? n.GetString() ?? menuItem.Name : menuItem.Name;
            var quantity = action.TryGetProperty("quantity", out var q) && q.TryGetInt32(out var qv)
                ? Math.Clamp(qv, 1, 20) : 1;
            var reason = action.TryGetProperty("reason", out var r) && r.ValueKind == JsonValueKind.String
                ? r.GetString() ?? "" : "";
            var evidenceIds = ExtractStringArray(action, "evidence_ids");

            results.Add(new SuggestedCartActionResponse(
                menuItemId, name, menuItem.Price, quantity, reason,
                RequiresCustomerConfirmation: true,
                Status: "pending",
                EvidenceIds: evidenceIds));
        }

        return results;
    }

    private static List<string> ExtractPythonGuardrailFlags(JsonElement root) =>
        ExtractStringArray(root, "guardrail_flags");

    private static FollowUpHint? ExtractFollowUp(JsonElement root)
    {
        if (!root.TryGetProperty("follow_up", out var followUp) || followUp.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        var canShowMore = followUp.TryGetProperty("can_show_more", out var c) && c.ValueKind == JsonValueKind.True;
        var remaining = followUp.TryGetProperty("remaining_count", out var r) && r.TryGetInt32(out var rv) ? rv : 0;
        return new FollowUpHint(canShowMore, remaining);
    }

    private static List<ChatFactToPersist> ExtractFacts(JsonElement root)
    {
        var results = new List<ChatFactToPersist>();
        if (!root.TryGetProperty("facts", out var facts) || facts.ValueKind != JsonValueKind.Array)
        {
            return results;
        }

        foreach (var fact in facts.EnumerateArray())
        {
            var kind = fact.TryGetProperty("kind", out var k) ? k.GetString() : null;
            var value = fact.TryGetProperty("value", out var v) ? v.GetString() : null;
            var confidence = fact.TryGetProperty("confidence", out var c) && c.TryGetDouble(out var cv) ? cv : 0.8;
            if (!string.IsNullOrWhiteSpace(kind) && !string.IsNullOrWhiteSpace(value))
            {
                results.Add(new ChatFactToPersist(kind, value, confidence));
            }
        }

        return results;
    }

    private static List<string> ExtractStringArray(JsonElement root, string property)
    {
        var results = new List<string>();
        if (!root.TryGetProperty(property, out var arr) || arr.ValueKind != JsonValueKind.Array)
        {
            return results;
        }

        foreach (var item in arr.EnumerateArray())
        {
            if (item.ValueKind == JsonValueKind.String)
            {
                var value = item.GetString()?.Trim();
                if (!string.IsNullOrEmpty(value)) results.Add(value);
            }
        }

        return results;
    }

    private static ChatAiResult Unavailable()
    {
        return new ChatAiResult(
            "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống.",
            ProviderAvailable: false,
            SuggestStaffHandoff: true);
    }

    private static ChatAiResult SlowFallback()
    {
        return new ChatAiResult(
            "Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé.",
            ProviderAvailable: false,
            GuardrailFlags: ["AI_PROVIDER_UNAVAILABLE"],
            SuggestStaffHandoff: true);
    }
}

/// <summary>
/// LLM-first orchestrator: loads live menu + cart/orders context, applies hard ledger exclusion,
/// delegates understanding to Python RAG. No keyword rule-tree for recommendations.
/// </summary>
public sealed class ChatAssistantService : IChatAssistantService
{
    private readonly RestaurantDbContext db;
    private readonly IChatAiProvider aiProvider;
    private readonly IMemoryCache cache;
    private readonly ILogger<ChatAssistantService> logger;

    public ChatAssistantService(
        RestaurantDbContext db,
        IChatAiProvider aiProvider,
        IMemoryCache cache,
        ILogger<ChatAssistantService> logger)
    {
        this.db = db;
        this.aiProvider = aiProvider;
        this.cache = cache;
        this.logger = logger;
    }

    public async Task<ChatAssistantReply> GenerateReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        string chatSessionId,
        string? tableSessionId,
        string? rollingSummary,
        IReadOnlySet<string> excludedMenuItemIds,
        IReadOnlyList<ChatSessionFactSnapshot> facts,
        CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        var prepared = await PrepareContextAsync(
            userMessage,
            history,
            tableCode,
            chatSessionId,
            tableSessionId,
            rollingSummary,
            excludedMenuItemIds,
            facts,
            cancellationToken);

        if (prepared.CatalogReply is not null)
        {
            LogStop(stopwatch, "catalog-fastpath");
            return prepared.CatalogReply;
        }

        var providerResult = await aiProvider.GenerateAsync(prepared.Request, cancellationToken);
        var reply = BuildAssistantReply(providerResult, prepared.AvailableMenuItems, excludedMenuItemIds);
        LogStop(stopwatch, "python-chat");
        return reply;
    }

    public async Task StreamReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        string chatSessionId,
        string? tableSessionId,
        string? rollingSummary,
        IReadOnlySet<string> excludedMenuItemIds,
        IReadOnlyList<ChatSessionFactSnapshot> facts,
        Func<ChatAssistantReply, CancellationToken, Task> onCompleteAsync,
        Func<string, CancellationToken, Task> onTokenAsync,
        CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        var prepared = await PrepareContextAsync(
            userMessage,
            history,
            tableCode,
            chatSessionId,
            tableSessionId,
            rollingSummary,
            excludedMenuItemIds,
            facts,
            cancellationToken);

        if (prepared.CatalogReply is not null)
        {
            await onTokenAsync(prepared.CatalogReply.Content, cancellationToken);
            await onCompleteAsync(prepared.CatalogReply, cancellationToken);
            LogStop(stopwatch, "catalog-fastpath-stream");
            return;
        }

        JsonElement? finalPayload = null;
        await foreach (var streamEvent in aiProvider.GenerateStreamAsync(prepared.Request, cancellationToken))
        {
            if (streamEvent.EventType == "token"
                && streamEvent.Data is { ValueKind: JsonValueKind.Object } tokenData
                && tokenData.TryGetProperty("text", out var textElement)
                && textElement.ValueKind == JsonValueKind.String)
            {
                var text = textElement.GetString();
                if (!string.IsNullOrEmpty(text))
                {
                    await onTokenAsync(text, cancellationToken);
                }
            }
            else if (streamEvent.EventType == "final" && streamEvent.Data is not null)
            {
                finalPayload = streamEvent.Data.Value;
            }
        }

        if (finalPayload is null)
        {
            var fallback = new ChatAssistantReply(
                "Xin lỗi, hệ thống hơi chậm. Bạn thử lại sau giây lát nhé.",
                [],
                ["AI_PROVIDER_UNAVAILABLE"],
                SuggestStaffHandoff: true);
            await onCompleteAsync(fallback, cancellationToken);
            LogStop(stopwatch, "stream-fallback");
            return;
        }

        var providerResult = ParseStreamFinal(finalPayload.Value, prepared.AvailableMenuItems, prepared.Request.ExcludedMenuItemIds ?? excludedMenuItemIds);
        var reply = BuildAssistantReply(providerResult, prepared.AvailableMenuItems, excludedMenuItemIds);
        await onCompleteAsync(reply, cancellationToken);
        LogStop(stopwatch, "python-stream");
    }

    private sealed record PreparedChatContext(
        ChatAiRequest Request,
        IReadOnlyList<ChatMenuItemContext> AvailableMenuItems,
        ChatAssistantReply? CatalogReply);

    private async Task<PreparedChatContext> PrepareContextAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        string chatSessionId,
        string? tableSessionId,
        string? rollingSummary,
        IReadOnlySet<string> excludedMenuItemIds,
        IReadOnlyList<ChatSessionFactSnapshot> facts,
        CancellationToken cancellationToken)
    {
        var (categories, menuItems) = await LoadMenuCatalogCachedAsync(cancellationToken);
        var categoryNames = categories.ToDictionary(
            category => category.Id,
            category => category.Name,
            StringComparer.OrdinalIgnoreCase);
        var activeCategoryIds = categories.Select(category => category.Id).ToList();

        var unavailableNames = menuItems
            .Where(item => !item.IsAvailable)
            .Select(item => item.Name)
            .ToList();

        var availableMenuItems = menuItems
            .Where(item => item.IsAvailable && !excludedMenuItemIds.Contains(item.Id))
            .Select(item => new ChatMenuItemContext(
                item.Id,
                item.Name,
                item.Description,
                item.Price,
                item.CategoryId,
                categoryNames[item.CategoryId],
                item.Tags.ToList(),
                item.IsAvailable))
            .ToList();

        var grounding = ChatMenuGrounding.SelectWithConstraints(userMessage, availableMenuItems, null);
        if (grounding.HasExplicitConstraint
            && IsPureCatalogRequest(userMessage)
            && grounding.MatchedCategoryNames.Count > 0)
        {
            return new PreparedChatContext(
                new ChatAiRequest(userMessage, [], availableMenuItems),
                availableMenuItems,
                BuildGroundedCatalog(grounding, availableMenuItems.Count - grounding.Candidates.Count));
        }

        var cartItems = await LoadCartAsync(tableSessionId, cancellationToken);
        var orders = await LoadOrdersAsync(tableSessionId, cancellationToken);
        var promotions = await LoadPromotionsCachedAsync(cancellationToken);
        var localTime = DateTimeOffset.Now;
        var mealPeriod = ResolveMealPeriod(localTime);
        var sessionMemory = BuildSessionMemory(rollingSummary, excludedMenuItemIds, facts, unavailableNames);
        var priorHistory = history.Take(Math.Max(0, history.Count - 1)).ToList();

        var request = new ChatAiRequest(
            userMessage,
            priorHistory,
            availableMenuItems,
            tableCode,
            sessionMemory,
            chatSessionId,
            tableSessionId,
            rollingSummary,
            excludedMenuItemIds,
            facts,
            cartItems,
            orders,
            promotions,
            localTime.ToString("O"),
            mealPeriod);

        return new PreparedChatContext(request, availableMenuItems, null);
    }

    private async Task<(List<Category> Categories, List<MenuItem> Items)> LoadMenuCatalogCachedAsync(CancellationToken ct)
    {
        var cached = await cache.GetOrCreateAsync<(List<Category>, List<MenuItem>)>(
            "chat-menu-catalog",
            async entry =>
            {
                entry.AbsoluteExpirationRelativeToNow = TimeSpan.FromSeconds(30);
                var categories = await db.Categories
                    .AsNoTracking()
                    .Where(category => category.IsActive)
                    .ToListAsync(ct);
                var activeCategoryIds = categories.Select(category => category.Id).ToList();
                var menuItems = await db.MenuItems
                    .AsNoTracking()
                    .Where(item => activeCategoryIds.Contains(item.CategoryId))
                    .ToListAsync(ct);
                return (categories, menuItems);
            });

        return cached;
    }

    private async Task<IReadOnlyList<object>> LoadPromotionsCachedAsync(CancellationToken ct)
    {
        var cached = await cache.GetOrCreateAsync(
            "chat-promotions",
            async entry =>
            {
                entry.AbsoluteExpirationRelativeToNow = TimeSpan.FromSeconds(60);
                return await LoadPromotionsAsync(ct);
            });

        return cached ?? [];
    }

    private ChatAssistantReply BuildAssistantReply(
        ChatAiResult providerResult,
        IReadOnlyList<ChatMenuItemContext> availableMenuItems,
        IReadOnlySet<string> excludedMenuItemIds)
    {
        if (!providerResult.ProviderAvailable
            && (providerResult.SuggestedCartActions is null || providerResult.SuggestedCartActions.Count == 0))
        {
            return new ChatAssistantReply(
                providerResult.Content,
                [],
                providerResult.GuardrailFlags ?? ["AI_PROVIDER_UNAVAILABLE"],
                SuggestStaffHandoff: providerResult.SuggestStaffHandoff,
                FactsToPersist: providerResult.Facts ?? [],
                RejectedMenuItemIds: providerResult.RejectedMenuItemIds ?? []);
        }

        var safeActions = (providerResult.SuggestedCartActions ?? [])
            .Where(a => !excludedMenuItemIds.Contains(a.MenuItemId)
                        && availableMenuItems.Any(m => m.Id.Equals(a.MenuItemId, StringComparison.OrdinalIgnoreCase)))
            .GroupBy(a => a.MenuItemId, StringComparer.OrdinalIgnoreCase)
            .Select(g => g.First())
            .ToList();

        var guardrailFlags = new List<string>(providerResult.GuardrailFlags ?? []);
        if (safeActions.Count > 0 && !guardrailFlags.Contains("CUSTOMER_CONFIRMATION_REQUIRED"))
        {
            guardrailFlags.Add("CUSTOMER_CONFIRMATION_REQUIRED");
        }

        var remaining = Math.Max(0, availableMenuItems.Count - excludedMenuItemIds.Count - safeActions.Count);
        var followUp = providerResult.FollowUp ?? new FollowUpHint(remaining > 0, remaining);

        return new ChatAssistantReply(
            providerResult.Content,
            safeActions,
            guardrailFlags,
            providerResult.SuggestStaffHandoff,
            followUp,
            providerResult.Facts ?? [],
            providerResult.RejectedMenuItemIds ?? [],
            providerResult.UpdatedRollingSummary);
    }

    private static ChatAiResult ParseStreamFinal(
        JsonElement root,
        IReadOnlyList<ChatMenuItemContext> availableMenuItems,
        IReadOnlySet<string> excluded)
    {
        var content = root.TryGetProperty("content", out var contentElement) && contentElement.ValueKind == JsonValueKind.String
            ? contentElement.GetString() ?? ""
            : "";
        var providerAvailable = root.TryGetProperty("provider_available", out var providerElement)
            && providerElement.ValueKind == JsonValueKind.True;
        var handoff = root.TryGetProperty("suggest_staff_handoff", out var h) && h.ValueKind == JsonValueKind.True;
        var followUp = root.TryGetProperty("follow_up", out var followUpElement) && followUpElement.ValueKind == JsonValueKind.Object
            ? new FollowUpHint(
                followUpElement.TryGetProperty("can_show_more", out var c) && c.ValueKind == JsonValueKind.True,
                followUpElement.TryGetProperty("remaining_count", out var r) && r.TryGetInt32(out var rv) ? rv : 0)
            : null;

        var actions = new List<SuggestedCartActionResponse>();
        if (root.TryGetProperty("suggested_cart_actions", out var actionsElement) && actionsElement.ValueKind == JsonValueKind.Array)
        {
            var menuLookup = availableMenuItems.ToDictionary(m => m.Id, StringComparer.OrdinalIgnoreCase);
            foreach (var action in actionsElement.EnumerateArray())
            {
                var menuItemId = action.TryGetProperty("menu_item_id", out var mid) ? mid.GetString() ?? "" : "";
                if (string.IsNullOrWhiteSpace(menuItemId) || excluded.Contains(menuItemId)) continue;
                if (!menuLookup.TryGetValue(menuItemId, out var menuItem) || !menuItem.IsAvailable) continue;
                var name = action.TryGetProperty("name", out var n) && n.ValueKind == JsonValueKind.String
                    ? n.GetString() ?? menuItem.Name
                    : menuItem.Name;
                var quantity = action.TryGetProperty("quantity", out var q) && q.TryGetInt32(out var qv)
                    ? Math.Clamp(qv, 1, 20)
                    : 1;
                var reason = action.TryGetProperty("reason", out var rsn) && rsn.ValueKind == JsonValueKind.String
                    ? rsn.GetString() ?? ""
                    : "";
                actions.Add(new SuggestedCartActionResponse(
                    menuItemId,
                    name,
                    menuItem.Price,
                    quantity,
                    reason,
                    RequiresCustomerConfirmation: true,
                    Status: "pending"));
            }
        }

        var flags = new List<string>();
        if (root.TryGetProperty("guardrail_flags", out var flagsElement) && flagsElement.ValueKind == JsonValueKind.Array)
        {
            foreach (var flag in flagsElement.EnumerateArray())
            {
                if (flag.ValueKind == JsonValueKind.String)
                {
                    var value = flag.GetString()?.Trim();
                    if (!string.IsNullOrEmpty(value)) flags.Add(value);
                }
            }
        }

        return new ChatAiResult(content, providerAvailable, actions, flags, handoff, followUp);
    }

    private void LogStop(Stopwatch stopwatch, string path)
    {
        stopwatch.Stop();
        logger.LogInformation("Chat assistant {Path} completed in {ElapsedMs}ms", path, stopwatch.ElapsedMilliseconds);
    }

    private async Task<IReadOnlyList<object>> LoadCartAsync(string? tableSessionId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(tableSessionId)) return [];

        var items = await db.TableSessionCartItems
            .AsNoTracking()
            .Where(c => c.TableSessionId == tableSessionId)
            .Join(db.MenuItems, c => c.MenuItemId, m => m.Id, (c, m) => new
            {
                menu_item_id = c.MenuItemId,
                name = m.Name,
                quantity = c.Quantity,
                price_vnd = m.Price,
                note = c.Note
            })
            .ToListAsync(ct);

        return items.Cast<object>().ToList();
    }

    private async Task<IReadOnlyList<object>> LoadPromotionsAsync(CancellationToken ct)
    {
        var now = DateTimeOffset.UtcNow;
        var promos = await db.Promotions
            .AsNoTracking()
            .Where(p => p.IsActive
                        && (p.StartsAt == null || p.StartsAt <= now)
                        && (p.EndsAt == null || p.EndsAt >= now))
            .Take(10)
            .Select(p => new { id = p.Id, title = p.Name, description = p.Description })
            .ToListAsync(ct);
        return promos.Cast<object>().ToList();
    }

    private async Task<IReadOnlyList<object>> LoadOrdersAsync(string? tableSessionId, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(tableSessionId)) return [];

        var orders = await db.Orders
            .AsNoTracking()
            .Include(o => o.OrderItems)
            .Where(o => o.TableSessionId == tableSessionId)
            .OrderByDescending(o => o.CreatedAt)
            .Take(5)
            .ToListAsync(ct);

        return orders.Select(o => (object)new
        {
            order_code = o.OrderCode,
            status = o.Status.ToString(),
            items = o.OrderItems.Select(i => new
            {
                menu_item_id = i.MenuItemId,
                name = i.MenuItemName,
                quantity = i.Quantity,
                status = i.Status.ToString()
            })
        }).ToList();
    }

    private static string ResolveMealPeriod(DateTimeOffset local)
    {
        var hour = local.Hour;
        if (hour < 11) return "breakfast";
        if (hour < 14) return "lunch";
        if (hour < 17) return "afternoon";
        return "dinner";
    }

    private static bool IsPureCatalogRequest(string message)
    {
        var lower = message.Trim().ToLowerInvariant();
        var soft = new[]
        {
            "dị ứng", "di ung", "chay", "cay", "ngọt", "ngot", "ít", "it ",
            "ngân sách", "ngan sach", "người", "nguoi", "budget", "allergy",
            "gợi ý", "goi y", "tư vấn", "tu van", "recommend", "cho bé", "cho be"
        };
        if (soft.Any(s => lower.Contains(s, StringComparison.Ordinal)))
        {
            return false;
        }

        var catalog = new[] { "xem", "cho xem", "danh sách", "danh sach", "nhóm", "nhom", "menu", "category" };
        return catalog.Any(c => lower.Contains(c, StringComparison.Ordinal));
    }

    private static ChatAssistantReply BuildGroundedCatalog(ChatMenuGroundingResult grounding, int remainingOutside)
    {
        var scope = grounding.MatchedCategoryNames.Count > 0
            ? $"nhóm {string.Join(", ", grounding.MatchedCategoryNames)}"
            : $"tag {string.Join(", ", grounding.MatchedTags)}";
        if (grounding.Candidates.Count == 0)
        {
            return new ChatAssistantReply(
                $"Hiện chưa có món còn bán phù hợp với {scope} trong thực đơn.",
                [],
                [],
                FollowUp: new FollowUpHint(false, 0));
        }

        var culture = System.Globalization.CultureInfo.GetCultureInfo("vi-VN");
        var take = grounding.Candidates.Take(8).ToList();
        var catalog = string.Join(
            Environment.NewLine,
            take.Select((item, index) =>
                $"{index + 1}. {item.Name} ({item.Id}) - {item.Price.ToString("#,0", culture)}đ: {item.Description}"));

        var actions = take.Select(item => new SuggestedCartActionResponse(
            item.Id,
            item.Name,
            item.Price,
            Quantity: 1,
            Reason: $"Thuộc {scope}, còn bán.",
            RequiresCustomerConfirmation: true,
            Status: "pending")).ToList();

        return new ChatAssistantReply(
            $"Đây là các món thuộc {scope} hiện còn bán:{Environment.NewLine}{Environment.NewLine}{catalog}{Environment.NewLine}{Environment.NewLine}Bạn muốn xem chi tiết hay thêm món nào vào giỏ?",
            actions,
            actions.Count > 0 ? ["CUSTOMER_CONFIRMATION_REQUIRED"] : [],
            FollowUp: new FollowUpHint(grounding.Candidates.Count > take.Count || remainingOutside > 0,
                Math.Max(0, grounding.Candidates.Count - take.Count)));
    }

    private static string BuildSessionMemory(
        string? rollingSummary,
        IReadOnlySet<string> excluded,
        IReadOnlyList<ChatSessionFactSnapshot> facts,
        IReadOnlyList<string> unavailableNames)
    {
        var lines = new List<string>();
        if (excluded.Count > 0)
        {
            lines.Add($"EXCLUDED_MENU_ITEM_IDS: {string.Join(',', excluded.OrderBy(id => id))}");
        }

        if (facts.Count > 0)
        {
            lines.Add("FACTS:");
            lines.AddRange(facts.Select(f => $"- {f.Kind}={f.Value} (conf={f.Confidence:0.00})"));
        }

        if (unavailableNames.Count > 0)
        {
            lines.Add($"CURRENTLY_UNAVAILABLE_NAMES: {string.Join(", ", unavailableNames.Take(20))}");
        }

        if (!string.IsNullOrWhiteSpace(rollingSummary))
        {
            lines.Add("ROLLING_SUMMARY:");
            lines.Add(rollingSummary.Trim());
        }

        var memory = string.Join("\n", lines);
        return memory.Length <= 12000 ? memory : memory[..12000];
    }
}
