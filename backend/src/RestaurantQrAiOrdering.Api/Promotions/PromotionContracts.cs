namespace RestaurantQrAiOrdering.Api.Promotions;

public sealed record PromotionRequest(
    string? Code,
    string? Name,
    string? Description,
    string? Type,
    decimal DiscountValue,
    decimal? MinOrderAmount,
    decimal? MaxDiscountAmount,
    bool IsFlashSale,
    DateTimeOffset? StartsAt,
    DateTimeOffset? EndsAt,
    bool IsActive);

public sealed record PromotionResponse(
    string PromotionId,
    string Code,
    string Name,
    string? Description,
    string Type,
    decimal DiscountValue,
    decimal? MinOrderAmount,
    decimal? MaxDiscountAmount,
    bool IsFlashSale,
    DateTimeOffset? StartsAt,
    DateTimeOffset? EndsAt,
    bool IsActive,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public sealed record ValidatePromotionRequest(
    string? Code,
    decimal SubtotalAmount);

public sealed record ValidatePromotionResponse(
    string Code,
    string Name,
    string Type,
    decimal SubtotalAmount,
    decimal DiscountAmount,
    decimal TotalAmount,
    bool IsFlashSale);
