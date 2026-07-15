using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class KitchenStatusMigrationTests
{
    [Fact]
    public void TestV60_LegacyKitchenAggregateDriftHasDataRepairMigration()
    {
        var repositoryRoot = FindRepositoryRoot();
        var migrationPath = Path.Combine(
            repositoryRoot,
            "backend",
            "src",
            "RestaurantQrAiOrdering.Api",
            "Data",
            "Migrations",
            "20260715190000_ReconcileLegacyKitchenStatuses.cs");

        Assert.True(File.Exists(migrationPath), $"Missing migration: {migrationPath}");
        var source = File.ReadAllText(migrationPath);

        Assert.Contains("BOOL_AND(item.status = 'Served')", source, StringComparison.Ordinal);
        Assert.Contains("BOOL_AND(item.status IN ('Ready', 'Served'))", source, StringComparison.Ordinal);
        Assert.Contains("order_row.status IN ('Placed', 'Confirmed')", source, StringComparison.Ordinal);
        Assert.Contains("UPDATE orders", source, StringComparison.Ordinal);
        Assert.Contains("INSERT INTO order_status_history", source, StringComparison.Ordinal);
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "SPEC.md")))
        {
            directory = directory.Parent;
        }

        return directory?.FullName
            ?? throw new InvalidOperationException("Could not locate repository root.");
    }
}
