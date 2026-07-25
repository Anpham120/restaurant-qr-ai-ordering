using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Chat;

public sealed class DbChatStore : IChatStore
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly HashSet<string> ExclusionStatuses = new(StringComparer.OrdinalIgnoreCase)
    {
        "suggested", "rejected", "accepted", "added_to_cart"
    };

    private readonly RestaurantDbContext dbContext;
    private static readonly Dictionary<string, object> SessionLocks = new(StringComparer.OrdinalIgnoreCase);
    private static readonly object SessionLocksGate = new();

    public DbChatStore(RestaurantDbContext dbContext)
    {
        this.dbContext = dbContext;
    }

    public ChatSessionCreateResult CreateOrGetSession(string? tableCode = null, string? tableSessionId = null)
    {
        var normalizedTableSessionId = NormalizeOptional(tableSessionId);
        if (normalizedTableSessionId is not null)
        {
            var existing = dbContext.ChatSessions
                .Include(session => session.Messages)
                .Include(session => session.Recommendations)
                .Include(session => session.Facts)
                .Where(session => session.TableSessionId == normalizedTableSessionId)
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
            Id = $"chat_{Guid.NewGuid():N}",
            TableCode = NormalizeOptional(tableCode),
            TableSessionId = normalizedTableSessionId,
            CreatedAt = now,
            UpdatedAt = now
        };

        dbContext.ChatSessions.Add(session);
        dbContext.SaveChanges();

        return new ChatSessionCreateResult(ToSnapshot(session), Reused: false);
    }

    public int DeleteSessionsByTableSession(string tableSessionId)
    {
        var normalized = NormalizeOptional(tableSessionId);
        if (normalized is null)
        {
            return 0;
        }

        // Recommendations, facts, feedback, messages cascade via FK.
        var sessions = dbContext.ChatSessions
            .Include(session => session.Messages)
            .Include(session => session.Recommendations)
            .Include(session => session.Facts)
            .Include(session => session.Feedback)
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
                .Select(m => ToMessageSnapshot(m, session))
                .ToList();
    }

    public ChatMessageSnapshot? AddMessage(
        string chatSessionId,
        string role,
        string content,
        IReadOnlyList<SuggestedCartActionResponse>? suggestedCartActions = null)
    {
        lock (GetSessionLock(chatSessionId))
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

            if (role.Equals("assistant", StringComparison.OrdinalIgnoreCase)
                && suggestedCartActions is { Count: > 0 })
            {
                foreach (var action in suggestedCartActions)
                {
                    UpsertRecommendationInternal(session, action.MenuItemId, "suggested", message.Id, now);
                }
            }

            dbContext.SaveChanges();
            return ToMessageSnapshot(message, session);
        }
    }

    public IReadOnlyList<ChatRecommendationSnapshot> UpsertRecommendations(
        string chatSessionId,
        IEnumerable<(string MenuItemId, string Status, string? TurnId)> entries)
    {
        lock (GetSessionLock(chatSessionId))
        {
            var session = FindSession(chatSessionId);
            if (session is null)
            {
                return [];
            }

            var now = DateTimeOffset.UtcNow;
            var results = new List<ChatRecommendationSnapshot>();
            foreach (var (menuItemId, status, turnId) in entries)
            {
                var entry = UpsertRecommendationInternal(session, menuItemId, status, turnId, now);
                if (entry is not null)
                {
                    results.Add(ToRecommendationSnapshot(entry));
                }
            }

            session.UpdatedAt = now;
            dbContext.SaveChanges();
            return results;
        }
    }

    public IReadOnlyList<ChatRecommendationSnapshot> GetRecommendations(string chatSessionId)
    {
        var session = FindSession(chatSessionId);
        if (session is null)
        {
            return [];
        }

        return session.Recommendations
            .OrderBy(r => r.CreatedAt)
            .Select(ToRecommendationSnapshot)
            .ToList();
    }

    public IReadOnlySet<string> GetExcludedMenuItemIds(string chatSessionId)
    {
        var session = FindSession(chatSessionId);
        if (session is null)
        {
            return new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        }

        return session.Recommendations
            .Where(r => ExclusionStatuses.Contains(r.Status))
            .Select(r => r.MenuItemId)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);
    }

    public void UpsertFacts(
        string chatSessionId,
        IEnumerable<(string Kind, string Value, double Confidence, string? SourceTurnId)> facts)
    {
        lock (GetSessionLock(chatSessionId))
        {
            var session = FindSession(chatSessionId);
            if (session is null)
            {
                return;
            }

            var now = DateTimeOffset.UtcNow;
            UpsertFactsInternal(session, facts, now);

            session.UpdatedAt = now;
            dbContext.SaveChanges();
        }
    }

    public IReadOnlyList<ChatSessionFactSnapshot> GetFacts(string chatSessionId)
    {
        var session = FindSession(chatSessionId);
        if (session is null)
        {
            return [];
        }

        return session.Facts
            .Select(f => new ChatSessionFactSnapshot(f.Kind, f.Value, f.Confidence, f.SourceTurnId))
            .ToList();
    }

    public ChatSessionStateSnapshot? GetSessionState(string chatSessionId)
    {
        var session = FindSession(chatSessionId);
        return session is null ? null : ToStateSnapshot(session);
    }

    public void ApplyAiSessionUpdates(
        string chatSessionId,
        ChatSessionUpdates updates,
        string? assistantTurnId,
        string? userTurnId)
    {
        lock (GetSessionLock(chatSessionId))
        {
            var session = FindSession(chatSessionId);
            if (session is null)
            {
                return;
            }

            var now = DateTimeOffset.UtcNow;
            UpsertFactsInternal(
                session,
                updates.Facts.Select(fact =>
                    (fact.Kind, fact.Value, fact.Confidence, assistantTurnId)),
                now);

            session.ConstraintsJson = JsonSerializer.Serialize(updates.Constraints, JsonOptions);
            session.ReferencedMenuItemIdsJson = JsonSerializer.Serialize(
                StableDistinct(
                    DeserializeStringList(session.ReferencedMenuItemIdsJson)
                        .Concat(updates.ReferencedMenuItemIds)),
                JsonOptions);
            if (!string.IsNullOrWhiteSpace(updates.MemoryVersion))
            {
                session.MemoryVersion = updates.MemoryVersion.Trim()[..Math.Min(50, updates.MemoryVersion.Trim().Length)];
            }

            if (updates.RollingSummary is not null)
            {
                session.RollingSummary = updates.RollingSummary.Length <= 8000
                    ? updates.RollingSummary
                    : updates.RollingSummary[..8000];
            }

            UpsertRecommendationEntries(session, updates.SuggestedMenuItemIds, "suggested", assistantTurnId, now);
            UpsertRecommendationEntries(session, updates.RejectedMenuItemIds, "rejected", userTurnId, now);

            // accepted and added_to_cart are backend-owned transitions. AI output is
            // context only and must never confirm a customer choice or mutate cart state.
            // Trusted recommendation/cart endpoints persist those statuses separately.

            session.UpdatedAt = now;
            dbContext.SaveChanges();
        }
    }

    public void UpdateRollingSummary(string chatSessionId, string summary)
    {
        lock (GetSessionLock(chatSessionId))
        {
            var session = FindSession(chatSessionId);
            if (session is null)
            {
                return;
            }

            session.RollingSummary = summary.Length <= 8000 ? summary : summary[..8000];
            session.UpdatedAt = DateTimeOffset.UtcNow;
            dbContext.SaveChanges();
        }
    }

    public void AddFeedback(string chatSessionId, string messageId, string rating, string? reason)
    {
        var session = FindSession(chatSessionId);
        if (session is null)
        {
            return;
        }

        var normalizedRating = rating.Trim().ToLowerInvariant();
        if (normalizedRating is not ("up" or "down"))
        {
            return;
        }

        var feedback = new ChatFeedback
        {
            Id = $"fb_{Guid.NewGuid():N}",
            ChatSessionId = session.Id,
            MessageId = messageId.Trim(),
            Rating = normalizedRating,
            Reason = string.IsNullOrWhiteSpace(reason) ? null : reason.Trim(),
            CreatedAt = DateTimeOffset.UtcNow
        };
        dbContext.ChatFeedbacks.Add(feedback);
        dbContext.SaveChanges();
    }

    private ChatRecommendation? UpsertRecommendationInternal(
        ChatSession session,
        string menuItemId,
        string status,
        string? turnId,
        DateTimeOffset now)
    {
        var normalizedStatus = status.Trim().ToLowerInvariant();
        if (!ExclusionStatuses.Contains(normalizedStatus) || string.IsNullOrWhiteSpace(menuItemId))
        {
            return null;
        }

        var existing = session.Recommendations.FirstOrDefault(r =>
            r.MenuItemId.Equals(menuItemId, StringComparison.OrdinalIgnoreCase)
            && r.Status.Equals(normalizedStatus, StringComparison.OrdinalIgnoreCase));

        if (existing is not null)
        {
            existing.TurnId = turnId ?? existing.TurnId;
            existing.UpdatedAt = now;
            return existing;
        }

        // Escalate status: if already added_to_cart, don't downgrade to suggested.
        var sameItem = session.Recommendations
            .Where(r => r.MenuItemId.Equals(menuItemId, StringComparison.OrdinalIgnoreCase))
            .ToList();
        if (normalizedStatus == "suggested"
            && sameItem.Any(r => r.Status is "rejected" or "accepted" or "added_to_cart"))
        {
            return sameItem.OrderByDescending(r => r.UpdatedAt).First();
        }

        var entry = new ChatRecommendation
        {
            Id = $"rec_{Guid.NewGuid():N}",
            ChatSessionId = session.Id,
            MenuItemId = menuItemId.Trim(),
            Status = normalizedStatus,
            TurnId = turnId,
            CreatedAt = now,
            UpdatedAt = now
        };
        session.Recommendations.Add(entry);
        dbContext.ChatRecommendations.Add(entry);
        return entry;
    }

    private void UpsertFactsInternal(
        ChatSession session,
        IEnumerable<(string Kind, string Value, double Confidence, string? SourceTurnId)> facts,
        DateTimeOffset now)
    {
        foreach (var (kind, value, confidence, sourceTurnId) in facts)
        {
            var normalizedKind = kind.Trim().ToLowerInvariant();
            var normalizedValue = value.Trim();
            if (string.IsNullOrWhiteSpace(normalizedKind) || string.IsNullOrWhiteSpace(normalizedValue))
            {
                continue;
            }

            var existing = session.Facts.FirstOrDefault(f =>
                f.Kind.Equals(normalizedKind, StringComparison.OrdinalIgnoreCase)
                && f.Value.Equals(normalizedValue, StringComparison.OrdinalIgnoreCase));

            if (existing is null)
            {
                existing = new ChatSessionFact
                {
                    Id = $"fact_{Guid.NewGuid():N}",
                    ChatSessionId = session.Id,
                    Kind = normalizedKind,
                    Value = normalizedValue,
                    Confidence = confidence,
                    SourceTurnId = sourceTurnId,
                    CreatedAt = now,
                    UpdatedAt = now
                };
                session.Facts.Add(existing);
                dbContext.ChatSessionFacts.Add(existing);
            }
            else
            {
                existing.Confidence = Math.Max(existing.Confidence, confidence);
                existing.SourceTurnId = sourceTurnId ?? existing.SourceTurnId;
                existing.UpdatedAt = now;
            }
        }
    }

    private void UpsertRecommendationEntries(
        ChatSession session,
        IEnumerable<string> menuItemIds,
        string status,
        string? turnId,
        DateTimeOffset now)
    {
        foreach (var menuItemId in StableDistinct(menuItemIds))
        {
            UpsertRecommendationInternal(session, menuItemId, status, turnId, now);
        }
    }

    private ChatSession? FindSession(string chatSessionId)
    {
        var normalizedChatSessionId = chatSessionId.Trim();
        var session = dbContext.ChatSessions
            .Include(session => session.Messages)
            .Include(session => session.Recommendations)
            .Include(session => session.Facts)
            .FirstOrDefault(session => session.Id == normalizedChatSessionId);

        if (session is null || string.IsNullOrWhiteSpace(session.TableSessionId))
        {
            return session;
        }

        var tableSession = dbContext.TableSessions
            .FirstOrDefault(candidate => candidate.Id == session.TableSessionId);
        var now = DateTimeOffset.UtcNow;
        if (tableSession?.IsActiveAt(now) == true)
        {
            return session;
        }

        tableSession?.ExpireIfPast(now);
        DeleteSessionsByTableSession(session.TableSessionId);
        return null;
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
                .Select(m => ToMessageSnapshot(m, session))
                .ToList(),
            session.TableSessionId,
            session.RollingSummary,
            session.Recommendations.Select(ToRecommendationSnapshot).ToList(),
            session.Facts.Select(f => new ChatSessionFactSnapshot(f.Kind, f.Value, f.Confidence, f.SourceTurnId)).ToList());
    }

    private static ChatSessionStateSnapshot ToStateSnapshot(ChatSession session)
    {
        IReadOnlyList<string> RecommendationIds(string status) => session.Recommendations
            .Where(entry => entry.Status.Equals(status, StringComparison.OrdinalIgnoreCase))
            .OrderBy(entry => entry.CreatedAt)
            .Select(entry => entry.MenuItemId)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        return new ChatSessionStateSnapshot(
            session.Facts
                .OrderBy(fact => fact.CreatedAt)
                .Select(fact => new ChatSessionFactSnapshot(
                    fact.Kind,
                    fact.Value,
                    fact.Confidence,
                    fact.SourceTurnId))
                .ToList(),
            DeserializeConstraints(session.ConstraintsJson),
            DeserializeStringList(session.ReferencedMenuItemIdsJson),
            RecommendationIds("suggested"),
            RecommendationIds("rejected"),
            RecommendationIds("accepted"),
            RecommendationIds("added_to_cart"),
            session.RollingSummary,
            string.IsNullOrWhiteSpace(session.MemoryVersion) ? "v1" : session.MemoryVersion);
    }

    private static ChatMessageSnapshot ToMessageSnapshot(ChatMessage message, ChatSession session)
    {
        var actions = DeserializeActions(message.SuggestedCartActionsJson);
        var statusByItem = session.Recommendations
            .GroupBy(r => r.MenuItemId, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(
                g => g.Key,
                g => PickDisplayStatus(g.Select(x => x.Status)),
                StringComparer.OrdinalIgnoreCase);

        var enriched = actions.Select(action =>
        {
            statusByItem.TryGetValue(action.MenuItemId, out var status);
            return action with { Status = MapLedgerToCardStatus(status) };
        }).ToList();

        return new ChatMessageSnapshot(
            message.Id,
            message.ChatSessionId,
            message.Role,
            message.Content,
            message.CreatedAt,
            enriched);
    }

    private static string PickDisplayStatus(IEnumerable<string> statuses)
    {
        var set = statuses.ToHashSet(StringComparer.OrdinalIgnoreCase);
        if (set.Contains("added_to_cart") || set.Contains("accepted")) return "accepted";
        if (set.Contains("rejected")) return "rejected";
        return "suggested";
    }

    private static string MapLedgerToCardStatus(string? ledgerStatus) => ledgerStatus switch
    {
        "accepted" or "added_to_cart" => "confirmed",
        "rejected" => "dismissed",
        _ => "pending"
    };

    private static ChatRecommendationSnapshot ToRecommendationSnapshot(ChatRecommendation r) =>
        new(r.Id, r.MenuItemId, r.Status, r.TurnId, r.UpdatedAt);

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

    private static IReadOnlyDictionary<string, JsonElement> DeserializeConstraints(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        }

        try
        {
            return JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json, JsonOptions)
                   ?? new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        }
        catch (JsonException)
        {
            return new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        }
    }

    private static IReadOnlyList<string> DeserializeStringList(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return [];
        }

        try
        {
            return StableDistinct(JsonSerializer.Deserialize<IReadOnlyList<string>>(json, JsonOptions) ?? []);
        }
        catch (JsonException)
        {
            return [];
        }
    }

    private static IReadOnlyList<string> StableDistinct(IEnumerable<string?> values)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var result = new List<string>();
        foreach (var value in values)
        {
            var normalized = value?.Trim();
            if (!string.IsNullOrEmpty(normalized) && seen.Add(normalized))
            {
                result.Add(normalized);
            }
        }

        return result;
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    private static object GetSessionLock(string chatSessionId)
    {
        lock (SessionLocksGate)
        {
            if (!SessionLocks.TryGetValue(chatSessionId, out var gate))
            {
                gate = new object();
                SessionLocks[chatSessionId] = gate;
            }

            return gate;
        }
    }
}
