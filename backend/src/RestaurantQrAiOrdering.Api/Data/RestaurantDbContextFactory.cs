#nullable enable

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace RestaurantQrAiOrdering.Api.Data;

public class RestaurantDbContextFactory : IDesignTimeDbContextFactory<RestaurantDbContext>
{
    public RestaurantDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<RestaurantDbContext>();

        var connectionString = Environment.GetEnvironmentVariable("EF_CONNECTION_STRING");
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            throw new InvalidOperationException("EF_CONNECTION_STRING is required for design-time database operations.");
        }

        optionsBuilder.UseNpgsql(connectionString);

        return new RestaurantDbContext(optionsBuilder.Options);
    }
}
