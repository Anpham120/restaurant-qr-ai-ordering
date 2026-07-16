using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class PersistenceMappingTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public PersistenceMappingTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public void TestV8_KnowledgeEmbeddingUsesStructuralValueComparison()
    {
        using var scope = factory.Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
        var embeddingProperty = db.Model
            .FindEntityType(typeof(KnowledgeEntry))!
            .FindProperty(nameof(KnowledgeEntry.Embedding));
        var comparer = embeddingProperty!.GetValueComparer();

        Assert.NotNull(comparer);
        var embedding = new[] { 0.5f, 1.0f };
        var snapshot = (float[])comparer!.Snapshot(embedding);

        Assert.NotSame(embedding, snapshot);
        Assert.True(comparer.Equals(embedding, snapshot));
    }

    [Theory]
    [InlineData(typeof(Order))]
    [InlineData(typeof(Payment))]
    public void TestV9_PostgresXminUsesTheStandardRowVersionMapping(Type entityType)
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseNpgsql("Host=localhost;Database=mapping_only;Username=test;Password=test")
            .Options;
        using var db = new RestaurantDbContext(options);
        var xmin = db.Model.FindEntityType(entityType)!.FindProperty("xmin");

        Assert.NotNull(xmin);
        Assert.True(xmin!.IsConcurrencyToken);
        Assert.Equal(ValueGenerated.OnAddOrUpdate, xmin.ValueGenerated);
        Assert.Equal("xid", xmin.GetColumnType());
    }
}
