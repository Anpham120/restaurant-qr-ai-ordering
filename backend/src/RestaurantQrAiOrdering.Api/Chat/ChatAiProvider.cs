using System.Diagnostics;
using System.Globalization;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
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
    string? MealPeriod = null,
    string? CatalogVersion = null,
    ChatSessionStateSnapshot? SessionState = null);

public sealed record ChatAiResult(
    string Content,
    bool ProviderAvailable,
    IReadOnlyList<SuggestedCartActionResponse>? SuggestedCartActions = null,
    IReadOnlyList<string>? GuardrailFlags = null,
    bool SuggestStaffHandoff = false,
    FollowUpHint? FollowUp = null,
    IReadOnlyList<ChatFactToPersist>? Facts = null,
    IReadOnlyList<string>? RejectedMenuItemIds = null,
    string? UpdatedRollingSummary = null,
    ChatDecisionTrace? Decision = null,
    IReadOnlyList<ChatEvidenceReference>? Evidence = null,
    IReadOnlyList<ChatVerifiedClaim>? Claims = null,
    ChatSessionUpdates? SessionUpdates = null,
    string? Model = null,
    string? PipelineProfile = null,
    IReadOnlyList<string>? ResolvedMenuItemIds = null,
    string? VerifierResult = null);

public sealed record ChatFactToPersist(string Kind, string Value, double Confidence);

public sealed record ChatDecisionTrace(
    string? Intent,
    string? Route,
    double? Confidence,
    bool? EvidenceSufficient,
    string? AbstainReason);

public sealed record ChatEvidenceReference(
    string Source,
    string? Title,
    string? ChunkId,
    string? MenuItemId,
    string? Section,
    double? Score);

public sealed record ChatVerifiedClaim(
    string Text,
    IReadOnlyList<string> EvidenceIds,
    bool Verified,
    string? Reason);

public sealed record ChatSessionUpdates(
    IReadOnlyList<ChatFactToPersist> Facts,
    IReadOnlyDictionary<string, JsonElement> Constraints,
    IReadOnlyList<string> ReferencedMenuItemIds,
    IReadOnlyList<string> SuggestedMenuItemIds,
    IReadOnlyList<string> RejectedMenuItemIds,
    IReadOnlyList<string> AcceptedMenuItemIds,
    IReadOnlyList<string> AddedToCartMenuItemIds,
    string? RollingSummary,
    string MemoryVersion,
    ChatConversationFrame? ConversationFrame = null);

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
        ChatSessionStateSnapshot? sessionState,
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
        ChatSessionStateSnapshot? sessionState,
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
    string? UpdatedRollingSummary = null,
    ChatSessionUpdates? SessionUpdates = null);

public sealed class PythonRagChatProvider : IChatAiProvider
{
    private static readonly JsonSerializerOptions RequestJsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private readonly HttpClient httpClient;
    private readonly IConfiguration configuration;
    private readonly ILogger<PythonRagChatProvider> logger;

    private sealed record ChatRequestV2Payload(
        string ContractVersion,
        string PipelineProfile,
        string Message,
        string? TableCode,
        string SessionId,
        string? TableSessionId,
        string RollingSummary,
        string MenuVersion,
        string CatalogVersion,
        ChatSessionStatePayload SessionState,
        ChatLiveContextPayload LiveContext,
        IReadOnlyList<string> ExcludedMenuItemIds,
        IReadOnlyList<ChatFactPayload> Facts,
        IReadOnlyList<object> CartItems,
        IReadOnlyList<object> Orders,
        IReadOnlyList<object> Promotions,
        string? LocalTime,
        string? MealPeriod,
        IReadOnlyList<ChatHistoryPayload> History,
        string SessionMemory,
        IReadOnlyList<ChatMenuItemPayload> MenuItems);

    private sealed record ChatSessionStatePayload(
        IReadOnlyList<ChatFactPayload> Facts,
        IReadOnlyDictionary<string, object?> Constraints,
        IReadOnlyList<string> ReferencedMenuItemIds,
        IReadOnlyList<string> SuggestedMenuItemIds,
        IReadOnlyList<string> RejectedMenuItemIds,
        IReadOnlyList<string> AcceptedMenuItemIds,
        IReadOnlyList<string> AddedToCartMenuItemIds,
        string RollingSummary,
        string MemoryVersion,
        ChatConversationFrame? ConversationFrame);

    private sealed record ChatLiveContextPayload(
        string CatalogVersion,
        IReadOnlyList<ChatMenuItemPayload> MenuItems,
        IReadOnlyList<object> CartItems,
        IReadOnlyList<object> Orders,
        IReadOnlyList<object> Promotions,
        string? LocalTime,
        string? MealPeriod,
        string? TableCode);

    private sealed record ChatFactPayload(string Kind, string Value, double Confidence);

    private sealed record ChatHistoryPayload(
        string Role,
        string Content,
        IReadOnlyList<ChatHistoryActionPayload> SuggestedCartActions);

    private sealed record ChatHistoryActionPayload(string MenuItemId, string Name);

    private sealed record ChatMenuItemPayload(
        string Id,
        string CategoryId,
        string CategoryName,
        string Name,
        string Description,
        decimal PriceVnd,
        IReadOnlyList<string> Tags,
        bool IsAvailable);

    public PythonRagChatProvider(
        HttpClient httpClient,
        IConfiguration configuration,
        ILogger<PythonRagChatProvider> logger)
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
            Content = JsonContent.Create(payload, options: RequestJsonOptions)
        };
        if (!TryAddInternalAuthorization(httpRequest))
        {
            yield return new ChatStreamEvent("final", JsonDocument.Parse("""
                {"content":"Trợ lý AI chưa được cấu hình xác thực nội bộ.","provider_available":false,"suggest_staff_handoff":true,"guardrail_flags":["AI_PROVIDER_UNAVAILABLE"]}
                """).RootElement);
            yield return new ChatStreamEvent("done", JsonDocument.Parse("{\"ok\":true}").RootElement);
            yield break;
        }

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
        while (!timeoutCts.IsCancellationRequested)
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
            using var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
            {
                Content = JsonContent.Create(payload, options: RequestJsonOptions)
            };
            if (!TryAddInternalAuthorization(httpRequest))
            {
                return Unavailable();
            }
            using var response = await httpClient.SendAsync(httpRequest, timeoutCts.Token);
            if (!response.IsSuccessStatusCode)
            {
                logger.LogWarning("Python AI service returned HTTP {StatusCode}.", (int)response.StatusCode);
                return SlowFallback();
            }

            using var json = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(timeoutCts.Token),
                cancellationToken: timeoutCts.Token);

            var excluded = request.ExcludedMenuItemIds ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var result = ParseResponsePayload(json.RootElement, request.AvailableMenuItems, excluded);
            if (string.IsNullOrWhiteSpace(result.Content))
            {
                return SlowFallback();
            }

            logger.LogInformation(
                "Python AI chat completed in {ElapsedMs}ms profile={PipelineProfile} model={Model} route={Route} resolved_menu_item_ids={ResolvedMenuItemIds} verifier_result={VerifierResult}",
                stopwatch.ElapsedMilliseconds,
                result.PipelineProfile ?? "unknown",
                result.Model ?? "unknown",
                result.Decision?.Route ?? "unknown",
                string.Join(",", result.ResolvedMenuItemIds ?? []),
                result.VerifierResult ?? "unknown");
            return result;
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            logger.LogWarning(exception, "Python AI service request failed after {ElapsedMs}ms.", stopwatch.ElapsedMilliseconds);
            return SlowFallback();
        }
    }

    private ChatRequestV2Payload BuildPayload(ChatAiRequest request)
    {
        var excluded = (request.ExcludedMenuItemIds ?? new HashSet<string>(StringComparer.OrdinalIgnoreCase))
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .Select(id => id.Trim())
            .OrderBy(id => id, StringComparer.Ordinal)
            .ToList();
        var persistedState = request.SessionState;
        var facts = (persistedState?.Facts ?? request.Facts ?? [])
            .Select(fact => new ChatFactPayload(fact.Kind, fact.Value, fact.Confidence))
            .ToList();
        var history = request.History
            .TakeLast(12)
            .Select(message => new ChatHistoryPayload(
                message.Role,
                message.Content,
                message.SuggestedCartActions
                    .Select(action => new ChatHistoryActionPayload(action.MenuItemId, action.Name))
                    .ToList()))
            .ToList();
        var menuItems = request.AvailableMenuItems
            .Select(item => new ChatMenuItemPayload(
                item.Id,
                item.CategoryId,
                item.CategoryName,
                item.Name,
                item.Description,
                item.Price,
                item.Tags,
                item.IsAvailable))
            .ToList();
        var catalogVersion = string.IsNullOrWhiteSpace(request.CatalogVersion)
            ? ComputeCatalogVersion(request.AvailableMenuItems)
            : request.CatalogVersion.Trim();
        var historyActions = request.History.SelectMany(message => message.SuggestedCartActions).ToList();
        var referencedIds = persistedState is not null
            ? StableDistinct(persistedState.ReferencedMenuItemIds)
            : StableDistinct(historyActions.Select(action => action.MenuItemId));
        var suggestedIds = persistedState is not null
            ? StableDistinct(persistedState.SuggestedMenuItemIds)
            : StableDistinct(referencedIds.Concat(excluded));
        var rejectedIds = persistedState is not null
            ? StableDistinct(persistedState.RejectedMenuItemIds)
            : StableDistinct(historyActions
                .Where(action => action.Status is "dismissed" or "rejected")
                .Select(action => action.MenuItemId));
        var acceptedIds = persistedState is not null
            ? StableDistinct(persistedState.AcceptedMenuItemIds)
            : StableDistinct(historyActions
                .Where(action => action.Status is "confirmed" or "accepted")
                .Select(action => action.MenuItemId));
        var addedToCartIds = StableDistinct(
            (persistedState?.AddedToCartMenuItemIds ?? [])
            .Concat(ExtractCartMenuItemIds(request.CartItems ?? [])));
        var rollingSummary = persistedState?.RollingSummary ?? request.RollingSummary ?? "";
        var cartItems = request.CartItems ?? [];
        var orders = request.Orders ?? [];
        var promotions = request.Promotions ?? [];
        var constraints = persistedState?.Constraints.ToDictionary(
            item => item.Key,
            item => (object?)item.Value.Clone(),
            StringComparer.Ordinal)
            ?? new Dictionary<string, object?>(StringComparer.Ordinal);
        var sessionState = new ChatSessionStatePayload(
            facts,
            constraints,
            referencedIds,
            suggestedIds,
            rejectedIds,
            acceptedIds,
            addedToCartIds,
            rollingSummary,
            persistedState?.MemoryVersion ?? "v1",
            persistedState?.ConversationFrame);
        var liveContext = new ChatLiveContextPayload(
            catalogVersion,
            menuItems,
            cartItems,
            orders,
            promotions,
            request.LocalTime,
            request.MealPeriod,
            request.TableCode);

        // Keep the legacy top-level aliases for one release while V2 consumers move to typed state/context.
        return new ChatRequestV2Payload(
            "v2",
            ReadPipelineProfile(),
            request.UserMessage,
            request.TableCode,
            request.ChatSessionId ?? "",
            request.TableSessionId,
            rollingSummary,
            catalogVersion,
            catalogVersion,
            sessionState,
            liveContext,
            excluded,
            facts,
            cartItems,
            orders,
            promotions,
            request.LocalTime,
            request.MealPeriod,
            history,
            request.SessionMemory,
            menuItems);
    }

    private string ReadPipelineProfile()
    {
        const string fallback = "llm_first_v1";
        var profile = configuration["AI_PIPELINE_PROFILE"]?.Trim();
        if (string.IsNullOrWhiteSpace(profile))
        {
            return fallback;
        }

        return profile is "llm_first_v1" or "evidence_first_v2" or "planner_state_v3"
            ? profile
            : throw new InvalidOperationException(
                $"Unsupported AI_PIPELINE_PROFILE '{profile}'.");
    }

    internal static string ComputeCatalogVersion(IReadOnlyList<ChatMenuItemContext> menuItems)
    {
        var canonical = new StringBuilder();
        foreach (var item in menuItems
                     .OrderBy(item => item.Id, StringComparer.Ordinal)
                     .ThenBy(item => item.Name, StringComparer.Ordinal))
        {
            AppendCatalogValue(canonical, item.Id);
            AppendCatalogValue(canonical, item.CategoryId);
            AppendCatalogValue(canonical, item.CategoryName);
            AppendCatalogValue(canonical, item.Name);
            AppendCatalogValue(canonical, item.Description);
            AppendCatalogValue(canonical, item.Price.ToString("G29", CultureInfo.InvariantCulture));
            AppendCatalogValue(canonical, item.IsAvailable ? "1" : "0");
            foreach (var tag in item.Tags.OrderBy(tag => tag, StringComparer.Ordinal))
            {
                AppendCatalogValue(canonical, tag);
            }

            canonical.Append('\n');
        }

        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(canonical.ToString()));
        return $"catalog-sha256-{Convert.ToHexString(hash).ToLowerInvariant()}";
    }

    private static void AppendCatalogValue(StringBuilder builder, string? value)
    {
        var normalized = value ?? "";
        builder.Append(normalized.Length).Append(':').Append(normalized).Append('|');
    }

    private static IReadOnlyList<string> StableDistinct(IEnumerable<string?> values)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var result = new List<string>();
        foreach (var value in values)
        {
            var normalized = value?.Trim();
            if (!string.IsNullOrEmpty(normalized) && seen.Add(normalized))
            {
                result.Add(normalized);
            }
        }

        return result;
    }

    private static IReadOnlyList<string> ExtractCartMenuItemIds(IReadOnlyList<object> cartItems)
    {
        var ids = new List<string?>();
        foreach (var item in cartItems)
        {
            var element = item is JsonElement jsonElement
                ? jsonElement
                : JsonSerializer.SerializeToElement(item, RequestJsonOptions);
            if (element.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            if ((element.TryGetProperty("menu_item_id", out var snakeId)
                 || element.TryGetProperty("menuItemId", out snakeId))
                && snakeId.ValueKind == JsonValueKind.String)
            {
                ids.Add(snakeId.GetString());
            }
        }

        return StableDistinct(ids);
    }

    private int ReadPositiveInt(string key, string fallbackKey, int defaultValue)
    {
        var rawValue = configuration[key]
            ?? configuration[fallbackKey]
            ?? configuration[$"Ai:{key[3..]}"];
        return int.TryParse(rawValue, out var value) && value > 0 ? value : defaultValue;
    }

    private bool TryAddInternalAuthorization(HttpRequestMessage request)
    {
        var token = configuration["AI_INTERNAL_TOKEN"]?.Trim();
        if (string.IsNullOrWhiteSpace(token))
        {
            logger.LogError("AI_INTERNAL_TOKEN is missing; refusing an unauthenticated AI request.");
            return false;
        }

        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return true;
    }

    internal static ChatAiResult ParseResponsePayload(
        JsonElement root,
        IReadOnlyList<ChatMenuItemContext> availableMenuItems,
        IReadOnlySet<string> excluded)
    {
        if (root.ValueKind != JsonValueKind.Object)
        {
            return SlowFallback();
        }

        var hasSessionUpdates = root.TryGetProperty("session_updates", out var sessionUpdatesElement)
                                && sessionUpdatesElement.ValueKind == JsonValueKind.Object;
        var facts = hasSessionUpdates && sessionUpdatesElement.TryGetProperty("facts", out _)
            ? ExtractFacts(sessionUpdatesElement)
            : ExtractFacts(root);
        var rejectedIds = hasSessionUpdates && sessionUpdatesElement.TryGetProperty("rejected_menu_item_ids", out _)
            ? ExtractStringArray(sessionUpdatesElement, "rejected_menu_item_ids")
            : ExtractStringArray(root, "rejected_menu_item_ids");
        var updatedSummary = hasSessionUpdates
            ? ExtractOptionalString(sessionUpdatesElement, "rolling_summary")
            : null;
        updatedSummary ??= ExtractOptionalString(root, "updated_rolling_summary");

        return new ChatAiResult(
            (ExtractPythonRagContent(root) ?? "").Trim(),
            ProviderAvailable: ExtractProviderAvailable(root),
            SuggestedCartActions: ExtractPythonSuggestedActions(root, availableMenuItems, excluded),
            GuardrailFlags: ExtractPythonGuardrailFlags(root),
            SuggestStaffHandoff: root.TryGetProperty("suggest_staff_handoff", out var handoff)
                                 && handoff.ValueKind == JsonValueKind.True,
            FollowUp: ExtractFollowUp(root),
            Facts: facts,
            RejectedMenuItemIds: rejectedIds,
            UpdatedRollingSummary: updatedSummary,
            Decision: ExtractDecision(root),
            Evidence: ExtractEvidence(root),
            Claims: ExtractClaims(root),
            SessionUpdates: hasSessionUpdates ? ExtractSessionUpdates(sessionUpdatesElement) : null,
            Model: ExtractOptionalString(root, "model"),
            PipelineProfile: ExtractOptionalString(root, "pipeline_profile"),
            ResolvedMenuItemIds: ExtractStringArray(root, "resolved_menu_item_ids"),
            VerifierResult: ExtractOptionalString(root, "verifier_result"));
    }

    private static ChatDecisionTrace? ExtractDecision(JsonElement root)
    {
        if (!root.TryGetProperty("decision", out var decision) || decision.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        return new ChatDecisionTrace(
            ExtractOptionalString(decision, "intent"),
            ExtractOptionalString(decision, "route"),
            ExtractOptionalDouble(decision, "confidence"),
            ExtractOptionalBoolean(decision, "evidence_sufficient"),
            ExtractOptionalString(decision, "abstain_reason"));
    }

    private static IReadOnlyList<ChatEvidenceReference> ExtractEvidence(JsonElement root)
    {
        var results = new List<ChatEvidenceReference>();
        if (!root.TryGetProperty("evidence", out var evidence) || evidence.ValueKind != JsonValueKind.Array)
        {
            return results;
        }

        foreach (var item in evidence.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            results.Add(new ChatEvidenceReference(
                ExtractOptionalString(item, "source") ?? "",
                ExtractOptionalString(item, "title"),
                ExtractOptionalString(item, "chunk_id"),
                ExtractOptionalString(item, "menu_item_id"),
                ExtractOptionalString(item, "section"),
                ExtractOptionalDouble(item, "score")));
        }

        return results;
    }

    private static IReadOnlyList<ChatVerifiedClaim> ExtractClaims(JsonElement root)
    {
        var results = new List<ChatVerifiedClaim>();
        if (!root.TryGetProperty("claims", out var claims) || claims.ValueKind != JsonValueKind.Array)
        {
            return results;
        }

        foreach (var item in claims.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            var text = ExtractOptionalString(item, "text");
            if (string.IsNullOrWhiteSpace(text))
            {
                continue;
            }

            results.Add(new ChatVerifiedClaim(
                text,
                ExtractStringArray(item, "evidence_ids"),
                item.TryGetProperty("verified", out var verified) && verified.ValueKind == JsonValueKind.True,
                ExtractOptionalString(item, "reason")));
        }

        return results;
    }

    private static ChatSessionUpdates ExtractSessionUpdates(JsonElement updates)
    {
        var constraints = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        if (updates.TryGetProperty("constraints", out var constraintsElement)
            && constraintsElement.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in constraintsElement.EnumerateObject())
            {
                constraints[property.Name] = property.Value.Clone();
            }
        }

        return new ChatSessionUpdates(
            ExtractFacts(updates),
            constraints,
            ExtractStringArray(updates, "referenced_menu_item_ids"),
            ExtractStringArray(updates, "suggested_menu_item_ids"),
            ExtractStringArray(updates, "rejected_menu_item_ids"),
            ExtractStringArray(updates, "accepted_menu_item_ids"),
            ExtractStringArray(updates, "added_to_cart_menu_item_ids"),
            ExtractOptionalString(updates, "rolling_summary"),
            ExtractOptionalString(updates, "memory_version") ?? "v1",
            ExtractConversationFrame(updates));
    }

    private static ChatConversationFrame? ExtractConversationFrame(JsonElement root)
    {
        if (!root.TryGetProperty("conversation_frame", out var frame)
            || frame.ValueKind != JsonValueKind.Object)
        {
            return null;
        }

        try
        {
            return JsonSerializer.Deserialize<ChatConversationFrame>(
                frame.GetRawText(),
                RequestJsonOptions);
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static string? ExtractOptionalString(JsonElement root, string property)
    {
        return root.ValueKind == JsonValueKind.Object
               && root.TryGetProperty(property, out var value)
               && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
    }

    private static double? ExtractOptionalDouble(JsonElement root, string property)
    {
        return root.ValueKind == JsonValueKind.Object
               && root.TryGetProperty(property, out var value)
               && value.ValueKind == JsonValueKind.Number
               && value.TryGetDouble(out var number)
            ? number
            : null;
    }

    private static bool? ExtractOptionalBoolean(JsonElement root, string property)
    {
        if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty(property, out var value))
        {
            return null;
        }

        return value.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            _ => null
        };
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
            if (action.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            var menuItemId = action.TryGetProperty("menu_item_id", out var mid)
                             && mid.ValueKind == JsonValueKind.String
                ? mid.GetString() ?? ""
                : "";
            if (!availableIds.Contains(menuItemId) || excluded.Contains(menuItemId)) continue;
            if (!menuLookup.TryGetValue(menuItemId, out var menuItem) || !menuItem.IsAvailable) continue;

            var name = action.TryGetProperty("name", out var n) && n.ValueKind == JsonValueKind.String
                ? n.GetString() ?? menuItem.Name : menuItem.Name;
            var quantity = action.TryGetProperty("quantity", out var q)
                           && q.ValueKind == JsonValueKind.Number
                           && q.TryGetInt32(out var qv)
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
        var remaining = followUp.TryGetProperty("remaining_count", out var r)
                        && r.ValueKind == JsonValueKind.Number
                        && r.TryGetInt32(out var rv)
            ? rv
            : 0;
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
            if (fact.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            var kind = ExtractOptionalString(fact, "kind");
            var value = fact.TryGetProperty("value", out var factValue)
                ? ExtractFactValue(factValue)
                : null;
            var confidence = fact.TryGetProperty("confidence", out var c)
                             && c.ValueKind == JsonValueKind.Number
                             && c.TryGetDouble(out var cv)
                ? cv
                : 0.8;
            if (!string.IsNullOrWhiteSpace(kind) && !string.IsNullOrWhiteSpace(value))
            {
                results.Add(new ChatFactToPersist(kind, value, confidence));
            }
        }

        return results;
    }

    private static string? ExtractFactValue(JsonElement value)
    {
        return value.ValueKind switch
        {
            JsonValueKind.String => value.GetString(),
            JsonValueKind.Number or JsonValueKind.True or JsonValueKind.False => value.GetRawText(),
            JsonValueKind.Object or JsonValueKind.Array => value.GetRawText(),
            _ => null
        };
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
        ChatSessionStateSnapshot? sessionState,
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
            sessionState,
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
        ChatSessionStateSnapshot? sessionState,
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
            sessionState,
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
        logger.LogInformation(
            "Python AI stream profile={PipelineProfile} model={Model} route={Route} resolved_menu_item_ids={ResolvedMenuItemIds} verifier_result={VerifierResult}",
            providerResult.PipelineProfile ?? "unknown",
            providerResult.Model ?? "unknown",
            providerResult.Decision?.Route ?? "unknown",
            string.Join(",", providerResult.ResolvedMenuItemIds ?? []),
            providerResult.VerifierResult ?? "unknown");
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
        ChatSessionStateSnapshot? sessionState,
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

        var catalogMenuItems = menuItems
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
        var availableMenuItems = catalogMenuItems
            .Where(item => item.IsAvailable && !excludedMenuItemIds.Contains(item.Id))
            .ToList();
        var catalogVersion = PythonRagChatProvider.ComputeCatalogVersion(availableMenuItems);

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
            mealPeriod,
            catalogVersion,
            sessionState);

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
        var safeSessionUpdates = SanitizeAiSessionUpdates(providerResult.SessionUpdates);
        if (!providerResult.ProviderAvailable
            && (providerResult.SuggestedCartActions is null || providerResult.SuggestedCartActions.Count == 0))
        {
            return new ChatAssistantReply(
                providerResult.Content,
                [],
                providerResult.GuardrailFlags ?? ["AI_PROVIDER_UNAVAILABLE"],
                SuggestStaffHandoff: providerResult.SuggestStaffHandoff,
                FactsToPersist: providerResult.Facts ?? [],
                RejectedMenuItemIds: providerResult.RejectedMenuItemIds ?? [],
                UpdatedRollingSummary: providerResult.UpdatedRollingSummary,
                SessionUpdates: safeSessionUpdates);
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
            providerResult.UpdatedRollingSummary,
            safeSessionUpdates);
    }

    private static ChatSessionUpdates? SanitizeAiSessionUpdates(ChatSessionUpdates? updates)
    {
        if (updates is null)
        {
            return null;
        }

        return updates with
        {
            AcceptedMenuItemIds = [],
            AddedToCartMenuItemIds = []
        };
    }

    private static ChatAiResult ParseStreamFinal(
        JsonElement root,
        IReadOnlyList<ChatMenuItemContext> availableMenuItems,
        IReadOnlySet<string> excluded) =>
        PythonRagChatProvider.ParseResponsePayload(root, availableMenuItems, excluded);

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
