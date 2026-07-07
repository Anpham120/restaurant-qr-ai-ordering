using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Promotions;

public sealed record PromotionDiscountResult(
    Promotion Promotion,
    decimal DiscountAmount,
    decimal TotalAmount);

public static class PromotionCalculator
{
    public static async Task<PromotionDiscountResult?> TryApplyAsync(
        RestaurantDbContext db,
        string? promotionCode,
        decimal subtotalAmount,
        DateTimeOffset now,
        CancellationToken cancellationToken = default)
    {
        var normalizedCode = NormalizeCode(promotionCode);
        if (normalizedCode is null)
        {
            return null;
        }

        var promotion = await db.Promotions
            .AsNoTracking()
            .FirstOrDefaultAsync(
                p => p.Code == normalizedCode,
                cancellationToken);

        if (promotion is null)
        {
            throw new PromotionInvalidException("PROMOTION_NOT_FOUND", "Promotion code was not found.");
        }

        ValidatePromotion(promotion, subtotalAmount, now);
        var discountAmount = CalculateDiscount(promotion, subtotalAmount);

        return new PromotionDiscountResult(
            promotion,
            discountAmount,
            Math.Max(0, subtotalAmount - discountAmount));
    }

    public static PromotionDiscountResult Apply(Promotion promotion, decimal subtotalAmount, DateTimeOffset now)
    {
        ValidatePromotion(promotion, subtotalAmount, now);
        var discountAmount = CalculateDiscount(promotion, subtotalAmount);

        return new PromotionDiscountResult(
            promotion,
            discountAmount,
            Math.Max(0, subtotalAmount - discountAmount));
    }

    public static string? NormalizeCode(string? promotionCode)
    {
        if (string.IsNullOrWhiteSpace(promotionCode))
        {
            return null;
        }

        return promotionCode.Trim().ToUpperInvariant();
    }

    public static string? NormalizePhone(string? phoneNumber)
    {
        if (string.IsNullOrWhiteSpace(phoneNumber))
        {
            return null;
        }

        var digits = new string(phoneNumber.Where(char.IsDigit).ToArray());
        return digits.Length == 0 ? null : digits;
    }

    private static void ValidatePromotion(Promotion promotion, decimal subtotalAmount, DateTimeOffset now)
    {
        if (!promotion.IsActive)
        {
            throw new PromotionInvalidException("PROMOTION_INACTIVE", "Promotion is not active.");
        }

        if (promotion.StartsAt is not null && now < promotion.StartsAt.Value)
        {
            throw new PromotionInvalidException("PROMOTION_NOT_STARTED", "Promotion has not started yet.");
        }

        if (promotion.EndsAt is not null && now > promotion.EndsAt.Value)
        {
            throw new PromotionInvalidException("PROMOTION_EXPIRED", "Promotion has expired.");
        }

        if (promotion.MinOrderAmount is not null && subtotalAmount < promotion.MinOrderAmount.Value)
        {
            throw new PromotionInvalidException(
                "PROMOTION_MIN_ORDER_NOT_MET",
                $"Order subtotal must be at least {promotion.MinOrderAmount.Value:N0} VND.");
        }
    }

    private static decimal CalculateDiscount(Promotion promotion, decimal subtotalAmount)
    {
        decimal discount = promotion.Type switch
        {
            PromotionType.Percentage => Math.Round(subtotalAmount * promotion.DiscountValue / 100m, 0, MidpointRounding.AwayFromZero),
            PromotionType.FixedAmount => promotion.DiscountValue,
            _ => 0m
        };

        if (promotion.MaxDiscountAmount is not null)
        {
            discount = Math.Min(discount, promotion.MaxDiscountAmount.Value);
        }

        return Math.Min(discount, subtotalAmount);
    }
}

public sealed class PromotionInvalidException : Exception
{
    public PromotionInvalidException(string errorCode, string message)
        : base(message)
    {
        ErrorCode = errorCode;
    }

    public string ErrorCode { get; }
}
