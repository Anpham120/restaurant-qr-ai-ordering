#nullable enable

using System;

namespace RestaurantQrAiOrdering.Entities;

/// <summary>
/// Recommendation ledger entry — source of truth for what was suggested,
/// rejected, accepted, or added to cart within a chat session.
/// </summary>
public class ChatRecommendation
{
    public string Id { get; set; } = string.Empty;

    public string ChatSessionId { get; set; } = string.Empty;

    public ChatSession? ChatSession { get; set; }

    public string MenuItemId { get; set; } = string.Empty;

    /// <summary>suggested | rejected | accepted | added_to_cart</summary>
    public string Status { get; set; } = "suggested";

    public string? TurnId { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
