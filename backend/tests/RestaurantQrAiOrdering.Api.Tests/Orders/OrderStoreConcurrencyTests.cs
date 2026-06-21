using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Tests.Orders;

public sealed class OrderStoreConcurrencyTests
{
    [Fact]
    public void UpdateOrderStatus_WhenSaveHitsConcurrencyConflict_ReturnsConflictStale()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase($"ConcurrencyTest_{Guid.NewGuid():N}")
            .Options;
        using var db = new TestRestaurantDbContext(options);

        var now = DateTimeOffset.UtcNow;
        db.Orders.Add(new Order
        {
            Id = "ord_concurrency",
            OrderCode = "ORD-9001",
            OrderType = OrderType.DineIn,
            Status = OrderStatus.Placed,
            TableCode = "T01",
            SubtotalAmount = 1000m,
            TotalAmount = 1000m,
            CreatedAt = now,
            UpdatedAt = now,
            Payment = new Payment
            {
                Id = "pay_concurrency",
                OrderId = "ord_concurrency",
                Method = PaymentMethod.COD,
                Status = PaymentStatus.Unpaid,
                Amount = 1000m,
                CreatedAt = now,
                UpdatedAt = now
            }
        });
        db.SaveChanges();

        // Simulate another request having mutated the row between load and save.
        db.ThrowConcurrencyOnSave = true;
        var store = new OrderStore(db);

        var result = store.UpdateOrderStatus("ORD-9001", OrderStatus.Confirmed, ActorContext.Customer);

        Assert.True(result.IsFound);
        Assert.Equal("CONFLICT_STALE", result.ErrorCode);
    }

    [Fact]
    public void UpdateOrderItemStatus_WhenSaveHitsConcurrencyConflict_ReturnsConflictStale()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase($"ConcurrencyTest_{Guid.NewGuid():N}")
            .Options;
        using var db = new TestRestaurantDbContext(options);

        var now = DateTimeOffset.UtcNow;
        db.Orders.Add(new Order
        {
            Id = "ord_item_concurrency",
            OrderCode = "ORD-9100",
            OrderType = OrderType.DineIn,
            Status = OrderStatus.Placed,
            TableCode = "T01",
            SubtotalAmount = 1000m,
            TotalAmount = 1000m,
            CreatedAt = now,
            UpdatedAt = now,
            OrderItems =
            {
                new OrderItem
                {
                    Id = "oi_concurrency",
                    OrderId = "ord_item_concurrency",
                    MenuItemId = "m_001",
                    MenuItemName = "Pho",
                    UnitPrice = 1000m,
                    Quantity = 1,
                    Status = OrderItemStatus.Pending,
                    CreatedAt = now,
                    UpdatedAt = now
                }
            },
            Payment = new Payment
            {
                Id = "pay_item_concurrency",
                OrderId = "ord_item_concurrency",
                Method = PaymentMethod.COD,
                Status = PaymentStatus.Unpaid,
                Amount = 1000m,
                CreatedAt = now,
                UpdatedAt = now
            }
        });
        db.SaveChanges();

        // Simulate another request having mutated the row between load and save.
        db.ThrowConcurrencyOnSave = true;
        var store = new OrderStore(db);

        var result = store.UpdateOrderItemStatus("ORD-9100", "oi_concurrency", OrderItemStatus.Ready);

        Assert.True(result.IsOrderFound);
        Assert.True(result.IsItemFound);
        Assert.Equal("CONFLICT_STALE", result.ErrorCode);
    }
}
