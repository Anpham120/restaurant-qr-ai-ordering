#nullable enable

using System;

namespace RestaurantQrAiOrdering.Entities;

/// <summary>
/// Customer thumbs-up / thumbs-down on an assistant message.
/// </summary>
public class ChatFeedback
{
    public string Id { get; set; } = string.Empty;

    public string ChatSessionId { get; set; } = string.Empty;

    public ChatSession? ChatSession { get; set; }

    public string MessageId { get; set; } = string.Empty;

    public ChatMessage? Message { get; set; }

    /// <summary>up | down</summary>
    public string Rating { get; set; } = string.Empty;

    public string? Reason { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}
