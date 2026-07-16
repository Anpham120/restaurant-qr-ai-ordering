namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record ChatSessionSnapshot(
    string Id,
    string? TableCode,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    string? TableSessionId,
    bool IsClosed);

public sealed record ChatMessageSnapshot(
    string Id,
    string ChatSessionId,
    string Role,
    string Content,
    DateTimeOffset CreatedAt,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions);

public interface IChatStore
{
    Task<(ChatSessionSnapshot Session, bool Reused)> CreateOrGetSessionAsync(
        string? tableCode,
        string? tableSessionId,
        CancellationToken cancellationToken);

    Task<ChatSessionSnapshot?> GetSessionAsync(string chatSessionId, CancellationToken cancellationToken);

    Task<IReadOnlyList<ChatMessageSnapshot>> GetMessagesAsync(
        string chatSessionId,
        int? limit,
        CancellationToken cancellationToken);

    Task<ChatMessageSnapshot?> AddMessageAsync(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions,
        CancellationToken cancellationToken);

    Task<int> DeleteSessionsByTableSessionAsync(string tableSessionId, CancellationToken cancellationToken);
}
