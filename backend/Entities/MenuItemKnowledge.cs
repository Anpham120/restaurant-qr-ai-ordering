#nullable enable

using System;

namespace RestaurantQrAiOrdering.Entities;

/// <summary>
/// Per-dish structured knowledge (ingredients, allergens, spice, calories)
/// managed by admin and joined with live menu for AI grounding.
/// </summary>
public class MenuItemKnowledge
{
    public string Id { get; set; } = string.Empty;

    public string MenuItemId { get; set; } = string.Empty;

    public MenuItem? MenuItem { get; set; }

    public string? Ingredients { get; set; }

    /// <summary>Comma-separated allergen codes e.g. peanut,shellfish,gluten</summary>
    public string? Allergens { get; set; }

    /// <summary>0-5 spice level</summary>
    public int SpiceLevel { get; set; }

    public int? CaloriesEstimate { get; set; }

    public string? FlavorProfile { get; set; }

    public string? DietaryTags { get; set; }

    public string? CookingMethod { get; set; }

    public int? ServingSizePeople { get; set; }

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
