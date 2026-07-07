using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Data;

public static class RestaurantTableSeed
{
    public const int TableCount = 40;

    public static IReadOnlyList<RestaurantTable> CreateTables(DateTimeOffset seededAt)
    {
        return Enumerable.Range(1, TableCount)
            .Select(index => new RestaurantTable
            {
                Id = $"tbl_{index:D2}",
                TableCode = FormatTableCode(index),
                DisplayName = $"Ban {index:D2}",
                IsActive = true,
                QrToken = $"cmc-table-t{index:D2}-qr",
                CreatedAt = seededAt,
                UpdatedAt = seededAt
            })
            .ToList();
    }

    public static string FormatTableCode(int index) => $"T{index:D2}";
}
