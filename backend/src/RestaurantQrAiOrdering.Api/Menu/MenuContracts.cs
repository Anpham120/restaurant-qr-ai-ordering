namespace RestaurantQrAiOrdering.Api.Menu;

public sealed record MenuResponse(
    IReadOnlyList<MenuCategoryResponse> Categories,
    IReadOnlyList<MenuItemResponse> Items);

public sealed record MenuCategoryResponse(
    string CategoryId,
    string Name);

public sealed record AdminCategoryResponse(
    string CategoryId,
    string Name,
    int DisplayOrder,
    bool IsActive,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public sealed record MenuItemResponse(
    string Id,
    string Name,
    string Description,
    decimal Price,
    string CategoryId,
    string CategoryName,
    string? ImageUrl,
    bool IsAvailable,
    IReadOnlyList<string> Tags);

public sealed record CategoryRequest(
    string? Name,
    int DisplayOrder,
    bool IsActive = true);

public sealed record MenuItemRequest(
    string? CategoryId,
    string? Name,
    string? Description,
    decimal Price,
    string? ImageUrl,
    bool IsAvailable = true,
    IReadOnlyList<string>? Tags = null);

public sealed record ToggleAvailabilityRequest(bool IsAvailable);
