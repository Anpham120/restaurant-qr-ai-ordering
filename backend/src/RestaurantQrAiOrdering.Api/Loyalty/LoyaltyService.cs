using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Loyalty;

public static class LoyaltyService
{
    public const int PointsPerTenThousandVnd = 1;
    public const decimal VndPerPoint = 10_000m;

    public static int CalculatePoints(decimal totalAmount)
    {
        if (totalAmount <= 0)
        {
            return 0;
        }

        return (int)Math.Floor(totalAmount / VndPerPoint);
    }

    public static async Task<LoyaltyMember?> AccruePointsAsync(
        RestaurantDbContext db,
        string? phoneNumber,
        decimal totalAmount,
        DateTimeOffset now,
        CancellationToken cancellationToken = default)
    {
        var normalizedPhone = Promotions.PromotionCalculator.NormalizePhone(phoneNumber);
        if (normalizedPhone is null)
        {
            return null;
        }

        var pointsToAdd = CalculatePoints(totalAmount);
        if (pointsToAdd <= 0)
        {
            return null;
        }

        var member = await db.LoyaltyMembers
            .FirstOrDefaultAsync(m => m.PhoneNumber == normalizedPhone, cancellationToken);

        if (member is null)
        {
            member = new LoyaltyMember
            {
                Id = $"loy_{Guid.NewGuid():N}",
                PhoneNumber = normalizedPhone,
                Points = pointsToAdd,
                LifetimeSpend = totalAmount,
                CreatedAt = now,
                UpdatedAt = now
            };
            db.LoyaltyMembers.Add(member);
            return member;
        }

        member.Points += pointsToAdd;
        member.LifetimeSpend += totalAmount;
        member.UpdatedAt = now;
        return member;
    }
}
