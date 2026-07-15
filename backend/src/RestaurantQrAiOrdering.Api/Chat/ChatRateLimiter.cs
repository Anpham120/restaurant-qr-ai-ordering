using System.Collections.Concurrent;

namespace RestaurantQrAiOrdering.Api.Chat;

public interface IChatRateLimiter
{
    bool TryAcquire(string chatSessionId);
}

/// <summary>
/// In-memory rate limiter: 10 messages/minute and 100 messages/session.
/// </summary>
public sealed class ChatRateLimiter : IChatRateLimiter
{
    private const int PerMinuteLimit = 10;
    private const int PerSessionLimit = 100;

    private readonly ConcurrentDictionary<string, SessionBucket> buckets = new(StringComparer.OrdinalIgnoreCase);

    public bool TryAcquire(string chatSessionId)
    {
        var bucket = buckets.GetOrAdd(chatSessionId, _ => new SessionBucket());
        lock (bucket.Gate)
        {
            var now = DateTimeOffset.UtcNow;
            bucket.Timestamps.RemoveAll(t => now - t > TimeSpan.FromMinutes(1));
            if (bucket.Timestamps.Count >= PerMinuteLimit || bucket.Total >= PerSessionLimit)
            {
                return false;
            }

            bucket.Timestamps.Add(now);
            bucket.Total += 1;
            return true;
        }
    }

    private sealed class SessionBucket
    {
        public object Gate { get; } = new();
        public List<DateTimeOffset> Timestamps { get; } = [];
        public int Total { get; set; }
    }
}
