namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record CreateChatSessionRequest(
    string? TableSessionId = null,
    string? TableCode = null);

public sealed record CreateChatSessionResponse(
    string ChatSessionId,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    string AccessToken,
    bool Reused,
    IReadOnlyList<ChatMessageResponse> Messages,
    IReadOnlyList<ChatRecommendationResponse> Recommendations);

public sealed record SendChatMessageRequest(
    string? Content,
    string? TableCode = null);

public sealed record ChatMessageResponse(
    string Id,
    string Role,
    string Content,
    DateTimeOffset CreatedAt,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions);

public sealed record SuggestedCartActionResponse(
    string MenuItemId,
    string Name,
    decimal Price,
    int Quantity,
    string Reason,
    bool RequiresCustomerConfirmation,
    string? Status = null,
    IReadOnlyList<string>? EvidenceIds = null);

public sealed record ChatRecommendationResponse(
    string MenuItemId,
    string Status,
    string? TurnId,
    DateTimeOffset UpdatedAt);

public sealed record UpdateRecommendationRequest(
    string MenuItemId,
    string Status,
    string? TurnId = null);

public sealed record ChatFeedbackRequest(
    string MessageId,
    string Rating,
    string? Reason = null);

public sealed record SendChatMessageResponse(
    ChatMessageResponse UserMessage,
    ChatMessageResponse Message,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions,
    IReadOnlyList<string> GuardrailFlags,
    bool? SuggestStaffHandoff = null,
    FollowUpHint? FollowUp = null);

public sealed record FollowUpHint(
    bool CanShowMore,
    int RemainingCount);

public sealed record ChatHistoryResponse(
    string ChatSessionId,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<ChatMessageResponse> Messages,
    IReadOnlyList<ChatRecommendationResponse> Recommendations);

public sealed record AssistanceRequestBody(
    string? Note = null);
