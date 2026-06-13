using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Menu;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Categories;

public static class CategoryEndpoints
{
    public static IEndpointRouteBuilder MapCategoryEndpoints(this IEndpointRouteBuilder app)
    {
        var adminCategories = app.MapGroup("/api/admin/categories").WithTags("Admin Categories");

        adminCategories.MapGet("/", async (RestaurantDbContext db) =>
        {
            var categories = await db.Categories
                .OrderBy(c => c.DisplayOrder)
                .ThenBy(c => c.Name, StringComparer.OrdinalIgnoreCase)
                .ToListAsync();

            return Results.Ok(categories
                .Select(ToAdminCategoryResponse)
                .ToList());
        })
        .WithName("AdminGetCategories");

        adminCategories.MapGet("/{categoryId}", async (string categoryId, RestaurantDbContext db) =>
        {
            var category = await db.Categories
                .FirstOrDefaultAsync(c => c.Id == categoryId);

            return category is null
                ? ApiResults.NotFound("CATEGORY_NOT_FOUND", "Category was not found.")
                : Results.Ok(ToAdminCategoryResponse(category));
        })
        .WithName("AdminGetCategory");

        adminCategories.MapPost("/", async (CategoryRequest? request, RestaurantDbContext db) =>
        {
            var validationError = ValidateCategoryRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var validatedRequest = request!;
            var now = DateTimeOffset.UtcNow;

            var category = new Category
            {
                Id = CreateUniqueCategoryId(validatedRequest.Name!, db),
                Name = validatedRequest.Name!.Trim(),
                DisplayOrder = validatedRequest.DisplayOrder,
                IsActive = validatedRequest.IsActive,
                CreatedAt = now,
                UpdatedAt = now
            };

            db.Categories.Add(category);
            await db.SaveChangesAsync();

            return Results.Created($"/api/admin/categories/{category.Id}", ToAdminCategoryResponse(category));
        })
        .WithName("AdminCreateCategory");

        adminCategories.MapPut("/{categoryId}", async (string categoryId, CategoryRequest? request, RestaurantDbContext db) =>
        {
            var validationError = ValidateCategoryRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var category = await db.Categories
                .FirstOrDefaultAsync(c => c.Id == categoryId);

            if (category is null)
            {
                return ApiResults.NotFound("CATEGORY_NOT_FOUND", "Category was not found.");
            }

            var validatedRequest = request!;
            category.Name = validatedRequest.Name!.Trim();
            category.DisplayOrder = validatedRequest.DisplayOrder;
            category.IsActive = validatedRequest.IsActive;
            category.UpdatedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync();

            return Results.Ok(ToAdminCategoryResponse(category));
        })
        .WithName("AdminUpdateCategory");

        adminCategories.MapDelete("/{categoryId}", async (string categoryId, RestaurantDbContext db) =>
        {
            var category = await db.Categories
                .Include(c => c.MenuItems)
                .FirstOrDefaultAsync(c => c.Id == categoryId);

            if (category is null)
            {
                return ApiResults.NotFound("CATEGORY_NOT_FOUND", "Category was not found.");
            }

            if (category.MenuItems.Count > 0)
            {
                return ApiResults.Conflict("CATEGORY_HAS_MENU_ITEMS", "Category has menu items and cannot be deleted.");
            }

            db.Categories.Remove(category);
            await db.SaveChangesAsync();

            return Results.NoContent();
        })
        .WithName("AdminDeleteCategory");

        return app;
    }

    public static AdminCategoryResponse ToAdminCategoryResponse(Category category)
    {
        return new AdminCategoryResponse(
            category.Id,
            category.Name,
            category.DisplayOrder,
            category.IsActive,
            category.CreatedAt,
            category.UpdatedAt);
    }

    private static IResult? ValidateCategoryRequest(CategoryRequest? request)
    {
        if (request is null)
        {
            return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ApiResults.BadRequest("CATEGORY_NAME_REQUIRED", "Category name is required.");
        }

        return null;
    }

    private static string CreateUniqueCategoryId(string name, RestaurantDbContext db)
    {
        var slug = new string(name
            .Trim()
            .ToLowerInvariant()
            .Select(character => char.IsLetterOrDigit(character) ? character : '_')
            .ToArray());

        slug = string.Join('_', slug.Split('_', StringSplitOptions.RemoveEmptyEntries));

        if (string.IsNullOrWhiteSpace(slug))
        {
            slug = "category";
        }

        var baseId = $"cat_{slug}";
        var id = baseId;
        var index = 2;

        while (db.Categories.Any(c => c.Id == id))
        {
            id = $"{baseId}_{index}";
            index++;
        }

        return id;
    }
}
