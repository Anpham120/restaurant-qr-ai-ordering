#nullable enable

using System;
using System.Collections.Generic;

namespace RestaurantQrAiOrdering.Entities;

public class KnowledgeEntry
{
    public string Id { get; set; } = string.Empty;

    public string Title { get; set; } = string.Empty;

    public string Content { get; set; } = string.Empty;

    public string SourceType { get; set; } = string.Empty;

    public string? MenuItemId { get; set; }

    public MenuItem? MenuItem { get; set; }

    public ICollection<string> Tags { get; set; } = new List<string>();

    public float[]? Embedding { get; set; }

    public bool IsActive { get; set; } = true;

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
