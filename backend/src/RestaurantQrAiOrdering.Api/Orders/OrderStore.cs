using System.Security.Cryptography;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Orders;

public interface IOrderStore
{
    OrderSnapshot CreateOrder(CreateOrderCommand command, ActorContext actor);

    OrderSnapshot? GetOrder(string orderCode);

    UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status, ActorContext actor);

    UpdateOrderItemStatusResult UpdateOrderItemStatus(string orderCode, string orderItemId, OrderItemStatus status);

    void RecordPaymentStatusEvent(Order order, ActorContext actor, string note);
}

public sealed class OrderStore : IOrderStore
{
    private readonly RestaurantDbContext db;

    public OrderStore(RestaurantDbContext db)
    {
        this.db = db;
    }

    public OrderSnapshot CreateOrder(CreateOrderCommand command, ActorContext actor)
    {
        var now = DateTimeOffset.UtcNow;
        var orderType = Enum.Parse<OrderType>(command.OrderType);
        var paymentMethod = Enum.Parse<PaymentMethod>(command.PaymentMethod);
        var tableCode = NormalizeOptional(command.TableCode)?.ToUpperInvariant();
        var table = orderType == OrderType.DineIn && tableCode is not null
            ? db.RestaurantTables.FirstOrDefault(t => t.TableCode == tableCode && t.IsActive)
            : null;
        var menuItems = LoadMenuItems(command);
        var tableSession = ResolveTableSession(orderType, table, now);

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
            TableSessionId = tableSession?.Id,
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

        if (orderType == OrderType.Pickup && command.PickupInfo is not null)
        {
            order.PickupCustomerName = NormalizeOptional(command.PickupInfo.CustomerName);
            order.PickupCustomerPhoneNumber = NormalizeOptional(command.PickupInfo.PhoneNumber);
            order.PickupRequestedAt = now;
        }

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

        AppendStatusHistory(order, fromStatus: null, order.Status, OrderStatusChangeSource.Status, actor, note: null, now);

        db.Orders.Add(order);
        db.SaveChanges();

        return ToSnapshot(order);
    }

    public OrderSnapshot? GetOrder(string orderCode)
    {
        var order = LoadOrder(orderCode, tracking: false);
        return order is null ? null : ToSnapshot(order);
    }

    public UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status, ActorContext actor)
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
        var fromStatus = order.Status;
        order.Status = status;
        order.UpdatedAt = now;
        AppendStatusHistory(order, fromStatus, status, OrderStatusChangeSource.Status, actor, note: null, now);

        try
        {
            db.SaveChanges();
        }
        catch (DbUpdateConcurrencyException)
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "CONFLICT_STALE");
        }

        if (status == OrderStatus.Completed && order.TableSessionId is not null)
        {
            CloseTableSessionIfLastActiveOrder(order, now);
        }

        return new UpdateOrderStatusResult(true, ToSnapshot(order));
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

    // Records a payment confirm/fail as a timeline marker on the order's status history.
    // The order status itself is unchanged; payment_transactions stays the source of truth
    // for money. Appends to the tracked order; the caller's SaveChanges persists it.
    public void RecordPaymentStatusEvent(Order order, ActorContext actor, string note)
    {
        AppendStatusHistory(
            order,
            order.Status,
            order.Status,
            OrderStatusChangeSource.Payment,
            actor,
            note,
            DateTimeOffset.UtcNow);
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
            .Include(order => order.StatusHistory)
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

    // Dine-in orders attach to the table's open, non-expired session (opening one if
    // none exists) so all orders for a seating share a session. Pickup gets no session.
    private TableSession? ResolveTableSession(OrderType orderType, RestaurantTable? table, DateTimeOffset now)
    {
        if (orderType != OrderType.DineIn || table is null)
        {
            return null;
        }

        var session = db.TableSessions.FirstOrDefault(session =>
            session.RestaurantTableId == table.Id
            && session.Status == TableSessionStatus.Open
            && session.ExpiresAt > now);

        if (session is not null)
        {
            return session;
        }

        session = new TableSession
        {
            Id = $"tsx_{Guid.NewGuid():N}",
            RestaurantTableId = table.Id,
            TableCode = table.TableCode,
            QrToken = table.QrToken,
            OrderType = OrderType.DineIn,
            Status = TableSessionStatus.Open,
            OpenedAt = now,
            ExpiresAt = now.AddHours(4),
            CreatedAt = now,
            UpdatedAt = now
        };
        db.TableSessions.Add(session);
        return session;
    }

    // Once an order completes, close its table session unless another order on the same
    // session is still active (so a shared seating stays open until everyone is done).
    private void CloseTableSessionIfLastActiveOrder(Order order, DateTimeOffset now)
    {
        var hasOtherActiveOrder = db.Orders.Any(other =>
            other.TableSessionId == order.TableSessionId
            && other.Id != order.Id
            && other.Status != OrderStatus.Completed
            && other.Status != OrderStatus.Cancelled);

        if (hasOtherActiveOrder)
        {
            return;
        }

        var session = db.TableSessions.FirstOrDefault(session => session.Id == order.TableSessionId);
        if (session is null || session.Status != TableSessionStatus.Open)
        {
            return;
        }

        session.Status = TableSessionStatus.Closed;
        session.ClosedAt = now;
        session.UpdatedAt = now;
        db.SaveChanges();
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
            _ => false
        };
    }

    private static bool IsCancellationLocked(Order order)
    {
        return order.Status is OrderStatus.Preparing
                or OrderStatus.Ready
                or OrderStatus.Served
                or OrderStatus.Completed
            || order.OrderItems.Any(item => item.Status is OrderItemStatus.Preparing
                or OrderItemStatus.Ready
                or OrderItemStatus.Served);
    }

    private static OrderSnapshot ToSnapshot(Order order)
    {
        var payment = order.Payment ?? new Payment();
        return new OrderSnapshot(
            order.Id,
            order.OrderCode,
            order.OrderType.ToString(),
            order.TableCode,
            order.TableSessionId,
            order.Status.ToString(),
            payment.Status.ToString(),
            payment.Method.ToString(),
            ToPickupInfoSnapshot(order),
            order.SubtotalAmount,
            order.TotalAmount,
            order.CreatedAt,
            order.UpdatedAt,
            order.OrderItems
                .OrderBy(item => item.CreatedAt)
                .Select(ToItemSnapshot)
                .ToList(),
            ToStatusEvents(order),
            order.CustomerAccessToken);
    }

    private static IReadOnlyList<OrderStatusEventSnapshot> ToStatusEvents(Order order)
    {
        return order.StatusHistory
            .OrderBy(history => history.CreatedAt)
            .ThenBy(history => history.Id)
            .Select(history => new OrderStatusEventSnapshot(
                history.ToStatus.ToString(),
                history.Source.ToString(),
                history.ChangedByRole,
                history.Note,
                history.CreatedAt))
            .ToList();
    }

    private static void AppendStatusHistory(
        Order order,
        OrderStatus? fromStatus,
        OrderStatus toStatus,
        OrderStatusChangeSource source,
        ActorContext actor,
        string? note,
        DateTimeOffset now)
    {
        order.StatusHistory.Add(new OrderStatusHistory
        {
            Id = $"osh_{Guid.NewGuid():N}",
            OrderId = order.Id,
            FromStatus = fromStatus,
            ToStatus = toStatus,
            Source = source,
            ChangedByUserId = actor.UserId,
            ChangedByRole = actor.Role,
            Note = note,
            CreatedAt = now
        });
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

    private static PickupInfoSnapshot? ToPickupInfoSnapshot(Order order)
    {
        if (string.IsNullOrWhiteSpace(order.PickupCustomerName)
            || string.IsNullOrWhiteSpace(order.PickupCustomerPhoneNumber))
        {
            return null;
        }

        return new PickupInfoSnapshot(
            order.PickupCustomerName,
            order.PickupCustomerPhoneNumber,
            order.PickupRequestedAt);
    }

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
