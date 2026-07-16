#nullable enable

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace RestaurantQrAiOrdering.Api.Data;

public class RestaurantDbContextFactory : IDesignTimeDbContextFactory<RestaurantDbContext>
{
    public RestaurantDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<RestaurantDbContext>();

        var connectionString = Environment.GetEnvironmentVariable("EF_CONNECTION_STRING")
            ?? "Host=localhost;Port=5432;Database=restaurant_qr;Username=restaurant_user;Password=ChangeMe123!";

        optionsBuilder.UseNpgsql(connectionString);

        return new RestaurantDbContext(optionsBuilder.Options);
    }
}
