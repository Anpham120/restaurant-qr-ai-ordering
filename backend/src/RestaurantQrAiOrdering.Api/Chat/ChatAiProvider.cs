using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record ChatAiRequest(
    string UserMessage,
    IReadOnlyList<ChatMessageSnapshot> History,
    IReadOnlyList<ChatMenuItemContext> AvailableMenuItems,
    string? TableCode = null,
    string SessionMemory = "");

public sealed record ChatAiResult(
    string Content,
    bool ProviderAvailable,
    IReadOnlyList<SuggestedCartActionResponse>? SuggestedCartActions = null,
    IReadOnlyList<string>? GuardrailFlags = null);

public interface IChatAiProvider
{
    Task<ChatAiResult> GenerateAsync(ChatAiRequest request, CancellationToken cancellationToken);
}

public interface IChatAssistantService
{
    Task<ChatAssistantReply> GenerateReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        CancellationToken cancellationToken);
}

public sealed record ChatAssistantReply(
    string Content,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions,
    IReadOnlyList<string> GuardrailFlags);

public sealed class GeminiChatProvider : IChatAiProvider
{
    private const string GeminiOpenAiBaseUrl = "https://generativelanguage.googleapis.com/v1beta/openai";
    private static readonly object RestaurantResponseFormat = new
    {
        type = "json_schema",
        json_schema = new
        {
            name = "restaurant_chat_response",
            strict = true,
            schema = new
            {
                type = "object",
                properties = new
                {
                    content = new { type = "string" },
                    suggested_cart_actions = new
                    {
                        type = "array",
                        items = new
                        {
                            type = "object",
                            properties = new
                            {
                                menu_item_id = new { type = "string" },
                                name = new { type = "string" },
                                price_vnd = new { type = new[] { "number", "null" } },
                                quantity = new { type = "integer" },
                                reason = new { type = new[] { "string", "null" } },
                                requires_customer_confirmation = new { type = "boolean" }
                            },
                            required = new[]
                            {
                                "menu_item_id", "name", "price_vnd", "quantity", "reason", "requires_customer_confirmation"
                            },
                            additionalProperties = false
                        }
                    },
                    guardrail_flags = new { type = "array", items = new { type = "string" } }
                },
                required = new[] { "content", "suggested_cart_actions", "guardrail_flags" },
                additionalProperties = false
            }
        }
    };
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
        var provider = configuration["AI_PROVIDER"] ?? configuration["Ai:Provider"];
        if (string.Equals(provider, "python-rag", StringComparison.OrdinalIgnoreCase))
        {
            return await GenerateWithPythonRagAsync(request, cancellationToken);
        }

        var apiKey = configuration["GEMINI_API_KEY"];
        var model = configuration["AI_MODEL"] ?? configuration["Ai:Model"];

        if (!string.Equals(provider, "gemini", StringComparison.OrdinalIgnoreCase)
            || string.IsNullOrWhiteSpace(apiKey)
            || string.IsNullOrWhiteSpace(model))
        {
            return Unavailable();
        }

        var timeoutSeconds = ReadPositiveInt("AI_TIMEOUT_SECONDS", defaultValue: 8);
        var maxRetry = ReadPositiveInt("AI_MAX_RETRY", defaultValue: 0);
        var endpoint = $"{GeminiOpenAiBaseUrl}/chat/completions";

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));

        for (var attempt = 0; attempt <= maxRetry; attempt++)
        {
            try
            {
                using var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
                {
                    Content = JsonContent.Create(new
                    {
                        model,
                        stream = false,
                        temperature = 0.2,
                        reasoning_effort = "low",
                        response_format = RestaurantResponseFormat,
                        messages = BuildMessages(request)
                    })
                };

                httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

                using var response = await httpClient.SendAsync(httpRequest, timeoutCts.Token);
                if (!response.IsSuccessStatusCode)
                {
                    logger.LogWarning("AI provider returned HTTP {StatusCode}.", (int)response.StatusCode);
                    continue;
                }

                using var payload = await JsonDocument.ParseAsync(
                    await response.Content.ReadAsStreamAsync(timeoutCts.Token),
                    cancellationToken: timeoutCts.Token);

                var content = ExtractAssistantContent(payload.RootElement);
                if (!string.IsNullOrWhiteSpace(content))
                {
                    // Try to parse structured JSON from LLM (content may be JSON)
                    var (parsedContent, actions, flags) = TryParseStructuredContent(content.Trim(), request.AvailableMenuItems);
                    return new ChatAiResult(DeduplicateResponseLines(parsedContent), ProviderAvailable: true, actions, flags);
                }
            }
            catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException)
            {
                logger.LogWarning(exception, "AI provider request failed.");
            }
        }

        return Unavailable();
    }

    private async Task<ChatAiResult> GenerateWithPythonRagAsync(ChatAiRequest request, CancellationToken cancellationToken)
    {
        var serviceUrl = configuration["AI_SERVICE_URL"] ?? configuration["Ai:ServiceUrl"];
        if (string.IsNullOrWhiteSpace(serviceUrl))
        {
            return Unavailable();
        }

        var timeoutSeconds = ReadPositiveInt("AI_TIMEOUT_SECONDS", defaultValue: 8);
        var maxRetry = ReadPositiveInt("AI_MAX_RETRY", defaultValue: 0);
        var endpoint = $"{serviceUrl.TrimEnd('/')}/v1/chat";

        using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutCts.CancelAfter(TimeSpan.FromSeconds(timeoutSeconds));

        var payload = new
        {
            message = request.UserMessage,
            table_code = request.TableCode,
            history = request.History
                .TakeLast(6)
                .Select(message => new
                {
                    role = message.Role,
                    content = message.Content
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

        for (var attempt = 0; attempt <= maxRetry; attempt++)
        {
            try
            {
                using var response = await httpClient.PostAsJsonAsync(endpoint, payload, timeoutCts.Token);
                if (!response.IsSuccessStatusCode)
                {
                    logger.LogWarning("Python AI service returned HTTP {StatusCode}.", (int)response.StatusCode);
                    continue;
                }

                using var json = await JsonDocument.ParseAsync(
                    await response.Content.ReadAsStreamAsync(timeoutCts.Token),
                    cancellationToken: timeoutCts.Token);

                var content = ExtractPythonRagContent(json.RootElement);
                if (!string.IsNullOrWhiteSpace(content))
                {
                    var actions = ExtractPythonSuggestedActions(json.RootElement, request.AvailableMenuItems);
                    var flags = ExtractPythonGuardrailFlags(json.RootElement);
                    return new ChatAiResult(content.Trim(), ProviderAvailable: ExtractProviderAvailable(json.RootElement), actions, flags);
                }
            }
            catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException)
            {
                logger.LogWarning(exception, "Python AI service request failed.");
            }
        }

        return Unavailable();
    }

    private int ReadPositiveInt(string key, int defaultValue)
    {
        var rawValue = configuration[key] ?? configuration[$"Ai:{key[3..]}"];
        return int.TryParse(rawValue, out var value) && value > 0 ? value : defaultValue;
    }

    private static object[] BuildMessages(ChatAiRequest request)
    {
        var menuContext = string.Join(
            "\n",
            request.AvailableMenuItems
                .Take(8)
                .Select(item => $"- {item.Id}: {item.Name}, category {item.CategoryName}, price {item.Price:0} VND, tags {string.Join(", ", item.Tags)}"));

        var recentHistory = request.History
            .TakeLast(6)
            .Select(message => new
            {
                role = message.Role,
                content = message.Content
            });

        var messages = new List<object>
        {
            new
            {
                role = "system",
                content = "You are the CMC Restaurant assistant. Answer only about menu, FAQ, restaurant policy, and safe dish suggestions. The available menu context is the exact candidate set: only mention or propose those items. Do not create orders, do not make payments, do not add items to cart. Do not repeat a sentence or an item in one response. If context is insufficient, say the system does not have enough information. Keep the answer concise in Vietnamese and list at most four items."
            },
            new
            {
                role = "system",
                content = $"Available menu context:\n{menuContext}"
            }
        };

        if (!string.IsNullOrWhiteSpace(request.SessionMemory))
        {
            messages.Add(new
            {
                role = "system",
                content = $"Earlier table-session memory:\n{request.SessionMemory}"
            });
        }

        messages.AddRange(recentHistory.Cast<object>());
        messages.Add(new
        {
            role = "user",
            content = request.UserMessage
        });

        return messages.ToArray();
    }

    private static string? ExtractAssistantContent(JsonElement root)
    {
        if (!root.TryGetProperty("choices", out var choices) || choices.ValueKind != JsonValueKind.Array)
        {
            return null;
        }

        var firstChoice = choices.EnumerateArray().FirstOrDefault();
        if (firstChoice.ValueKind == JsonValueKind.Undefined)
        {
            return null;
        }

        if (firstChoice.TryGetProperty("message", out var message)
            && message.TryGetProperty("content", out var content)
            && content.ValueKind == JsonValueKind.String)
        {
            return content.GetString();
        }

        if (firstChoice.TryGetProperty("text", out var text)
            && text.ValueKind == JsonValueKind.String)
        {
            return text.GetString();
        }

        return null;
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
        JsonElement root, IReadOnlyList<ChatMenuItemContext> availableMenuItems)
    {
        var results = new List<SuggestedCartActionResponse>();
        if (!root.TryGetProperty("suggested_cart_actions", out var actionsElement)
            || actionsElement.ValueKind != JsonValueKind.Array)
        {
            return results;
        }

        var availableIds = new HashSet<string>(availableMenuItems.Select(m => m.Id));
        var menuLookup = availableMenuItems.ToDictionary(m => m.Id);

        foreach (var action in actionsElement.EnumerateArray())
        {
            var menuItemId = action.TryGetProperty("menu_item_id", out var mid) ? mid.GetString() ?? "" : "";
            if (!availableIds.Contains(menuItemId)) continue;

            var menuItem = menuLookup[menuItemId];
            var name = action.TryGetProperty("name", out var n) && n.ValueKind == JsonValueKind.String
                ? n.GetString() ?? menuItem.Name : menuItem.Name;
            var quantity = action.TryGetProperty("quantity", out var q) && q.TryGetInt32(out var qv)
                ? Math.Clamp(qv, 1, 20) : 1;
            var reason = action.TryGetProperty("reason", out var r) && r.ValueKind == JsonValueKind.String
                ? r.GetString() ?? "" : "";

            results.Add(new SuggestedCartActionResponse(
                menuItemId, name, menuItem.Price, quantity, reason,
                RequiresCustomerConfirmation: true));
        }
        return results;
    }

    private static List<string> ExtractPythonGuardrailFlags(JsonElement root)
    {
        var results = new List<string>();
        if (!root.TryGetProperty("guardrail_flags", out var flagsElement)
            || flagsElement.ValueKind != JsonValueKind.Array)
        {
            return results;
        }
        foreach (var flag in flagsElement.EnumerateArray())
        {
            if (flag.ValueKind == JsonValueKind.String)
            {
                var value = flag.GetString()?.Trim();
                if (!string.IsNullOrEmpty(value)) results.Add(value);
            }
        }
        return results;
    }

    private static (string Content, List<SuggestedCartActionResponse> Actions, List<string> Flags)
        TryParseStructuredContent(string rawContent, IReadOnlyList<ChatMenuItemContext> availableMenuItems)
    {
        // LLM may return JSON with content + suggested_cart_actions
        try
        {
            using var doc = JsonDocument.Parse(rawContent);
            var root = doc.RootElement;
            if (root.TryGetProperty("content", out var contentEl) && contentEl.ValueKind == JsonValueKind.String)
            {
                var content = contentEl.GetString()?.Trim() ?? rawContent;
                var actions = ExtractPythonSuggestedActions(root, availableMenuItems);
                var flags = ExtractPythonGuardrailFlags(root);
                return (content, actions, flags);
            }
        }
        catch (JsonException) { /* not JSON, use raw content */ }
        return (rawContent, [], []);
    }

    private static string DeduplicateResponseLines(string content)
    {
        var unique = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var line in Regex.Split(content, @"(?<=[.!?])\s+|\r?\n", RegexOptions.CultureInvariant)
                     .Where(value => !string.IsNullOrWhiteSpace(value))
                     .Select(value => value.Trim()))
        {
            var fingerprint = new string(line
                .Where(char.IsLetterOrDigit)
                .Select(char.ToLowerInvariant)
                .ToArray());
            if (fingerprint.Length == 0 || seen.Add(fingerprint))
            {
                unique.Add(line);
            }
        }

        return unique.Count == 0 ? content.Trim() : string.Join(' ', unique);
    }

    private static ChatAiResult Unavailable()
    {
        return new ChatAiResult(
            "Hiện tại trợ lý AI chưa sẵn sàng. Bạn vẫn có thể xem thực đơn và đặt món trực tiếp trên hệ thống.",
            ProviderAvailable: false);
    }
}

public sealed class ChatAssistantService : IChatAssistantService
{
    private readonly RestaurantDbContext db;
    private readonly IChatAiProvider aiProvider;

    public ChatAssistantService(RestaurantDbContext db, IChatAiProvider aiProvider)
    {
        this.db = db;
        this.aiProvider = aiProvider;
    }

    public async Task<ChatAssistantReply> GenerateReplyAsync(
        string userMessage,
        IReadOnlyList<ChatMessageSnapshot> history,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        var normalizedMessage = Normalize(userMessage);
        if (IsOutOfScope(normalizedMessage))
        {
            return new ChatAssistantReply(
                "Mình chỉ hỗ trợ chọn món, hỏi đáp thực đơn và gợi ý giỏ hàng an toàn cho CMC Restaurant.",
                [],
                ["OUT_OF_SCOPE"]);
        }

        var categories = await db.Categories
            .AsNoTracking()
            .Where(category => category.IsActive)
            .ToListAsync(cancellationToken);
        var categoryNames = categories.ToDictionary(
            category => category.Id,
            category => category.Name,
            StringComparer.OrdinalIgnoreCase);
        var activeCategoryIds = categories.Select(category => category.Id).ToList();
        var menuItems = await db.MenuItems
            .AsNoTracking()
            .Where(item => activeCategoryIds.Contains(item.CategoryId))
            .ToListAsync(cancellationToken);
        var unavailableMatch = menuItems.FirstOrDefault(item =>
            !item.IsAvailable && normalizedMessage.Contains(Normalize(item.Name), StringComparison.OrdinalIgnoreCase));

        if (unavailableMatch is not null)
        {
            return new ChatAssistantReply(
                $"{unavailableMatch.Name} hiện đang hết hàng nên mình không thể gợi ý thêm món này vào giỏ.",
                [],
                ["MENU_ITEM_UNAVAILABLE"]);
        }

        var menuGrounding = ChatMenuGrounding.SelectWithConstraints(
            userMessage,
            menuItems
                .Where(item => item.IsAvailable)
                .Select(item => new ChatMenuItemContext(
                    item.Id,
                    item.Name,
                    item.Description,
                    item.Price,
                    item.CategoryId,
                    categoryNames[item.CategoryId],
                    item.Tags.ToList(),
                    item.IsAvailable)));
        var availableMenuItems = menuGrounding.Candidates;
        if (menuGrounding.HasExplicitConstraint)
        {
            return BuildGroundedCatalog(menuGrounding);
        }

        var priorHistory = history.Take(Math.Max(0, history.Count - 1)).ToList();
        var sessionMemory = BuildSessionMemory(priorHistory);
        var providerResult = await aiProvider.GenerateAsync(
            new ChatAiRequest(userMessage, priorHistory, availableMenuItems, tableCode, sessionMemory),
            cancellationToken);

        if (!providerResult.ProviderAvailable)
        {
            return new ChatAssistantReply(
                providerResult.Content,
                [],
                ["AI_PROVIDER_UNAVAILABLE"]);
        }

        // Use AI-provided suggestions if available, fallback to string-matching
        IReadOnlyList<SuggestedCartActionResponse> suggestedActions;
        if (providerResult.SuggestedCartActions is { Count: > 0 } aiActions)
        {
            suggestedActions = aiActions;
        }
        else
        {
            var fallbackAction = BuildSuggestedAction(normalizedMessage, availableMenuItems);
            suggestedActions = fallbackAction is null ? [] : [fallbackAction];
        }

        var guardrailFlags = new List<string>(providerResult.GuardrailFlags ?? []);
        if (suggestedActions.Count > 0 && !guardrailFlags.Contains("CUSTOMER_CONFIRMATION_REQUIRED"))
        {
            guardrailFlags.Add("CUSTOMER_CONFIRMATION_REQUIRED");
        }

        return new ChatAssistantReply(
            providerResult.Content,
            suggestedActions,
            guardrailFlags);
    }

    private static ChatAssistantReply BuildGroundedCatalog(ChatMenuGroundingResult grounding)
    {
        var scope = grounding.MatchedCategoryNames.Count > 0
            ? $"nhóm {string.Join(", ", grounding.MatchedCategoryNames)}"
            : $"tag {string.Join(", ", grounding.MatchedTags)}";
        if (grounding.Candidates.Count == 0)
        {
            return new ChatAssistantReply(
                $"Hiện chưa có món còn bán phù hợp với {scope} trong thực đơn.",
                [],
                []);
        }

        var culture = CultureInfo.GetCultureInfo("vi-VN");
        var catalog = string.Join(
            Environment.NewLine,
            grounding.Candidates.Select((item, index) =>
                $"{index + 1}. {item.Name} ({item.Id}) - {item.Price.ToString("#,0", culture)}đ: {item.Description}"));

        return new ChatAssistantReply(
            $"Đây là các món thuộc {scope} hiện còn bán:{Environment.NewLine}{Environment.NewLine}{catalog}{Environment.NewLine}{Environment.NewLine}Bạn muốn xem chi tiết hay thêm món nào vào giỏ?",
            [],
            []);
    }

    private static SuggestedCartActionResponse? BuildSuggestedAction(
        string normalizedMessage,
        IReadOnlyList<ChatMenuItemContext> availableMenuItems)
    {
        if (availableMenuItems.Count == 0)
        {
            return null;
        }

        var item = availableMenuItems.FirstOrDefault(menuItem =>
            normalizedMessage.Contains(Normalize(menuItem.Name), StringComparison.OrdinalIgnoreCase)
            || menuItem.Tags.Any(tag => normalizedMessage.Contains(Normalize(tag), StringComparison.OrdinalIgnoreCase)));

        item ??= ShouldSuggestDefaultItem(normalizedMessage)
            ? availableMenuItems.FirstOrDefault(menuItem =>
                menuItem.Tags.Any(tag => Normalize(tag).Equals("pho bien", StringComparison.OrdinalIgnoreCase)))
                ?? availableMenuItems.FirstOrDefault()
            : null;

        if (item is null)
        {
            return null;
        }

        return new SuggestedCartActionResponse(
            item.Id,
            item.Name,
            item.Price,
            Quantity: 1,
            Reason: "Mon con ban trong menu hien tai va can khach xac nhan truoc khi them vao gio.",
            RequiresCustomerConfirmation: true);
    }

    private static bool ShouldSuggestDefaultItem(string normalizedMessage)
    {
        var suggestionTerms = new[]
        {
            "goi y",
            "tu van",
            "mon",
            "an gi",
            "2 nguoi",
            "mot nguoi",
            "khai vi",
            "mon chinh",
            "do uong",
            "trang mieng"
        };

        return suggestionTerms.Any(term => normalizedMessage.Contains(term, StringComparison.OrdinalIgnoreCase));
    }

    private static bool IsOutOfScope(string normalizedMessage)
    {
        var outOfScopeTerms = new[]
        {
            "python",
            "code",
            "lap trinh",
            "javascript",
            "hack",
            "sql injection"
        };

        return outOfScopeTerms.Any(term => normalizedMessage.Contains(term, StringComparison.OrdinalIgnoreCase));
    }

    private static string BuildSessionMemory(IReadOnlyList<ChatMessageSnapshot> history)
    {
        var olderTurnCount = Math.Max(0, history.Count - 6);
        if (olderTurnCount == 0)
        {
            return string.Empty;
        }

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var remembered = new List<string>();
        foreach (var message in history.Take(olderTurnCount).Reverse())
        {
            var content = message.Content.Trim();
            if (!message.Role.Equals("user", StringComparison.OrdinalIgnoreCase) ||
                string.IsNullOrWhiteSpace(content) ||
                !seen.Add(content))
            {
                continue;
            }

            remembered.Add(content);
            if (remembered.Count == 8)
            {
                break;
            }
        }

        remembered.Reverse();
        var memory = string.Join("\n", remembered.Select(item => $"- {item}"));
        return memory.Length <= 1200 ? memory : memory[..1200];
    }

    private static string Normalize(string value)
    {
        return value.Trim().ToLowerInvariant();
    }
}
