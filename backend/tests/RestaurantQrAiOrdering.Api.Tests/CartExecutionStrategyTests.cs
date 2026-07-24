using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class CartExecutionStrategyTests
{
    [Fact]
    public void CartMutationsWrapSerializableTransactionInExecutionStrategy()
    {
        var repositoryRoot = FindRepositoryRoot();
        var source = File.ReadAllText(Path.Combine(
            repositoryRoot,
            "backend",
            "src",
            "RestaurantQrAiOrdering.Api",
            "Cart",
            "CartEndpoints.cs"));

        AssertExecutionStrategyBeforeTransaction(source, "cart/items", ".WithName(\"UpdateTableSessionCartItem\")");
        AssertExecutionStrategyBeforeTransaction(source, "MapDelete(\"/api/table-sessions/{tableSessionId}/cart\"", ".WithName(\"ClearTableSessionCart\")");
    }

    private static void AssertExecutionStrategyBeforeTransaction(string source, string routeMarker, string routeEndMarker)
    {
        var routeStart = source.IndexOf(routeMarker, StringComparison.Ordinal);
        var routeEnd = source.IndexOf(routeEndMarker, routeStart, StringComparison.Ordinal);

        Assert.True(routeStart >= 0 && routeEnd > routeStart);
        var handler = source[routeStart..routeEnd];
        var strategyIndex = handler.IndexOf("CreateExecutionStrategy()", StringComparison.Ordinal);
        var executeIndex = handler.IndexOf("ExecuteAsync<IResult>", StringComparison.Ordinal);
        var transactionIndex = handler.IndexOf("BeginTransactionAsync", StringComparison.Ordinal);

        Assert.True(strategyIndex >= 0);
        Assert.True(executeIndex > strategyIndex);
        Assert.True(transactionIndex > executeIndex);
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "SPEC.md")))
        {
            directory = directory.Parent;
        }

        Assert.NotNull(directory);
        return directory!.FullName;
    }
}
