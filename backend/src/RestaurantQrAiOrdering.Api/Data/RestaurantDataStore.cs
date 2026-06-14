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

    private static ICollection<string> NormalizeTags(IReadOnlyCollection<string> tags)
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
        // Seed data for development/demo only.
        // In production, categories will be managed via admin API or database migration.
        var now = DateTimeOffset.UtcNow;

        return
        [
            new Category { Id = "cat_appetizer", Name = "Khai vi", DisplayOrder = 10, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_main", Name = "Mon chinh", DisplayOrder = 20, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_noodle", Name = "Pho va bun", DisplayOrder = 30, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_seafood", Name = "Hai san", DisplayOrder = 40, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_drink", Name = "Do uong", DisplayOrder = 50, IsActive = true, CreatedAt = now, UpdatedAt = now },
            new Category { Id = "cat_dessert", Name = "Trang mieng", DisplayOrder = 60, IsActive = true, CreatedAt = now, UpdatedAt = now }
        ];
    }

    private static List<MenuItem> SeedMenuItems()
    {
        // Seed data for development/demo only.
        // In production, menu items will be managed via admin API or database migration.
        // Note: Some items have isAvailable=false to test out-of-stock scenarios.
        var now = DateTimeOffset.UtcNow;

        return
        [
            CreateSeedMenuItem("m_001", "cat_main", "Com ga xoi mo", "Ga chien gion, com thom, dua chua.", 45000, "https://example.com/images/com-ga-xoi-mo.jpg", true, ["pho bien", "mon chinh", "signature"], now),
            CreateSeedMenuItem("m_002", "cat_main", "Com suon nuong", "Suon uop mat ong nuong than, an kem rau chua.", 52000, "https://example.com/images/com-suon-nuong.jpg", true, ["pho bien", "nuong"], now),
            CreateSeedMenuItem("m_003", "cat_noodle", "Pho bo tai", "Pho bo nuoc dung trong, bo tai mem, rau thom.", 55000, "https://example.com/images/pho-bo-tai.jpg", true, ["nong", "pho", "bo"], now),
            CreateSeedMenuItem("m_004", "cat_noodle", "Bun bo Hue", "Nuoc dung dam vi sa te, bo, cha cua va rau song.", 60000, "https://example.com/images/bun-bo-hue.jpg", false, ["cay", "het hang", "unavailable-demo"], now),
            CreateSeedMenuItem("m_005", "cat_appetizer", "Goi cuon tom thit", "Goi cuon tuoi kem nuoc cham dau phong.", 39000, "https://example.com/images/goi-cuon.jpg", true, ["fresh", "light"], now),
            CreateSeedMenuItem("m_006", "cat_appetizer", "Cha gio hai san", "Cha gio gion nhan hai san, sot mayo cay.", 42000, "https://example.com/images/cha-gio-hai-san.jpg", true, ["chien gion", "seafood"], now),
            CreateSeedMenuItem("m_007", "cat_seafood", "Tom rang muoi", "Tom tuoi rang muoi ot, an kem rau thom.", 185000, "https://example.com/images/tom-rang-muoi.jpg", true, ["seafood", "share"], now),
            CreateSeedMenuItem("m_008", "cat_seafood", "Lau Thai hai san", "Lau Thai chua cay voi tom, muc, ca va rau tuoi.", 345000, "https://example.com/images/lau-thai-hai-san.jpg", true, ["spicy", "seafood", "share"], now),
            CreateSeedMenuItem("m_009", "cat_drink", "Tra dao cam sa", "Tra dao mat lanh voi cam vang va sa tuoi.", 55000, "https://example.com/images/tra-dao-cam-sa.jpg", true, ["drink", "fresh"], now),
            CreateSeedMenuItem("m_010", "cat_drink", "Ca phe sua da", "Ca phe rang xay pha phin, sua dac va da vien.", 45000, "https://example.com/images/ca-phe-sua-da.jpg", false, ["drink", "coffee", "unavailable-demo"], now),
            CreateSeedMenuItem("m_011", "cat_dessert", "Che khuc bach", "Khuc bach beo nhe, vai, hanh nhan va siro duong phen.", 55000, "https://example.com/images/che-khuc-bach.jpg", true, ["sweet", "cool"], now),
            CreateSeedMenuItem("m_012", "cat_dessert", "Banh flan caramel", "Banh flan min, caramel thom, dung lanh.", 35000, "https://example.com/images/banh-flan.jpg", true, ["sweet", "classic"], now)
        ];
    }

    private static MenuItem CreateSeedMenuItem(
        string id,
        string categoryId,
        string name,
        string description,
        decimal price,
        string imageUrl,
        bool isAvailable,
        ICollection<string> tags,
        DateTimeOffset now)
    {
        return new MenuItem
        {
            Id = id,
            CategoryId = categoryId,
            Name = name,
            Description = description,
            Price = price,
            ImageUrl = imageUrl,
            IsAvailable = isAvailable,
            Tags = tags,
            CreatedAt = now,
            UpdatedAt = now
        };
    }

    private static List<RestaurantTable> SeedTables()
    {
        // Seed data for development/demo only.
        // In production, tables will be created via admin API or database migration.
        var now = DateTimeOffset.UtcNow;

        return Enumerable
            .Range(1, 8)
            .Select(number => new RestaurantTable
            {
                Id = $"tbl_{number:00}",
                TableCode = $"T{number:00}",
                DisplayName = $"Ban {number:00}",
                IsActive = true,
                QrToken = $"cmc-table-t{number:00}-qr",
                CreatedAt = now,
                UpdatedAt = now
            })
            .ToList();
    }
}

public enum DeleteCategoryResult
{
    Deleted,
    NotFound,
    HasMenuItems
}
