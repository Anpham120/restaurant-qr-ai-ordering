namespace RestaurantQrAiOrdering.Api.Loyalty;

public sealed record LoyaltyMemberRequest(
    string? PhoneNumber,
    string? FullName,
    int Points);

public sealed record LoyaltyMemberResponse(
    string MemberId,
    string PhoneNumber,
    string? FullName,
    int Points,
    decimal LifetimeSpend,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public sealed record LoyaltyRewardRequest(
    string? Name,
    string? Description,
    int PointsRequired,
    bool IsActive);

public sealed record LoyaltyRewardResponse(
    string RewardId,
    string Name,
    string? Description,
    int PointsRequired,
    bool IsActive,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public sealed record LoyaltyLookupResponse(
    string PhoneNumber,
    int Points,
    decimal LifetimeSpend,
    IReadOnlyList<LoyaltyRewardResponse> AvailableRewards);
