#nullable enable

namespace RestaurantQrAiOrdering.Entities;

public class LoyaltyMember
{
    public string Id { get; set; } = string.Empty;

    public string PhoneNumber { get; set; } = string.Empty;

    public string? FullName { get; set; }

    public int Points { get; set; }

    public decimal LifetimeSpend { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}
