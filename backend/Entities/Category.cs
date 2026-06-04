#nullable enable

using System.Collections.Generic;

namespace RestaurantQrAiOrdering.Entities;

public class Category
{
    public string Id { get; set; } = string.Empty;

    public string Name { get; set; } = string.Empty;

    public int DisplayOrder { get; set; }

    public bool IsActive { get; set; } = true;

    public ICollection<MenuItem> MenuItems { get; set; } = new List<MenuItem>();
}
