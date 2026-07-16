using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Promotions;

public static class PromotionEndpoints
{
    public static IEndpointRouteBuilder MapPromotionEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/promotions/validate", async (
            ValidatePromotionRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            if (request is null || string.IsNullOrWhiteSpace(request.Code))
            {
                return ApiResults.BadRequest("PROMOTION_CODE_REQUIRED", "Promotion code is required.");
            }

            if (request.SubtotalAmount < 0)
            {
                return ApiResults.BadRequest("SUBTOTAL_INVALID", "Subtotal amount must be zero or greater.");
            }

            try
            {
                var result = await PromotionCalculator.TryApplyAsync(
                    db,
                    request.Code,
                    request.SubtotalAmount,
                    DateTimeOffset.UtcNow,
                    cancellationToken);

                if (result is null)
                {
                    return ApiResults.BadRequest("PROMOTION_CODE_REQUIRED", "Promotion code is required.");
                }

                return Results.Ok(new ValidatePromotionResponse(
                    result.Promotion.Code,
                    result.Promotion.Name,
                    result.Promotion.Type.ToString(),
                    request.SubtotalAmount,
                    result.DiscountAmount,
                    result.TotalAmount,
                    result.Promotion.IsFlashSale));
            }
            catch (PromotionInvalidException ex)
            {
                return ApiResults.BadRequest(ex.ErrorCode, ex.Message);
            }
        })
        .WithName("ValidatePromotion")
        .WithTags("Promotions");

        var adminPromotions = app.MapGroup("/api/admin/promotions")
            .WithTags("Admin Promotions")
            .RequireAuthorization("AdminOnly");

        adminPromotions.MapGet("/", async (RestaurantDbContext db, CancellationToken cancellationToken) =>
        {
            var promotions = await db.Promotions
                .OrderByDescending(p => p.IsFlashSale)
                .ThenBy(p => p.Code)
                .ToListAsync(cancellationToken);

            return Results.Ok(promotions.Select(ToResponse).ToList());
        })
        .WithName("AdminGetPromotions");

        adminPromotions.MapGet("/{promotionId}", async (
            string promotionId,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var promotion = await db.Promotions
                .FirstOrDefaultAsync(p => p.Id == promotionId, cancellationToken);

            return promotion is null
                ? ApiResults.NotFound("PROMOTION_NOT_FOUND", "Promotion was not found.")
                : Results.Ok(ToResponse(promotion));
        })
        .WithName("AdminGetPromotion");

        adminPromotions.MapPost("/", async (
            PromotionRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var validationError = ValidatePromotionRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var validatedRequest = request!;
            var normalizedCode = PromotionCalculator.NormalizeCode(validatedRequest.Code)!;
            var codeExists = await db.Promotions.AnyAsync(p => p.Code == normalizedCode, cancellationToken);
            if (codeExists)
            {
                return ApiResults.Conflict("PROMOTION_CODE_EXISTS", "Promotion code already exists.");
            }

            var now = DateTimeOffset.UtcNow;
            var promotion = new Promotion
            {
                Id = $"promo_{Guid.NewGuid():N}",
                Code = normalizedCode,
                Name = validatedRequest.Name!.Trim(),
                Description = NormalizeOptional(validatedRequest.Description),
                Type = Enum.Parse<PromotionType>(validatedRequest.Type!.Trim()),
                DiscountValue = validatedRequest.DiscountValue,
                MinOrderAmount = validatedRequest.MinOrderAmount,
                MaxDiscountAmount = validatedRequest.MaxDiscountAmount,
                IsFlashSale = validatedRequest.IsFlashSale,
                StartsAt = validatedRequest.StartsAt,
                EndsAt = validatedRequest.EndsAt,
                IsActive = validatedRequest.IsActive,
                CreatedAt = now,
                UpdatedAt = now
            };

            db.Promotions.Add(promotion);
            await db.SaveChangesAsync(cancellationToken);

            return Results.Created($"/api/admin/promotions/{promotion.Id}", ToResponse(promotion));
        })
        .WithName("AdminCreatePromotion");

        adminPromotions.MapPut("/{promotionId}", async (
            string promotionId,
            PromotionRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var validationError = ValidatePromotionRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var promotion = await db.Promotions
                .FirstOrDefaultAsync(p => p.Id == promotionId, cancellationToken);

            if (promotion is null)
            {
                return ApiResults.NotFound("PROMOTION_NOT_FOUND", "Promotion was not found.");
            }

            var validatedRequest = request!;
            var normalizedCode = PromotionCalculator.NormalizeCode(validatedRequest.Code)!;
            var codeExists = await db.Promotions.AnyAsync(
                p => p.Code == normalizedCode && p.Id != promotionId,
                cancellationToken);
            if (codeExists)
            {
                return ApiResults.Conflict("PROMOTION_CODE_EXISTS", "Promotion code already exists.");
            }

            promotion.Code = normalizedCode;
            promotion.Name = validatedRequest.Name!.Trim();
            promotion.Description = NormalizeOptional(validatedRequest.Description);
            promotion.Type = Enum.Parse<PromotionType>(validatedRequest.Type!.Trim());
            promotion.DiscountValue = validatedRequest.DiscountValue;
            promotion.MinOrderAmount = validatedRequest.MinOrderAmount;
            promotion.MaxDiscountAmount = validatedRequest.MaxDiscountAmount;
            promotion.IsFlashSale = validatedRequest.IsFlashSale;
            promotion.StartsAt = validatedRequest.StartsAt;
            promotion.EndsAt = validatedRequest.EndsAt;
            promotion.IsActive = validatedRequest.IsActive;
            promotion.UpdatedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync(cancellationToken);

            return Results.Ok(ToResponse(promotion));
        })
        .WithName("AdminUpdatePromotion");

        adminPromotions.MapDelete("/{promotionId}", async (
            string promotionId,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var promotion = await db.Promotions
                .FirstOrDefaultAsync(p => p.Id == promotionId, cancellationToken);

            if (promotion is null)
            {
                return ApiResults.NotFound("PROMOTION_NOT_FOUND", "Promotion was not found.");
            }

            db.Promotions.Remove(promotion);
            await db.SaveChangesAsync(cancellationToken);

            return Results.NoContent();
        })
        .WithName("AdminDeletePromotion");

        return app;
    }

    public static PromotionResponse ToResponse(Promotion promotion)
    {
        return new PromotionResponse(
            promotion.Id,
            promotion.Code,
            promotion.Name,
            promotion.Description,
            promotion.Type.ToString(),
            promotion.DiscountValue,
            promotion.MinOrderAmount,
            promotion.MaxDiscountAmount,
            promotion.IsFlashSale,
            promotion.StartsAt,
            promotion.EndsAt,
            promotion.IsActive,
            promotion.CreatedAt,
            promotion.UpdatedAt);
    }

    private static IResult? ValidatePromotionRequest(PromotionRequest? request)
    {
        if (request is null)
        {
            return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

        if (string.IsNullOrWhiteSpace(request.Code))
        {
            return ApiResults.BadRequest("PROMOTION_CODE_REQUIRED", "Promotion code is required.");
        }

        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ApiResults.BadRequest("PROMOTION_NAME_REQUIRED", "Promotion name is required.");
        }

        if (string.IsNullOrWhiteSpace(request.Type)
            || !Enum.TryParse<PromotionType>(request.Type.Trim(), ignoreCase: false, out _))
        {
            return ApiResults.BadRequest("PROMOTION_TYPE_INVALID", "Promotion type is invalid.");
        }

        if (request.DiscountValue <= 0)
        {
            return ApiResults.BadRequest("PROMOTION_DISCOUNT_INVALID", "Discount value must be greater than zero.");
        }

        if (request.StartsAt is not null && request.EndsAt is not null && request.StartsAt > request.EndsAt)
        {
            return ApiResults.BadRequest("PROMOTION_DATE_RANGE_INVALID", "Promotion start date must be before end date.");
        }

        return null;
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
