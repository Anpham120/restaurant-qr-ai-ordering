using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Orders;

public interface IOrderStore
{
    OrderSnapshot CreateOrder(CreateOrderCommand command);

    OrderSnapshot? GetOrder(string orderCode);

    UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status);

    UpdateOrderItemStatusResult UpdateOrderItemStatus(string orderCode, string orderItemId, OrderItemStatus status);
}

public sealed class OrderStore : IOrderStore
{
    private readonly RestaurantDbContext db;

    public OrderStore(RestaurantDbContext db)
    {
        this.db = db;
    }

    public OrderSnapshot CreateOrder(CreateOrderCommand command)
    {
        var now = DateTimeOffset.UtcNow;
        var orderType = Enum.Parse<OrderType>(command.OrderType);
        var paymentMethod = Enum.Parse<PaymentMethod>(command.PaymentMethod);
        var tableCode = NormalizeOptional(command.TableCode)?.ToUpperInvariant();
        var table = orderType == OrderType.DineIn && tableCode is not null
            ? db.RestaurantTables.FirstOrDefault(t => t.TableCode == tableCode && t.IsActive)
            : null;
        var menuItems = LoadMenuItems(command);

        var order = new Order
        {
            Id = $"ord_{Guid.NewGuid():N}",
            OrderCode = CreateNextOrderCode(),
            CustomerAccessToken = GenerateAccessToken(),
            OrderType = orderType,
            Status = OrderStatus.Placed,
            RestaurantTableId = table?.Id,
            RestaurantTable = table,
            TableCode = table?.TableCode ?? tableCode,
            CreatedAt = now,
            UpdatedAt = now,
            Payment = new Payment
            {
                Id = $"pay_{Guid.NewGuid():N}",
                Method = paymentMethod,
                Status = PaymentStatus.Unpaid,
                CreatedAt = now,
                UpdatedAt = now
            }
        };

        ApplyDeliveryInfo(order, command.DeliveryInfo);

        foreach (var requestItem in command.Items)
        {
            var menuItem = menuItems[requestItem.MenuItemId!.Trim()];
            order.OrderItems.Add(new OrderItem
            {
                Id = $"oi_{Guid.NewGuid():N}",
                OrderId = order.Id,
                MenuItemId = menuItem.Id,
                MenuItemName = menuItem.Name,
                UnitPrice = menuItem.Price,
                Quantity = requestItem.Quantity,
                Status = OrderItemStatus.Pending,
                CreatedAt = now,
                UpdatedAt = now
            });
        }

        order.SubtotalAmount = order.OrderItems.Sum(item => item.UnitPrice * item.Quantity);
        order.TotalAmount = order.SubtotalAmount;
        order.Payment.Amount = order.TotalAmount;

        db.Orders.Add(order);
        db.SaveChanges();

        return ToSnapshot(order, [new OrderStatusEventSnapshot(order.Status.ToString(), now)]);
    }

    public OrderSnapshot? GetOrder(string orderCode)
    {
        var order = LoadOrder(orderCode, tracking: false);
        return order is null ? null : ToSnapshot(order);
    }

    public UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status)
    {
        var order = LoadOrder(orderCode, tracking: true);
        if (order is null)
        {
            return new UpdateOrderStatusResult(false, null);
        }

        if (status == OrderStatus.Cancelled && IsCancellationLocked(order))
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "ORDER_CANCEL_NOT_ALLOWED");
        }

        if (!CanTransition(order.Status, status))
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "ORDER_STATUS_TRANSITION_INVALID");
        }

        // An order can't be marked Completed until its payment is actually settled.
        if (status == OrderStatus.Completed
            && order.Payment?.Status is not (PaymentStatus.Confirmed or PaymentStatus.Paid))
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "ORDER_COMPLETE_REQUIRES_PAYMENT");
        }

        var now = DateTimeOffset.UtcNow;
        order.Status = status;
        order.UpdatedAt = now;

        try
        {
            db.SaveChanges();
        }
        catch (DbUpdateConcurrencyException)
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "CONFLICT_STALE");
        }

        return new UpdateOrderStatusResult(
            true,
            ToSnapshot(order, [new OrderStatusEventSnapshot(order.Status.ToString(), now)]));
    }

    public UpdateOrderItemStatusResult UpdateOrderItemStatus(string orderCode, string orderItemId, OrderItemStatus status)
    {
        var order = LoadOrder(orderCode, tracking: true);
        if (order is null)
        {
            return new UpdateOrderItemStatusResult(false, false, null, null);
        }

        var item = order.OrderItems.FirstOrDefault(item =>
            item.Id.Equals(orderItemId, StringComparison.OrdinalIgnoreCase));

        if (item is null)
        {
            return new UpdateOrderItemStatusResult(true, false, ToSnapshot(order), null);
        }

        var now = DateTimeOffset.UtcNow;
        item.Status = status;
        item.UpdatedAt = now;
        order.UpdatedAt = now;
        db.SaveChanges();

        var orderSnapshot = ToSnapshot(order);
        var itemSnapshot = orderSnapshot.Items.First(snapshot =>
            snapshot.OrderItemId.Equals(item.Id, StringComparison.OrdinalIgnoreCase));

        return new UpdateOrderItemStatusResult(true, true, orderSnapshot, itemSnapshot);
    }

    private Dictionary<string, MenuItem> LoadMenuItems(CreateOrderCommand command)
    {
        var menuItemIds = command.Items
            .Select(item => item.MenuItemId!.Trim())
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();

        return db.MenuItems
            .Where(menuItem => menuItemIds.Contains(menuItem.Id))
            .ToList()
            .ToDictionary(menuItem => menuItem.Id, StringComparer.OrdinalIgnoreCase);
    }

    private Order? LoadOrder(string orderCode, bool tracking)
    {
        var normalizedOrderCode = orderCode.Trim();
        var query = db.Orders
            .Include(order => order.Payment)
            .Include(order => order.OrderItems)
            .Include(order => order.RestaurantTable)
            .Where(order => order.OrderCode == normalizedOrderCode);

        if (!tracking)
        {
            query = query.AsNoTracking();
        }

        return query.FirstOrDefault();
    }

    private static string GenerateAccessToken()
    {
        return Convert.ToBase64String(RandomNumberGenerator.GetBytes(32))
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');
    }

    private string CreateNextOrderCode()
    {
        return $"ORD-{db.NextOrderCodeNumber()}";
    }

    private static bool CanTransition(OrderStatus current, OrderStatus next)
    {
        if (current == next)
        {
            return true;
        }

        if (next == OrderStatus.Cancelled)
        {
            return current is OrderStatus.Draft or OrderStatus.Placed or OrderStatus.Confirmed;
        }

        return current switch
        {
            OrderStatus.Draft => next is OrderStatus.Placed,
            OrderStatus.Placed => next is OrderStatus.Confirmed or OrderStatus.Preparing,
            OrderStatus.Confirmed => next is OrderStatus.Preparing,
            OrderStatus.Preparing => next is OrderStatus.Ready,
            OrderStatus.Ready => next is OrderStatus.Served or OrderStatus.Completed,
            OrderStatus.Served => next is OrderStatus.Completed,
            OrderStatus.Delivering => next is OrderStatus.Delivered,
            OrderStatus.Delivered => next is OrderStatus.Completed,
            _ => false
        };
    }

    private static bool IsCancellationLocked(Order order)
    {
        return order.Status is OrderStatus.Preparing
                or OrderStatus.Ready
                or OrderStatus.Served
                or OrderStatus.Delivering
                or OrderStatus.Delivered
                or OrderStatus.Completed
            || order.OrderItems.Any(item => item.Status is OrderItemStatus.Preparing
                or OrderItemStatus.Ready
                or OrderItemStatus.Served);
    }

    private static OrderSnapshot ToSnapshot(
        Order order,
        IReadOnlyList<OrderStatusEventSnapshot>? events = null)
    {
        var payment = order.Payment ?? new Payment();
        return new OrderSnapshot(
            order.Id,
            order.OrderCode,
            order.OrderType.ToString(),
            order.TableCode,
            order.Status.ToString(),
            payment.Status.ToString(),
            payment.Method.ToString(),
            ToDeliveryInfoSnapshot(order),
            order.SubtotalAmount,
            order.TotalAmount,
            order.CreatedAt,
            order.UpdatedAt,
            order.OrderItems
                .OrderBy(item => item.CreatedAt)
                .Select(ToItemSnapshot)
                .ToList(),
            events ?? [new OrderStatusEventSnapshot(order.Status.ToString(), order.UpdatedAt)],
            order.CustomerAccessToken);
    }

    private static OrderItemSnapshot ToItemSnapshot(OrderItem item)
    {
        return new OrderItemSnapshot(
            item.Id,
            item.MenuItemId,
            item.MenuItemName,
            item.UnitPrice,
            item.Quantity,
            item.Status.ToString(),
            item.UnitPrice * item.Quantity,
            item.UpdatedAt);
    }

    private static DeliveryInfoSnapshot? ToDeliveryInfoSnapshot(Order order)
    {
        if (string.IsNullOrWhiteSpace(order.DeliveryRecipientName)
            || string.IsNullOrWhiteSpace(order.DeliveryPhoneNumber)
            || string.IsNullOrWhiteSpace(order.DeliveryAddress))
        {
            return null;
        }

        return new DeliveryInfoSnapshot(
            order.DeliveryRecipientName,
            order.DeliveryPhoneNumber,
            order.DeliveryAddress,
            order.DeliveryNote);
    }

    private static void ApplyDeliveryInfo(Order order, DeliveryInfoRequest? deliveryInfo)
    {
        if (deliveryInfo is null)
        {
            return;
        }

        order.DeliveryRecipientName = deliveryInfo.RecipientName?.Trim();
        order.DeliveryPhoneNumber = deliveryInfo.PhoneNumber?.Trim();
        order.DeliveryAddress = deliveryInfo.Address?.Trim();
        order.DeliveryNote = NormalizeOptional(deliveryInfo.Note);
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
