namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record CreateChatSessionRequest(
    string? TableSessionId = null,
    string? TableCode = null);

public sealed record CreateChatSessionResponse(
    string ChatSessionId,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    bool Reused,
    IReadOnlyList<ChatMessageResponse> Messages);

public sealed record SendChatMessageRequest(
    string? Content);

public sealed record SuggestedCartActionResponse(
    string MenuItemId,
    string Name,
    decimal Price,
    int Quantity,
    string Reason,
    bool RequiresCustomerConfirmation);

public sealed record ChatMessageResponse(
    string Id,
    string Role,
    string Content,
    DateTimeOffset CreatedAt,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions);

public sealed record RetrievedSourceResponse(
    string Source,
    string Title,
    double Score);

public sealed record ChatDiagnosticsResponse(
    bool AiServiceAvailable,
    bool LlmProviderAvailable,
    string Model,
    string RetrievalMethod,
    string? FastPath,
    IReadOnlyDictionary<string, double> LatencyMs,
    IReadOnlyList<RetrievedSourceResponse> RetrievedSources);

public sealed record SendChatMessageResponse(
    ChatMessageResponse Message,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions,
    IReadOnlyList<string> GuardrailFlags,
    ChatDiagnosticsResponse Diagnostics);

public sealed record ChatHistoryResponse(
    string ChatSessionId,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<ChatMessageResponse> Messages);
