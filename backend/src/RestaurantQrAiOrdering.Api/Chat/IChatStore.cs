namespace RestaurantQrAiOrdering.Api.Chat;

public sealed record ChatSessionSnapshot(
    string Id,
    string? TableCode,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<ChatMessageSnapshot> Messages,
    string? TableSessionId = null);

public sealed record ChatMessageSnapshot(
    string Id,
    string ChatSessionId,
    string Role,
    string Content,
    DateTimeOffset CreatedAt,
    IReadOnlyList<SuggestedCartActionResponse> SuggestedCartActions);

public interface IChatStore
{
    ChatSessionSnapshot CreateSession(string? tableCode = null, string? tableSessionId = null);

    ChatSessionSnapshot? GetSession(string chatSessionId);

    IReadOnlyList<ChatMessageSnapshot>? GetMessages(string chatSessionId);

    ChatMessageSnapshot? AddMessage(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions = null);

    /// <summary>
    /// Xóa toàn bộ chat sessions + messages gắn với một phiên bàn.
    /// Gọi khi phiên bàn đóng/hết hạn để dọn dữ liệu cho khách mới.
    /// Trả về số chat session đã xóa.
    /// </summary>
    int DeleteSessionsByTableSession(string tableSessionId);
}
