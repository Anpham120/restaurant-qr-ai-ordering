using System.Reflection;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class AiContractBoundaryTests
{
    [Fact]
    public void ChatAiProvider_UsesStableAiServicePaths()
    {
        var source = ReadSource("ChatAiProvider.cs");

        Assert.Contains("/v1/chat", source, StringComparison.Ordinal);
        Assert.Contains("/v1/chat/stream", source, StringComparison.Ordinal);
        Assert.DoesNotContain("/v2/chat", source, StringComparison.Ordinal);
    }

    [Fact]
    public void AiContractSchema_IsPresentInRepository()
    {
        var repoRoot = FindRepositoryRoot();
        var schemaPath = Path.Combine(repoRoot, "ai", "contracts", "ai-chat-v1.schema.json");
        Assert.True(File.Exists(schemaPath), $"Missing AI contract schema at {schemaPath}");

        var schema = File.ReadAllText(schemaPath);
        Assert.Contains("\"ChatRequest\"", schema, StringComparison.Ordinal);
        Assert.Contains("\"ChatResponse\"", schema, StringComparison.Ordinal);
        Assert.Contains("suggested_cart_actions", schema, StringComparison.Ordinal);
    }

    private static string ReadSource(string fileName)
    {
        var apiRoot = Path.Combine(FindRepositoryRoot(), "backend", "src", "RestaurantQrAiOrdering.Api");
        var path = Directory.EnumerateFiles(apiRoot, fileName, SearchOption.AllDirectories).FirstOrDefault();
        Assert.NotNull(path);
        return File.ReadAllText(path!);
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "ai", "contracts")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new InvalidOperationException("Could not locate repository root.");
    }
}
