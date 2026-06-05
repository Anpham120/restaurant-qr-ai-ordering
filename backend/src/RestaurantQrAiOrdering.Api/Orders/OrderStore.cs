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
    private readonly object syncRoot = new();
    private readonly RestaurantDataStore restaurantData;
    private readonly List<Order> orders = [];
    private readonly Dictionary<string, List<OrderStatusEventSnapshot>> orderEvents = new(StringComparer.OrdinalIgnoreCase);
    private int nextOrderNumber = 1001;
    private int nextOrderItemNumber = 1;

    public OrderStore(RestaurantDataStore restaurantData)
    {
        this.restaurantData = restaurantData;
    }

    public OrderSnapshot CreateOrder(CreateOrderCommand command)
    {
        lock (syncRoot)
        {
            var now = DateTimeOffset.UtcNow;
            var orderNumber = nextOrderNumber++;
            var order = new Order
            {
                Id = $"ord_{orderNumber}",
                OrderCode = $"ORD-{orderNumber}",
                OrderType = Enum.Parse<OrderType>(command.OrderType),
                Status = OrderStatus.Placed,
                TableCode = NormalizeOptional(command.TableCode),
                CreatedAt = now,
                UpdatedAt = now,
                Payment = new Payment
                {
                    Id = $"pay_{orderNumber}",
                    Method = Enum.Parse<PaymentMethod>(command.PaymentMethod),
                    Status = PaymentStatus.Unpaid,
                    CreatedAt = now,
                    UpdatedAt = now
                }
            };

            ApplyDeliveryInfo(order, command.DeliveryInfo);

            foreach (var requestItem in command.Items)
            {
                var menuItem = restaurantData.GetMenuItem(requestItem.MenuItemId!);
                var orderItem = new OrderItem
                {
                    Id = $"oi_{nextOrderItemNumber++:000}",
                    OrderId = order.Id,
                    MenuItemId = menuItem!.Id,
                    MenuItemName = menuItem.Name,
                    UnitPrice = menuItem.Price,
                    Quantity = requestItem.Quantity,
                    Status = OrderItemStatus.Pending,
                    CreatedAt = now,
                    UpdatedAt = now
                };

                order.OrderItems.Add(orderItem);
            }

            order.SubtotalAmount = order.OrderItems.Sum(item => item.UnitPrice * item.Quantity);
            order.TotalAmount = order.SubtotalAmount + order.MockDeliveryFee;
            order.Payment.Amount = order.TotalAmount;
            orderEvents[order.OrderCode] = [new OrderStatusEventSnapshot(order.Status.ToString(), now)];
            orders.Add(order);

            return ToSnapshot(order);
        }
    }

    public OrderSnapshot? GetOrder(string orderCode)
    {
        lock (syncRoot)
        {
            var order = FindOrder(orderCode);
            return order is null ? null : ToSnapshot(order);
        }
    }

    public UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status)
    {
        lock (syncRoot)
        {
            var order = FindOrder(orderCode);
            if (order is null)
            {
                return new UpdateOrderStatusResult(false, null);
            }

            var now = DateTimeOffset.UtcNow;
            order.Status = status;
            order.UpdatedAt = now;
            orderEvents[order.OrderCode].Add(new OrderStatusEventSnapshot(status.ToString(), now));

            return new UpdateOrderStatusResult(true, ToSnapshot(order));
        }
    }

    public UpdateOrderItemStatusResult UpdateOrderItemStatus(string orderCode, string orderItemId, OrderItemStatus status)
    {
        lock (syncRoot)
        {
            var order = FindOrder(orderCode);
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

            var orderSnapshot = ToSnapshot(order);
            var itemSnapshot = orderSnapshot.Items.First(snapshot =>
                snapshot.OrderItemId.Equals(item.Id, StringComparison.OrdinalIgnoreCase));

            return new UpdateOrderItemStatusResult(true, true, orderSnapshot, itemSnapshot);
        }
    }

    private Order? FindOrder(string orderCode)
    {
        return orders.FirstOrDefault(order =>
            order.OrderCode.Equals(orderCode.Trim(), StringComparison.OrdinalIgnoreCase));
    }

    private OrderSnapshot ToSnapshot(Order order)
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
                .OrderBy(item => item.Id, StringComparer.OrdinalIgnoreCase)
                .Select(ToItemSnapshot)
                .ToList(),
            orderEvents.GetValueOrDefault(order.OrderCode, []).ToList());
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
