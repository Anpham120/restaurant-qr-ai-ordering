#nullable enable

using System;

namespace RestaurantQrAiOrdering.Entities;

public class ChatMessage
{
    public string Id { get; set; } = string.Empty;

    public string ChatSessionId { get; set; } = string.Empty;

    public ChatSession? ChatSession { get; set; }

    public string Role { get; set; } = string.Empty;

    public string Content { get; set; } = string.Empty;

    public string? SuggestedCartActionsJson { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}
