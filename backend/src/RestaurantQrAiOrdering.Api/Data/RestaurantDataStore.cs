using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Data;

public sealed class RestaurantDataStore
{
    private readonly object syncRoot = new();
    private readonly List<Category> categories;
    private readonly List<MenuItem> menuItems;
    private readonly List<RestaurantTable> tables;

    public RestaurantDataStore()
    {
        categories = SeedCategories();
        menuItems = SeedMenuItems();
        tables = SeedTables();
    }

    public IReadOnlyList<Category> GetCategories(bool includeInactive = false)
    {
        lock (syncRoot)
        {
            return categories
                .Where(category => includeInactive || category.IsActive)
                .OrderBy(category => category.DisplayOrder)
                .ThenBy(category => category.Name, StringComparer.OrdinalIgnoreCase)
                .Select(CloneCategory)
                .ToList();
        }
    }

    public Category? GetCategory(string categoryId, bool includeInactive = false)
    {
        lock (syncRoot)
        {
            var category = categories.FirstOrDefault(category =>
                category.Id.Equals(categoryId, StringComparison.OrdinalIgnoreCase)
                && (includeInactive || category.IsActive));

            return category is null ? null : CloneCategory(category);
        }
    }

    public Category CreateCategory(string name, int displayOrder, bool isActive)
    {
        lock (syncRoot)
        {
            var now = DateTimeOffset.UtcNow;
            var category = new Category
            {
                Id = CreateUniqueCategoryId(name),
                Name = name.Trim(),
                DisplayOrder = displayOrder,
                IsActive = isActive,
                CreatedAt = now,
                UpdatedAt = now
            };

            categories.Add(category);

            return CloneCategory(category);
        }
    }

    public Category? UpdateCategory(string categoryId, string name, int displayOrder, bool isActive)
    {
        lock (syncRoot)
        {
            var category = categories.FirstOrDefault(category =>
                category.Id.Equals(categoryId, StringComparison.OrdinalIgnoreCase));

            if (category is null)
            {
                return null;
            }

            category.Name = name.Trim();
            category.DisplayOrder = displayOrder;
            category.IsActive = isActive;
            category.UpdatedAt = DateTimeOffset.UtcNow;

            return CloneCategory(category);
        }
    }

    public DeleteCategoryResult DeleteCategory(string categoryId)
    {
        lock (syncRoot)
        {
            var category = categories.FirstOrDefault(category =>
                category.Id.Equals(categoryId, StringComparison.OrdinalIgnoreCase));

            if (category is null)
            {
                return DeleteCategoryResult.NotFound;
            }

            var hasItems = menuItems.Any(item =>
                item.CategoryId.Equals(category.Id, StringComparison.OrdinalIgnoreCase));

            if (hasItems)
            {
                return DeleteCategoryResult.HasMenuItems;
            }

            categories.Remove(category);
            return DeleteCategoryResult.Deleted;
        }
    }

    public IReadOnlyList<MenuItem> GetMenuItems(bool includeInactiveCategories = false)
    {
        lock (syncRoot)
        {
            var visibleCategoryIds = categories
                .Where(category => includeInactiveCategories || category.IsActive)
                .Select(category => category.Id)
                .ToHashSet(StringComparer.OrdinalIgnoreCase);

            return menuItems
                .Where(item => visibleCategoryIds.Contains(item.CategoryId))
                .OrderBy(item => categories.First(category =>
                    category.Id.Equals(item.CategoryId, StringComparison.OrdinalIgnoreCase)).DisplayOrder)
                .ThenBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
                .Select(CloneMenuItem)
                .ToList();
        }
    }

    public MenuItem? GetMenuItem(string menuItemId)
    {
        lock (syncRoot)
        {
            var item = menuItems.FirstOrDefault(item =>
                item.Id.Equals(menuItemId, StringComparison.OrdinalIgnoreCase));

            return item is null ? null : CloneMenuItem(item);
        }
    }

    public MenuItem CreateMenuItem(
        string categoryId,
        string name,
        string description,
        decimal price,
        string? imageUrl,
        bool isAvailable,
        IReadOnlyCollection<string> tags)
    {
        lock (syncRoot)
        {
            var now = DateTimeOffset.UtcNow;
            var item = new MenuItem
            {
                Id = CreateUniqueMenuItemId(),
                CategoryId = categoryId,
                Name = name.Trim(),
                Description = description.Trim(),
                Price = price,
                ImageUrl = NormalizeOptional(imageUrl),
                IsAvailable = isAvailable,
                Tags = NormalizeTags(tags),
                CreatedAt = now,
                UpdatedAt = now
            };

            menuItems.Add(item);

            return CloneMenuItem(item);
        }
    }

    public MenuItem? UpdateMenuItem(
        string menuItemId,
        string categoryId,
        string name,
        string description,
        decimal price,
        string? imageUrl,
        bool isAvailable,
        IReadOnlyCollection<string> tags)
    {
        lock (syncRoot)
        {
            var item = menuItems.FirstOrDefault(item =>
                item.Id.Equals(menuItemId, StringComparison.OrdinalIgnoreCase));

            if (item is null)
            {
                return null;
            }

            item.CategoryId = categoryId;
            item.Name = name.Trim();
            item.Description = description.Trim();
            item.Price = price;
            item.ImageUrl = NormalizeOptional(imageUrl);
            item.IsAvailable = isAvailable;
            item.Tags = NormalizeTags(tags);
            item.UpdatedAt = DateTimeOffset.UtcNow;

            return CloneMenuItem(item);
        }
    }

    public MenuItem? ToggleAvailability(string menuItemId, bool isAvailable)
    {
        lock (syncRoot)
        {
            var item = menuItems.FirstOrDefault(item =>
                item.Id.Equals(menuItemId, StringComparison.OrdinalIgnoreCase));

            if (item is null)
            {
                return null;
            }

            item.IsAvailable = isAvailable;
            item.UpdatedAt = DateTimeOffset.UtcNow;

            return CloneMenuItem(item);
        }
    }

    public bool DeleteMenuItem(string menuItemId)
    {
        lock (syncRoot)
        {
            var item = menuItems.FirstOrDefault(item =>
                item.Id.Equals(menuItemId, StringComparison.OrdinalIgnoreCase));

            if (item is null)
            {
                return false;
            }

            menuItems.Remove(item);
            return true;
        }
    }

    public RestaurantTable? GetActiveTable(string tableCode)
    {
        lock (syncRoot)
        {
            var normalized = tableCode.Trim().ToUpperInvariant();
            var table = tables.FirstOrDefault(table =>
                table.TableCode.Equals(normalized, StringComparison.OrdinalIgnoreCase)
                && table.IsActive);

            return table is null ? null : CloneTable(table);
        }
    }

    public bool CategoryExists(string categoryId, bool requireActive = true)
    {
        lock (syncRoot)
        {
            return categories.Any(category =>
                category.Id.Equals(categoryId, StringComparison.OrdinalIgnoreCase)
                && (!requireActive || category.IsActive));
        }
    }

    private string CreateUniqueCategoryId(string name)
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

        while (categories.Any(category => category.Id.Equals(id, StringComparison.OrdinalIgnoreCase)))
        {
            id = $"{baseId}_{index}";
            index++;
        }

        return id;
    }

    private string CreateUniqueMenuItemId()
    {
        var nextNumber = menuItems
            .Select(item => item.Id)
            .Where(id => id.StartsWith("m_", StringComparison.OrdinalIgnoreCase))
            .Select(id => int.TryParse(id[2..], out var number) ? number : 0)
            .DefaultIfEmpty(0)
            .Max() + 1;

        return $"m_{nextNumber:000}";
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }

    private static IList<string> NormalizeTags(IReadOnlyCollection<string> tags)
    {
        return tags
            .Where(tag => !string.IsNullOrWhiteSpace(tag))
            .Select(tag => tag.Trim())
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static Category CloneCategory(Category category)
    {
        return new Category
        {
            Id = category.Id,
            Name = category.Name,
            DisplayOrder = category.DisplayOrder,
            IsActive = category.IsActive,
            CreatedAt = category.CreatedAt,
            UpdatedAt = category.UpdatedAt
        };
    }

    private static MenuItem CloneMenuItem(MenuItem item)
    {
        return new MenuItem
        {
            Id = item.Id,
            CategoryId = item.CategoryId,
            Name = item.Name,
            Description = item.Description,
            Price = item.Price,
            ImageUrl = item.ImageUrl,
            IsAvailable = item.IsAvailable,
            Tags = item.Tags.ToList(),
            CreatedAt = item.CreatedAt,
            UpdatedAt = item.UpdatedAt
        };
    }

    private static RestaurantTable CloneTable(RestaurantTable table)
    {
        return new RestaurantTable
        {
            Id = table.Id,
            TableCode = table.TableCode,
            DisplayName = table.DisplayName,
            IsActive = table.IsActive,
            QrToken = table.QrToken,
            CreatedAt = table.CreatedAt,
            UpdatedAt = table.UpdatedAt
        };
    }

    private static List<Category> SeedCategories()
    {
        // Mirrors the official 91-dish menu so the AI chat assistant sees
        // the same catalogue as the customer-facing API.
        return RestaurantMenuSeed.CreateCategories(DateTimeOffset.UtcNow).ToList();
    }

    private static List<MenuItem> SeedMenuItems()
    {
        return RestaurantMenuSeed.CreateMenuItems(DateTimeOffset.UtcNow).ToList();
    }

    private static List<RestaurantTable> SeedTables()
    {
        return RestaurantTableSeed.CreateTables(DateTimeOffset.UtcNow).ToList();
    }
}

public enum DeleteCategoryResult
{
    Deleted,
    NotFound,
    HasMenuItems
}
