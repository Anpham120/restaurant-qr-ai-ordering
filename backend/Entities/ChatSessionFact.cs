#nullable enable

using System;

namespace RestaurantQrAiOrdering.Entities;

/// <summary>
/// Extracted preference / constraint fact for a chat session
/// (allergen, diet, spice, budget, party size, language, etc.).
/// </summary>
public class ChatSessionFact
{
    public string Id { get; set; } = string.Empty;

    public string ChatSessionId { get; set; } = string.Empty;

    public ChatSession? ChatSession { get; set; }

    /// <summary>Fact kind e.g. allergen, diet, spice, budget, party_size, language</summary>
    public string Kind { get; set; } = string.Empty;

    public string Value { get; set; } = string.Empty;

    public string? SourceTurnId { get; set; }

    public double Confidence { get; set; } = 1.0;

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
