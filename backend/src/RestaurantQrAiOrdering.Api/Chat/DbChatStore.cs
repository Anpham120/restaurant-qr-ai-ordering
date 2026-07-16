using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Chat;

public sealed class DbChatStore : IChatStore
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private readonly RestaurantDbContext db;

    public DbChatStore(RestaurantDbContext db)
    {
        this.db = db;
    }

    public async Task<(ChatSessionSnapshot Session, bool Reused)> CreateOrGetSessionAsync(
        string? tableCode,
        string? tableSessionId,
        CancellationToken cancellationToken)
    {
        var normalizedTableSessionId = NormalizeOptional(tableSessionId);
        if (normalizedTableSessionId is not null)
        {
            var existing = await db.ChatSessions
                .AsNoTracking()
                .Where(session => session.TableSessionId == normalizedTableSessionId && !session.IsClosed)
                .OrderByDescending(session => session.UpdatedAt)
                .FirstOrDefaultAsync(cancellationToken);
            if (existing is not null)
            {
                return (ToSnapshot(existing), true);
            }
        }

        var now = DateTimeOffset.UtcNow;
        var session = new ChatSession
        {
            Id = $"chat_{Guid.NewGuid():N}",
            TableCode = NormalizeOptional(tableCode),
            TableSessionId = normalizedTableSessionId,
            CreatedAt = now,
            UpdatedAt = now,
            IsClosed = false
        };
        db.ChatSessions.Add(session);
        await db.SaveChangesAsync(cancellationToken);
        return (ToSnapshot(session), false);
    }

    public async Task<ChatSessionSnapshot?> GetSessionAsync(
        string chatSessionId,
        CancellationToken cancellationToken)
    {
        var session = await db.ChatSessions
            .AsNoTracking()
            .FirstOrDefaultAsync(value => value.Id == chatSessionId && !value.IsClosed, cancellationToken);
        return session is null ? null : ToSnapshot(session);
    }

    public async Task<IReadOnlyList<ChatMessageSnapshot>> GetMessagesAsync(
        string chatSessionId,
        int? limit,
        CancellationToken cancellationToken)
    {
        var query = db.ChatMessages
            .AsNoTracking()
            .Where(message => message.ChatSessionId == chatSessionId)
            .OrderByDescending(message => message.CreatedAt)
            .AsQueryable();
        if (limit is > 0)
        {
            query = query.Take(limit.Value);
        }
        var messages = await query.ToListAsync(cancellationToken);
        return messages
            .OrderBy(message => message.CreatedAt)
            .Select(ToMessageSnapshot)
            .ToList();
    }

    public async Task<ChatMessageSnapshot?> AddMessageAsync(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions,
        CancellationToken cancellationToken)
    {
        var session = await db.ChatSessions
            .FirstOrDefaultAsync(value => value.Id == chatSessionId && !value.IsClosed, cancellationToken);
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
        db.ChatMessages.Add(message);
        session.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
        return ToMessageSnapshot(message);
    }

    public async Task<int> DeleteSessionsByTableSessionAsync(
        string tableSessionId,
        CancellationToken cancellationToken)
    {
        var normalized = NormalizeOptional(tableSessionId);
        if (normalized is null)
        {
            return 0;
        }
        var sessions = await db.ChatSessions
            .Where(session => session.TableSessionId == normalized)
            .ToListAsync(cancellationToken);
        if (sessions.Count == 0)
        {
            return 0;
        }
        db.ChatSessions.RemoveRange(sessions);
        await db.SaveChangesAsync(cancellationToken);
        return sessions.Count;
    }

    private static ChatSessionSnapshot ToSnapshot(ChatSession session) => new(
        session.Id,
        session.TableCode,
        session.CreatedAt,
        session.UpdatedAt,
        session.TableSessionId,
        session.IsClosed);

    private static ChatMessageSnapshot ToMessageSnapshot(ChatMessage message) => new(
        message.Id,
        message.ChatSessionId,
        message.Role,
        message.Content,
        message.CreatedAt,
        DeserializeActions(message.SuggestedCartActionsJson));

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

    private static string? NormalizeOptional(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Trim();
}
