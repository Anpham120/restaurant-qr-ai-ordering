using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Data;

public static class TableQrTokenRotator
{
    private const string LegacyPrefix = "cmc-table-";

    public static async Task RotateLegacyTokensAsync(
        RestaurantDbContext db,
        CancellationToken cancellationToken = default)
    {
        var tables = await db.RestaurantTables
            .Where(table => table.QrToken == null || table.QrToken.StartsWith(LegacyPrefix))
            .ToListAsync(cancellationToken);

        if (tables.Count == 0)
        {
            return;
        }

        foreach (var table in tables)
        {
            RotateTableQrToken(table);
        }

        await db.SaveChangesAsync(cancellationToken);
    }

    public static string RotateTableQrToken(RestaurantTable table)
    {
        var token = GenerateToken();
        table.QrToken = token;
        table.UpdatedAt = DateTimeOffset.UtcNow;
        return token;
    }

    private static string GenerateToken()
    {
        return Convert.ToBase64String(RandomNumberGenerator.GetBytes(32))
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');
    }
}
