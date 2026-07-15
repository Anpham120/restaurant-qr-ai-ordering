namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record ChatSessionSnapshot(
    string Id,
    string? TableCode,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<ChatMessageSnapshot> Messages,
    string? TableSessionId = null,
    string? RollingSummary = null,
    IReadOnlyList<ChatRecommendationSnapshot>? Recommendations = null,
    IReadOnlyList<ChatSessionFactSnapshot>? Facts = null);

public sealed record ChatMessageSnapshot(
    string Id,
    string ChatSessionId,
    string Role,
    string Content,
    DateTimeOffset CreatedAt,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions);

public sealed record ChatRecommendationSnapshot(
    string Id,
    string MenuItemId,
    string Status,
    string? TurnId,
    DateTimeOffset UpdatedAt);

public sealed record ChatSessionFactSnapshot(
    string Kind,
    string Value,
    double Confidence,
    string? SourceTurnId);

public sealed record ChatSessionCreateResult(
    ChatSessionSnapshot Session,
    bool Reused);

public interface IChatStore
{
    ChatSessionCreateResult CreateOrGetSession(string? tableCode = null, string? tableSessionId = null);

    ChatSessionSnapshot? GetSession(string chatSessionId);

    IReadOnlyList<ChatMessageSnapshot>? GetMessages(string chatSessionId);

    ChatMessageSnapshot? AddMessage(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions = null);

    /// <summary>
    /// Upsert recommendation ledger entries. Status: suggested|rejected|accepted|added_to_cart.
    /// </summary>
    IReadOnlyList<ChatRecommendationSnapshot> UpsertRecommendations(
        string chatSessionId,
        IEnumerable<(string MenuItemId, string Status, string? TurnId)> entries);

    IReadOnlyList<ChatRecommendationSnapshot> GetRecommendations(string chatSessionId);

    IReadOnlySet<string> GetExcludedMenuItemIds(string chatSessionId);

    void UpsertFacts(
        string chatSessionId,
        IEnumerable<(string Kind, string Value, double Confidence, string? SourceTurnId)> facts);

    IReadOnlyList<ChatSessionFactSnapshot> GetFacts(string chatSessionId);

    void UpdateRollingSummary(string chatSessionId, string summary);

    void AddFeedback(string chatSessionId, string messageId, string rating, string? reason);

    /// <summary>
    /// Xóa toàn bộ chat sessions + messages + ledger + facts gắn với một phiên bàn.
    /// </summary>
    int DeleteSessionsByTableSession(string tableSessionId);
}
