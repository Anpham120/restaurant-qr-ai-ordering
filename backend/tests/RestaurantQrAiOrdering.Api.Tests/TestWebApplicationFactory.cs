using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Realtime;

namespace RestaurantQrAiOrdering.Api.Tests;

public class TestWebApplicationFactory : WebApplicationFactory<Program>
{
    private static readonly RecordingOrderRealtimeNotifier SharedRealtimeNotifier = new();
    private readonly string _dbName = $"TestDb_{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureServices(services =>
        {
            var removeTypes = new[]
            {
                typeof(DbContextOptions<RestaurantDbContext>),
                typeof(DbContextOptions),
                typeof(RestaurantDbContext),
            };

            foreach (var type in removeTypes)
            {
                var descriptors = services.Where(d => d.ServiceType == type).ToList();
                foreach (var d in descriptors)
                {
                    services.Remove(d);
                }
            }

            services.AddSingleton<DbContextOptions<RestaurantDbContext>>(
                new DbContextOptionsBuilder<RestaurantDbContext>()
                    .UseInMemoryDatabase(_dbName)
                    .Options);

            services.AddScoped<RestaurantDbContext>(sp =>
            {
                return new RestaurantDbContext(sp.GetRequiredService<DbContextOptions<RestaurantDbContext>>());
            });

            var realtimeDescriptors = services.Where(
                d => d.ServiceType == typeof(IOrderRealtimeNotifier)).ToList();
            foreach (var d in realtimeDescriptors)
            {
                services.Remove(d);
            }
            services.AddSingleton<IOrderRealtimeNotifier>(SharedRealtimeNotifier);
        });
    }

    public RecordingOrderRealtimeNotifier GetRealtimeNotifier() => SharedRealtimeNotifier;
}

public sealed class RecordingOrderRealtimeNotifier : IOrderRealtimeNotifier
{
    public List<OrderCreatedEvent> Created { get; } = [];
    public List<(OrderStatusChangedEvent Payload, string? TableCode)> StatusChanged { get; } = [];
    public List<(OrderItemStatusChangedEvent Payload, string? TableCode)> ItemStatusChanged { get; } = [];

    public void Clear()
    {
        Created.Clear();
        StatusChanged.Clear();
        ItemStatusChanged.Clear();
    }

    public Task OrderCreatedAsync(OrderCreatedEvent payload, CancellationToken cancellationToken)
    {
        Created.Add(payload);
        return Task.CompletedTask;
    }

    public Task OrderStatusChangedAsync(
        OrderStatusChangedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        StatusChanged.Add((payload, tableCode));
        return Task.CompletedTask;
    }

    public Task OrderItemStatusChangedAsync(
        OrderItemStatusChangedEvent payload,
        string? tableCode,
        CancellationToken cancellationToken)
    {
        ItemStatusChanged.Add((payload, tableCode));
        return Task.CompletedTask;
    }
}
