using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Menu;

public static class MenuEndpoints
{
    public static IEndpointRouteBuilder MapMenuEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/menu", (RestaurantDataStore store) =>
        {
            var categories = store.GetCategories();
            var categoryLookup = categories.ToDictionary(
                category => category.Id,
                category => category,
                StringComparer.OrdinalIgnoreCase);

            var response = new MenuResponse(
                categories.Select(ToPublicCategoryResponse).ToList(),
                store.GetMenuItems()
                    .Where(item => categoryLookup.ContainsKey(item.CategoryId))
                    .Select(item => ToMenuItemResponse(item, categoryLookup[item.CategoryId].Name))
                    .ToList());

            return Results.Ok(response);
        })
        .WithName("GetMenu")
        .WithTags("Menu");

        var adminMenu = app.MapGroup("/api/admin/menu-items").WithTags("Admin Menu");

        adminMenu.MapGet("/", (RestaurantDataStore store) =>
        {
            var categories = store.GetCategories(includeInactive: true).ToDictionary(
                category => category.Id,
                category => category.Name,
                StringComparer.OrdinalIgnoreCase);

            var response = store.GetMenuItems(includeInactiveCategories: true)
                .Select(item => ToMenuItemResponse(
                    item,
                    categories.GetValueOrDefault(item.CategoryId, string.Empty)))
                .ToList();

            return Results.Ok(response);
        })
        .WithName("AdminGetMenuItems");

        adminMenu.MapGet("/{menuItemId}", (string menuItemId, RestaurantDataStore store) =>
        {
            var item = store.GetMenuItem(menuItemId);
            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var category = store.GetCategory(item.CategoryId, includeInactive: true);
            return Results.Ok(ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminGetMenuItem");

        adminMenu.MapPost("/", (MenuItemRequest? request, RestaurantDataStore store) =>
        {
            var validationError = ValidateMenuItemRequest(request, store);
            if (validationError is not null)
            {
                return validationError;
            }

            var validatedRequest = request!;
            var item = store.CreateMenuItem(
                validatedRequest.CategoryId!.Trim(),
                validatedRequest.Name!,
                validatedRequest.Description ?? string.Empty,
                validatedRequest.Price,
                validatedRequest.ImageUrl,
                validatedRequest.IsAvailable,
                validatedRequest.Tags ?? []);

            var category = store.GetCategory(item.CategoryId, includeInactive: true);
            return Results.Created($"/api/admin/menu-items/{item.Id}", ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminCreateMenuItem");

        adminMenu.MapPut("/{menuItemId}", (string menuItemId, MenuItemRequest? request, RestaurantDataStore store) =>
        {
            var validationError = ValidateMenuItemRequest(request, store);
            if (validationError is not null)
            {
                return validationError;
            }

            var validatedRequest = request!;
            var item = store.UpdateMenuItem(
                menuItemId,
                validatedRequest.CategoryId!.Trim(),
                validatedRequest.Name!,
                validatedRequest.Description ?? string.Empty,
                validatedRequest.Price,
                validatedRequest.ImageUrl,
                validatedRequest.IsAvailable,
                validatedRequest.Tags ?? []);

            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var category = store.GetCategory(item.CategoryId, includeInactive: true);
            return Results.Ok(ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminUpdateMenuItem");

        adminMenu.MapPatch("/{menuItemId}/availability", (string menuItemId, ToggleAvailabilityRequest? request, RestaurantDataStore store) =>
        {
            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            var item = store.ToggleAvailability(menuItemId, request.IsAvailable);
            if (item is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var category = store.GetCategory(item.CategoryId, includeInactive: true);
            return Results.Ok(ToMenuItemResponse(item, category?.Name ?? string.Empty));
        })
        .WithName("AdminToggleMenuItemAvailability");

        adminMenu.MapDelete("/{menuItemId}", (string menuItemId, RestaurantDataStore store) =>
        {
            return store.DeleteMenuItem(menuItemId)
                ? Results.NoContent()
                : ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
        })
        .WithName("AdminDeleteMenuItem");

        return app;
    }

    private static IResult? ValidateMenuItemRequest(MenuItemRequest? request, RestaurantDataStore store)
    {
        if (request is null)
        {
            return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

        if (string.IsNullOrWhiteSpace(request.CategoryId))
        {
            return ApiResults.BadRequest("CATEGORY_REQUIRED", "Category is required.");
        }

        if (!store.CategoryExists(request.CategoryId.Trim()))
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
}
