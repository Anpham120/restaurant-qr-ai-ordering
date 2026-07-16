using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Promotions;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Loyalty;

public static class LoyaltyEndpoints
{
    public static IEndpointRouteBuilder MapLoyaltyEndpoints(this IEndpointRouteBuilder app)
    {
        // Personal loyalty balances are never public: only an authenticated customer
        // or an operator may query a phone number.
        app.MapGet("/api/loyalty/lookup", async (
            string? phone,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var normalizedPhone = PromotionCalculator.NormalizePhone(phone);
            if (normalizedPhone is null)
            {
                return ApiResults.BadRequest("LOYALTY_PHONE_REQUIRED", "Phone number is required.");
            }

            var member = await db.LoyaltyMembers
                .AsNoTracking()
                .FirstOrDefaultAsync(m => m.PhoneNumber == normalizedPhone, cancellationToken);

            var points = member?.Points ?? 0;
            var lifetimeSpend = member?.LifetimeSpend ?? 0m;

            var rewards = await db.LoyaltyRewards
                .AsNoTracking()
                .Where(r => r.IsActive && r.PointsRequired <= points)
                .OrderBy(r => r.PointsRequired)
                .ToListAsync(cancellationToken);

            return Results.Ok(new LoyaltyLookupResponse(
                normalizedPhone,
                points,
                lifetimeSpend,
                rewards.Select(ToRewardResponse).ToList()));
        })
        .WithName("LoyaltyLookup")
        .WithTags("Loyalty")
        .RequireAuthorization();

        MapAdminMembers(app);
        MapAdminRewards(app);

        return app;
    }

    private static void MapAdminMembers(IEndpointRouteBuilder app)
    {
        var members = app.MapGroup("/api/admin/loyalty/members")
            .WithTags("Admin Loyalty")
            .RequireAuthorization("AdminOnly");

        members.MapGet("/", async (RestaurantDbContext db, CancellationToken cancellationToken) =>
        {
            var list = await db.LoyaltyMembers
                .AsNoTracking()
                .OrderByDescending(m => m.Points)
                .ThenBy(m => m.PhoneNumber)
                .ToListAsync(cancellationToken);

            return Results.Ok(list.Select(ToMemberResponse).ToList());
        })
        .WithName("AdminGetLoyaltyMembers");

        members.MapGet("/{memberId}", async (
            string memberId,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var member = await db.LoyaltyMembers
                .AsNoTracking()
                .FirstOrDefaultAsync(m => m.Id == memberId, cancellationToken);

            return member is null
                ? ApiResults.NotFound("LOYALTY_MEMBER_NOT_FOUND", "Loyalty member was not found.")
                : Results.Ok(ToMemberResponse(member));
        })
        .WithName("AdminGetLoyaltyMember");

        members.MapPost("/", async (
            LoyaltyMemberRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var normalizedPhone = PromotionCalculator.NormalizePhone(request?.PhoneNumber);
            if (normalizedPhone is null)
            {
                return ApiResults.BadRequest("LOYALTY_PHONE_REQUIRED", "Phone number is required.");
            }

            if (request!.Points < 0)
            {
                return ApiResults.BadRequest("LOYALTY_POINTS_INVALID", "Points must be zero or greater.");
            }

            var exists = await db.LoyaltyMembers.AnyAsync(m => m.PhoneNumber == normalizedPhone, cancellationToken);
            if (exists)
            {
                return ApiResults.Conflict("LOYALTY_PHONE_EXISTS", "A member with this phone number already exists.");
            }

            var now = DateTimeOffset.UtcNow;
            var member = new LoyaltyMember
            {
                Id = $"loy_{Guid.NewGuid():N}",
                PhoneNumber = normalizedPhone,
                FullName = NormalizeOptional(request.FullName),
                Points = request.Points,
                LifetimeSpend = 0m,
                CreatedAt = now,
                UpdatedAt = now
            };

            db.LoyaltyMembers.Add(member);
            await db.SaveChangesAsync(cancellationToken);

            return Results.Created($"/api/admin/loyalty/members/{member.Id}", ToMemberResponse(member));
        })
        .WithName("AdminCreateLoyaltyMember");

        members.MapPut("/{memberId}", async (
            string memberId,
            LoyaltyMemberRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var normalizedPhone = PromotionCalculator.NormalizePhone(request?.PhoneNumber);
            if (normalizedPhone is null)
            {
                return ApiResults.BadRequest("LOYALTY_PHONE_REQUIRED", "Phone number is required.");
            }

            if (request!.Points < 0)
            {
                return ApiResults.BadRequest("LOYALTY_POINTS_INVALID", "Points must be zero or greater.");
            }

            var member = await db.LoyaltyMembers.FirstOrDefaultAsync(m => m.Id == memberId, cancellationToken);
            if (member is null)
            {
                return ApiResults.NotFound("LOYALTY_MEMBER_NOT_FOUND", "Loyalty member was not found.");
            }

            var phoneTaken = await db.LoyaltyMembers.AnyAsync(
                m => m.PhoneNumber == normalizedPhone && m.Id != memberId,
                cancellationToken);
            if (phoneTaken)
            {
                return ApiResults.Conflict("LOYALTY_PHONE_EXISTS", "A member with this phone number already exists.");
            }

            member.PhoneNumber = normalizedPhone;
            member.FullName = NormalizeOptional(request.FullName);
            member.Points = request.Points;
            member.UpdatedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync(cancellationToken);

            return Results.Ok(ToMemberResponse(member));
        })
        .WithName("AdminUpdateLoyaltyMember");

        members.MapDelete("/{memberId}", async (
            string memberId,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var member = await db.LoyaltyMembers.FirstOrDefaultAsync(m => m.Id == memberId, cancellationToken);
            if (member is null)
            {
                return ApiResults.NotFound("LOYALTY_MEMBER_NOT_FOUND", "Loyalty member was not found.");
            }

            db.LoyaltyMembers.Remove(member);
            await db.SaveChangesAsync(cancellationToken);

            return Results.NoContent();
        })
        .WithName("AdminDeleteLoyaltyMember");
    }

    private static void MapAdminRewards(IEndpointRouteBuilder app)
    {
        var rewards = app.MapGroup("/api/admin/loyalty/rewards")
            .WithTags("Admin Loyalty")
            .RequireAuthorization("AdminOnly");

        rewards.MapGet("/", async (RestaurantDbContext db, CancellationToken cancellationToken) =>
        {
            var list = await db.LoyaltyRewards
                .AsNoTracking()
                .OrderBy(r => r.PointsRequired)
                .ToListAsync(cancellationToken);

            return Results.Ok(list.Select(ToRewardResponse).ToList());
        })
        .WithName("AdminGetLoyaltyRewards");

        rewards.MapPost("/", async (
            LoyaltyRewardRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var validationError = ValidateRewardRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var now = DateTimeOffset.UtcNow;
            var reward = new LoyaltyReward
            {
                Id = $"rwd_{Guid.NewGuid():N}",
                Name = request!.Name!.Trim(),
                Description = NormalizeOptional(request.Description),
                PointsRequired = request.PointsRequired,
                IsActive = request.IsActive,
                CreatedAt = now,
                UpdatedAt = now
            };

            db.LoyaltyRewards.Add(reward);
            await db.SaveChangesAsync(cancellationToken);

            return Results.Created($"/api/admin/loyalty/rewards/{reward.Id}", ToRewardResponse(reward));
        })
        .WithName("AdminCreateLoyaltyReward");

        rewards.MapPut("/{rewardId}", async (
            string rewardId,
            LoyaltyRewardRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var validationError = ValidateRewardRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var reward = await db.LoyaltyRewards.FirstOrDefaultAsync(r => r.Id == rewardId, cancellationToken);
            if (reward is null)
            {
                return ApiResults.NotFound("LOYALTY_REWARD_NOT_FOUND", "Loyalty reward was not found.");
            }

            reward.Name = request!.Name!.Trim();
            reward.Description = NormalizeOptional(request.Description);
            reward.PointsRequired = request.PointsRequired;
            reward.IsActive = request.IsActive;
            reward.UpdatedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync(cancellationToken);

            return Results.Ok(ToRewardResponse(reward));
        })
        .WithName("AdminUpdateLoyaltyReward");

        rewards.MapDelete("/{rewardId}", async (
            string rewardId,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var reward = await db.LoyaltyRewards.FirstOrDefaultAsync(r => r.Id == rewardId, cancellationToken);
            if (reward is null)
            {
                return ApiResults.NotFound("LOYALTY_REWARD_NOT_FOUND", "Loyalty reward was not found.");
            }

            db.LoyaltyRewards.Remove(reward);
            await db.SaveChangesAsync(cancellationToken);

            return Results.NoContent();
        })
        .WithName("AdminDeleteLoyaltyReward");
    }

    private static IResult? ValidateRewardRequest(LoyaltyRewardRequest? request)
    {
        if (request is null)
        {
            return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ApiResults.BadRequest("LOYALTY_REWARD_NAME_REQUIRED", "Reward name is required.");
        }

        if (request.PointsRequired <= 0)
        {
            return ApiResults.BadRequest("LOYALTY_REWARD_POINTS_INVALID", "Points required must be greater than zero.");
        }

        return null;
    }

    private static LoyaltyMemberResponse ToMemberResponse(LoyaltyMember member)
    {
        return new LoyaltyMemberResponse(
            member.Id,
            member.PhoneNumber,
            member.FullName,
            member.Points,
            member.LifetimeSpend,
            member.CreatedAt,
            member.UpdatedAt);
    }

    private static LoyaltyRewardResponse ToRewardResponse(LoyaltyReward reward)
    {
        return new LoyaltyRewardResponse(
            reward.Id,
            reward.Name,
            reward.Description,
            reward.PointsRequired,
            reward.IsActive,
            reward.CreatedAt,
            reward.UpdatedAt);
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
