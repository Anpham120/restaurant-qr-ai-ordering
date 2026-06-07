using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Menu;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Categories;

public static class CategoryEndpoints
{
    public static IEndpointRouteBuilder MapCategoryEndpoints(this IEndpointRouteBuilder app)
    {
        var adminCategories = app.MapGroup("/api/admin/categories").WithTags("Admin Categories");

        adminCategories.MapGet("/", (RestaurantDataStore store) =>
        {
            return Results.Ok(store.GetCategories(includeInactive: true)
                .Select(ToAdminCategoryResponse)
                .ToList());
        })
        .WithName("AdminGetCategories");

        adminCategories.MapGet("/{categoryId}", (string categoryId, RestaurantDataStore store) =>
        {
            var category = store.GetCategory(categoryId, includeInactive: true);

            return category is null
                ? ApiResults.NotFound("CATEGORY_NOT_FOUND", "Category was not found.")
                : Results.Ok(ToAdminCategoryResponse(category));
        })
        .WithName("AdminGetCategory");

        adminCategories.MapPost("/", (CategoryRequest request, RestaurantDataStore store) =>
        {
            var validationError = ValidateCategoryRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var category = store.CreateCategory(request.Name!, request.DisplayOrder, request.IsActive);

            return Results.Created($"/api/admin/categories/{category.Id}", ToAdminCategoryResponse(category));
        })
        .WithName("AdminCreateCategory");

        adminCategories.MapPut("/{categoryId}", (string categoryId, CategoryRequest request, RestaurantDataStore store) =>
        {
            var validationError = ValidateCategoryRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var category = store.UpdateCategory(categoryId, request.Name!, request.DisplayOrder, request.IsActive);

            return category is null
                ? ApiResults.NotFound("CATEGORY_NOT_FOUND", "Category was not found.")
                : Results.Ok(ToAdminCategoryResponse(category));
        })
        .WithName("AdminUpdateCategory");

        adminCategories.MapDelete("/{categoryId}", (string categoryId, RestaurantDataStore store) =>
        {
            return store.DeleteCategory(categoryId) switch
            {
                DeleteCategoryResult.Deleted => Results.NoContent(),
                DeleteCategoryResult.HasMenuItems => ApiResults.Conflict("CATEGORY_HAS_MENU_ITEMS", "Category has menu items and cannot be deleted."),
                _ => ApiResults.NotFound("CATEGORY_NOT_FOUND", "Category was not found.")
            };
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

    private static IResult? ValidateCategoryRequest(CategoryRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Name))
        {
            return ApiResults.BadRequest("CATEGORY_NAME_REQUIRED", "Category name is required.");
        }

        return null;
    }
}
