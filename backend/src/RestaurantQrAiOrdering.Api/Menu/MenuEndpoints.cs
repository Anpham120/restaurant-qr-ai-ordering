using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Menu;

public static class MenuEndpoints
{
    public static IEndpointRouteBuilder MapMenuEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/menu", async (RestaurantDbContext db) =>
        {
            var categories = await db.Categories
                .Where(c => c.IsActive)
                .OrderBy(c => c.DisplayOrder)
                .ThenBy(c => c.Name)
                .ToListAsync();

            var categoryLookup = categories.ToDictionary(
                c => c.Id,
                c => c,
                StringComparer.OrdinalIgnoreCase);

            var items = await db.MenuItems
                .Where(i => categoryLookup.ContainsKey(i.CategoryId))
                .Where(i => i.IsAvailable)
                .ToListAsync();

            var sortedItems = items
                .OrderBy(i => categoryLookup[i.CategoryId].DisplayOrder)
                .ThenBy(i => i.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();

            var sortedCategories = categoryLookup.Values
                .OrderBy(c => c.DisplayOrder)
                .ThenBy(c => c.Name, StringComparer.OrdinalIgnoreCase)
                .Select(ToPublicCategoryResponse)
                .ToList();

            var response = new MenuResponse(
                sortedCategories,
                sortedItems
                    .Select(i => ToMenuItemResponse(i, categoryLookup[i.CategoryId].Name))
                    .ToList());

            return Results.Ok(response);
        })
        .WithName("GetMenu")
        .WithTags("Menu");

        var adminMenu = app.MapGroup("/api/admin/menu-items")
            .WithTags("Admin Menu")
            .RequireAuthorization("StaffOrAdmin");

        adminMenu.MapGet("/", async (bool includeInactiveCategories = false, RestaurantDbContext db = null!) =>
        {
            var categories = await db.Categories
                .ToListAsync();

            var categoriesDict = categories.ToDictionary(
                c => c.Id,
                c => c.Name,
                StringComparer.OrdinalIgnoreCase);

            var activeCategoryIds = categories
                .Where(c => c.IsActive)
                .Select(c => c.Id)
                .ToList();

            var query = db.MenuItems.AsQueryable();

            if (!includeInactiveCategories)
            {
                query = query.Where(i => activeCategoryIds.Contains(i.CategoryId));
            }

            var items = await query
                .OrderBy(i => i.Name)
                .ToListAsync();

            var response = items
                .Select(i => ToMenuItemResponse(i, categoriesDict.GetValueOrDefault(i.CategoryId, string.Empty)))
                .ToList();

            return Results.Ok(response);
        })
        .WithName("AdminGetMenuItems");

        adminMenu.MapGet("/{menuItemId}", async (string menuItemId, RestaurantDbContext db) =>
        {
            var item = await db.MenuItems
                .FirstOrDefaultAsync(i => i.Id == menuItemId);

            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var category = await db.Categories
                .FirstOrDefaultAsync(c => c.Id == item.CategoryId);

            return Results.Ok(ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminGetMenuItem");

        adminMenu.MapPost("/", async (MenuItemRequest? request, RestaurantDbContext db) =>
        {
            var validationError = await ValidateMenuItemRequestAsync(request, db);
            if (validationError is not null)
            {
                return validationError;
            }

            var validatedRequest = request!;
            var now = DateTimeOffset.UtcNow;

            var item = new MenuItem
            {
                Id = await CreateUniqueMenuItemIdAsync(db),
                CategoryId = validatedRequest.CategoryId!.Trim(),
                Name = validatedRequest.Name!.Trim(),
                Description = validatedRequest.Description?.Trim() ?? string.Empty,
                Price = validatedRequest.Price,
                ImageUrl = NormalizeOptional(validatedRequest.ImageUrl),
                IsAvailable = validatedRequest.IsAvailable,
                Tags = NormalizeTags(validatedRequest.Tags ?? []),
                CreatedAt = now,
                UpdatedAt = now
            };

            db.MenuItems.Add(item);
            await db.SaveChangesAsync();

            var category = await db.Categories
                .FirstOrDefaultAsync(c => c.Id == item.CategoryId);

            return Results.Created($"/api/admin/menu-items/{item.Id}", ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminCreateMenuItem");

        adminMenu.MapPut("/{menuItemId}", async (string menuItemId, MenuItemRequest? request, RestaurantDbContext db) =>
        {
            var validationError = await ValidateMenuItemRequestAsync(request, db);
            if (validationError is not null)
            {
                return validationError;
            }

            var item = await db.MenuItems
                .FirstOrDefaultAsync(i => i.Id == menuItemId);

            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var validatedRequest = request!;
            item.CategoryId = validatedRequest.CategoryId!.Trim();
            item.Name = validatedRequest.Name!.Trim();
            item.Description = validatedRequest.Description?.Trim() ?? string.Empty;
            item.Price = validatedRequest.Price;
            item.ImageUrl = NormalizeOptional(validatedRequest.ImageUrl);
            item.IsAvailable = validatedRequest.IsAvailable;
            item.Tags = NormalizeTags(validatedRequest.Tags ?? []);
            item.UpdatedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync();

            var category = await db.Categories
                .FirstOrDefaultAsync(c => c.Id == item.CategoryId);

            return Results.Ok(ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminUpdateMenuItem");

        adminMenu.MapPatch("/{menuItemId}/availability", async (string menuItemId, ToggleAvailabilityRequest? request, RestaurantDbContext db) =>
        {
            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            var item = await db.MenuItems
                .FirstOrDefaultAsync(i => i.Id == menuItemId);

            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            item.IsAvailable = request.IsAvailable;
            item.UpdatedAt = DateTimeOffset.UtcNow;

            await db.SaveChangesAsync();

            var category = await db.Categories
                .FirstOrDefaultAsync(c => c.Id == item.CategoryId);

            return Results.Ok(ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminToggleMenuItemAvailability");

        adminMenu.MapDelete("/{menuItemId}", async (string menuItemId, RestaurantDbContext db) =>
        {
            var item = await db.MenuItems
                .FirstOrDefaultAsync(i => i.Id == menuItemId);

            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            db.MenuItems.Remove(item);
            await db.SaveChangesAsync();

            return Results.NoContent();
        })
        .WithName("AdminDeleteMenuItem");

        return app;
    }

    private static async Task<IResult?> ValidateMenuItemRequestAsync(MenuItemRequest? request, RestaurantDbContext db)
    {
        if (request is null)
        {
            return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

        if (string.IsNullOrWhiteSpace(request.CategoryId))
        {
            return ApiResults.BadRequest("CATEGORY_REQUIRED", "Category is required.");
        }

        var categoryExists = await db.Categories
            .AnyAsync(c => c.Id == request.CategoryId.Trim() && c.IsActive);

        if (!categoryExists)
        {
            return ApiResults.BadRequest("CATEGORY_INVALID", "Category must exist and be active.");
        }

        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ApiResults.BadRequest("MENU_ITEM_NAME_REQUIRED", "Menu item name is required.");
        }

        if (request.Price <= 0)
        {
            return ApiResults.BadRequest("MENU_ITEM_PRICE_INVALID", "Menu item price must be greater than zero.");
        }

        return null;
    }

    private static MenuCategoryResponse ToPublicCategoryResponse(Category category)
    {
        return new MenuCategoryResponse(category.Id, category.Name);
    }

    private static MenuItemResponse ToMenuItemResponse(MenuItem item, string categoryName)
    {
        return new MenuItemResponse(
            item.Id,
            item.Name,
            item.Description,
            item.Price,
            item.CategoryId,
            categoryName,
            item.ImageUrl,
            item.IsAvailable,
            item.Tags.ToList());
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    private static ICollection<string> NormalizeTags(IReadOnlyCollection<string> tags)
    {
        return tags
            .Where(tag => !string.IsNullOrWhiteSpace(tag))
            .Select(tag => tag.Trim())
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static async Task<string> CreateUniqueMenuItemIdAsync(RestaurantDbContext db)
    {
        var allIds = await db.MenuItems
            .Select(i => i.Id)
            .ToListAsync();

        var lastNumber = allIds
            .Select(id => id.StartsWith("m_") && int.TryParse(id.AsSpan(2), out var n) ? n : 0)
            .DefaultIfEmpty(0)
            .Max();

        return $"m_{lastNumber + 1:000}";
    }
}
