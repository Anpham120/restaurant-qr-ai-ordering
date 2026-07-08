using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Chat;

public sealed class DbChatStore : IChatStore
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly RestaurantDbContext dbContext;

    public DbChatStore(RestaurantDbContext dbContext)
    {
        this.dbContext = dbContext;
    }

    public ChatSessionSnapshot CreateSession(string? tableCode = null, string? tableSessionId = null)
    {
        var now = DateTimeOffset.UtcNow;
        var session = new ChatSession
        {
            Id = $"chat_{Guid.NewGuid():N}",
            TableCode = NormalizeOptional(tableCode),
            TableSessionId = NormalizeOptional(tableSessionId),
            CreatedAt = now,
            UpdatedAt = now
        };

        dbContext.ChatSessions.Add(session);
        dbContext.SaveChanges();

        return ToSnapshot(session);
    }

    public int DeleteSessionsByTableSession(string tableSessionId)
    {
        var normalized = NormalizeOptional(tableSessionId);
        if (normalized is null)
        {
            return 0;
        }

        // Messages xóa theo cascade (FK ChatMessage -> ChatSession).
        var sessions = dbContext.ChatSessions
            .Include(session => session.Messages)
            .Where(session => session.TableSessionId == normalized)
            .ToList();

        if (sessions.Count == 0)
        {
            return 0;
        }

        dbContext.ChatSessions.RemoveRange(sessions);
        dbContext.SaveChanges();
        return sessions.Count;
    }

    public ChatSessionSnapshot? GetSession(string chatSessionId)
    {
        var session = FindSession(chatSessionId);
        return session is null ? null : ToSnapshot(session);
    }

    public IReadOnlyList<ChatMessageSnapshot>? GetMessages(string chatSessionId)
    {
        var session = FindSession(chatSessionId);
        return session is null
            ? null
            : session.Messages
                .OrderBy(message => message.CreatedAt)
                .Select(ToMessageSnapshot)
                .ToList();
    }

    public ChatMessageSnapshot? AddMessage(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions = null)
    {
        var session = FindSession(chatSessionId);
        if (session is null)
        {
            return null;
        }

        var now = DateTimeOffset.UtcNow;
        var message = new ChatMessage
        {
            Id = $"msg_{Guid.NewGuid():N}",
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
        dbContext.SaveChanges();

        return ToMessageSnapshot(message);
    }

    private ChatSession? FindSession(string chatSessionId)
    {
        return dbContext.ChatSessions
            .Include(session => session.Messages)
            .FirstOrDefault(session =>
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
