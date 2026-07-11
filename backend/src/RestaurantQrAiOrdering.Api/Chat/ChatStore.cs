using System.Text.Json;
using RestaurantQrAiOrdering.Entities;

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
    /// Xóa toàn bộ chat sessions + messages gắn với một phiên bàn.
    /// Gọi khi phiên bàn đóng/hết hạn để dọn dữ liệu cho khách mới.
    /// Trả về số chat session đã xóa.
    /// </summary>
    int DeleteSessionsByTableSession(string tableSessionId);
}

public sealed class ChatStore : IChatStore
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly object syncRoot = new();
    private readonly List<ChatSession> sessions = [];
    private int nextSessionNumber = 1;
    private int nextMessageNumber = 1;

    public ChatSessionCreateResult CreateOrGetSession(string? tableCode = null, string? tableSessionId = null)
    {
        lock (syncRoot)
        {
            var normalizedTableSessionId = NormalizeOptional(tableSessionId);
            if (normalizedTableSessionId is not null)
            {
                var existing = sessions
                    .Where(session => string.Equals(
                        session.TableSessionId,
                        normalizedTableSessionId,
                        StringComparison.OrdinalIgnoreCase))
                    .OrderByDescending(session => session.UpdatedAt)
                    .FirstOrDefault();

                if (existing is not null)
                {
                    return new ChatSessionCreateResult(ToSnapshot(existing), Reused: true);
                }
            }

            var now = DateTimeOffset.UtcNow;
            var session = new ChatSession
            {
                Id = $"chat_{nextSessionNumber++:000}",
                TableCode = NormalizeOptional(tableCode),
                TableSessionId = normalizedTableSessionId,
                CreatedAt = now,
                UpdatedAt = now
            };

            sessions.Add(session);
            return new ChatSessionCreateResult(ToSnapshot(session), Reused: false);
        }
    }

    public int DeleteSessionsByTableSession(string tableSessionId)
    {
        lock (syncRoot)
        {
            return sessions.RemoveAll(session =>
                session.TableSessionId is not null &&
                session.TableSessionId.Equals(tableSessionId, StringComparison.OrdinalIgnoreCase));
        }
    }

    public ChatSessionSnapshot? GetSession(string chatSessionId)
    {
        lock (syncRoot)
        {
            var session = FindSession(chatSessionId);
            return session is null ? null : ToSnapshot(session);
        }
    }

    public IReadOnlyList<ChatMessageSnapshot>? GetMessages(string chatSessionId)
    {
        lock (syncRoot)
        {
            var session = FindSession(chatSessionId);
            return session is null
                ? null
                : session.Messages
                    .OrderBy(message => message.CreatedAt)
                    .Select(ToMessageSnapshot)
                    .ToList();
        }
    }

    public ChatMessageSnapshot? AddMessage(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions = null)
    {
        lock (syncRoot)
        {
            var session = FindSession(chatSessionId);
            if (session is null)
            {
                return null;
            }

            var now = DateTimeOffset.UtcNow;
            var message = new ChatMessage
            {
                Id = $"msg_{nextMessageNumber++:000}",
                ChatSessionId = session.Id,
                Role = role,
                Content = content,
                SuggestedCartActionsJson = suggestedCartActions is { Count: > 0 }
                    ? JsonSerializer.Serialize(suggestedCartActions, JsonOptions)
                    : null,
                CreatedAt = now
            };

            session.Messages.Add(message);
            session.UpdatedAt = now;

            return ToMessageSnapshot(message);
        }
    }

    private ChatSession? FindSession(string chatSessionId)
    {
        return sessions.FirstOrDefault(session =>
            session.Id.Equals(chatSessionId, StringComparison.OrdinalIgnoreCase));
    }

    private static ChatSessionSnapshot ToSnapshot(ChatSession session)
    {
        return new ChatSessionSnapshot(
            session.Id,
            session.TableCode,
            session.CreatedAt,
            session.UpdatedAt,
            session.Messages
                .OrderBy(message => message.CreatedAt)
                .Select(ToMessageSnapshot)
                .ToList(),
            session.TableSessionId);
    }

    private static ChatMessageSnapshot ToMessageSnapshot(ChatMessage message)
    {
        return new ChatMessageSnapshot(
            message.Id,
            message.ChatSessionId,
            message.Role,
            message.Content,
            message.CreatedAt,
            DeserializeActions(message.SuggestedCartActionsJson));
    }

    private static IReadOnlyList<SuggestedCartActionResponse> DeserializeActions(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return [];
        }

        try
        {
            return JsonSerializer.Deserialize<IReadOnlyList<SuggestedCartActionResponse>>(json, JsonOptions) ?? [];
        }
        catch (JsonException)
        {
            return [];
        }
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
