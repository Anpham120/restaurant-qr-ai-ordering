namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record CreateChatSessionRequest(
    string? TableSessionId = null,
    string? TableCode = null);

public sealed record CreateChatSessionResponse(
    string ChatSessionId,
    DateTimeOffset CreatedAt,
    string AccessToken);

public sealed record SendChatMessageRequest(
    string? Content,
    string? TableCode = null);

public sealed record ChatMessageResponse(
    string Id,
    string Role,
    string Content,
    DateTimeOffset CreatedAt);

public sealed record SuggestedCartActionResponse(
    string MenuItemId,
    string Name,
    decimal Price,
    int Quantity,
    string Reason,
    bool RequiresCustomerConfirmation);

public sealed record SendChatMessageResponse(
    ChatMessageResponse Message,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions,
    IReadOnlyList<string> GuardrailFlags);

public sealed record ChatHistoryResponse(
    string ChatSessionId,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<ChatMessageResponse> Messages);
