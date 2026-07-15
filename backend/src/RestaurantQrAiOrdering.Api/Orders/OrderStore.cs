using System.Security.Cryptography;
using System.Data;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Orders;

public interface IOrderStore
{
    OrderSnapshot CreateOrder(CreateOrderCommand command, ActorContext actor);

    OrderSnapshot? GetOrder(string orderCode);

    IdempotentOrderSnapshot? GetOrderByIdempotencyKey(string idempotencyKey);

    UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status, ActorContext actor);

    UpdateOrderItemStatusResult UpdateOrderItemStatus(
        string orderCode,
        string orderItemId,
        OrderItemStatus status,
        ActorContext actor);

    void RecordPaymentStatusEvent(Order order, ActorContext actor, string note);

    IReadOnlyList<OrderSnapshot> StageTableSessionCompletion(
        string tableSessionId,
        ActorContext actor,
        DateTimeOffset now);
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
        var executionStrategy = db.Database.CreateExecutionStrategy();
        return executionStrategy.Execute(() => CreateOrderAttempt(command, actor));
    }

    private OrderSnapshot CreateOrderAttempt(CreateOrderCommand command, ActorContext actor)
    {
        // A retry can reuse this scoped DbContext after an unknown commit result. Clear
        // tracked state and replay by idempotency key before opening a new transaction.
        db.ChangeTracker.Clear();
        var existing = GetOrderByIdempotencyKey(command.IdempotencyKey);
        if (existing is not null)
        {
            if (existing.RequestFingerprint != command.RequestFingerprint)
            {
                throw new IdempotencyKeyReuseException();
            }

            return existing.Order;
        }

        using var transaction = db.Database.IsRelational()
            ? db.Database.BeginTransaction(IsolationLevel.Serializable)
            : null;
        var now = DateTimeOffset.UtcNow;
        var orderType = Enum.Parse<OrderType>(command.OrderType);
        var tableCode = NormalizeOptional(command.TableCode)?.ToUpperInvariant();
        var qrToken = NormalizeOptional(command.QrToken);
        var tableSessionId = NormalizeOptional(command.TableSessionId);
        // Resolve the table from the scanned QR token, not the client-supplied table code:
        // endpoint validation already proved this token maps to this active table.
        var table = qrToken is not null
            ? db.RestaurantTables.FirstOrDefault(t => t.QrToken == qrToken && t.IsActive)
            : null;
        if (orderType == OrderType.DineIn && table is null)
        {
            throw new TableSessionUnavailableException(
                "TABLE_SESSION_INVALID",
                "The table session is no longer valid. Please scan QR again.",
                StatusCodes.Status409Conflict);
        }

        var menuItems = LoadMenuItems(command);
        var tableSession = ResolveTableSession(tableSessionId, table, now);
        if (orderType == OrderType.DineIn && tableSession is null)
        {
            throw new TableSessionUnavailableException(
                "TABLE_SESSION_EXPIRED",
                "Table session has expired. Please scan QR again.",
                StatusCodes.Status410Gone);
        }
        if (tableSession is not null)
        {
            // Touch the shared session row so order creation and settlement start cannot both commit.
            tableSession.UpdatedAt = now;
        }

        var order = new Order
        {
            Id = $"ord_{Guid.NewGuid():N}",
            OrderCode = CreateNextOrderCode(),
            CustomerAccessToken = GenerateAccessToken(),
            IdempotencyKey = command.IdempotencyKey,
            RequestFingerprint = command.RequestFingerprint,
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
                Method = PaymentMethod.Unselected,
                Status = PaymentStatus.NotRequested,
                CreatedAt = now,
                UpdatedAt = now
            }
        };

        foreach (var requestItem in command.Items)
        {
            // Endpoint validation already checked availability, but a menu item can be
            // deactivated or deleted in the gap before we load it here. Fail with a typed
            // domain error instead of a raw KeyNotFoundException (HTTP 500).
            if (!menuItems.TryGetValue(requestItem.MenuItemId!.Trim(), out var menuItem))
            {
                throw new MenuItemUnavailableException(requestItem.MenuItemId!.Trim());
            }

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
        var discount = Math.Clamp(command.DiscountAmount, 0m, order.SubtotalAmount);
        order.DiscountAmount = discount;
        order.TotalAmount = order.SubtotalAmount - discount;
        order.PromotionId = discount > 0 ? command.PromotionId : null;
        order.PromotionCode = discount > 0 ? command.PromotionCode : null;
        order.CustomerPhoneNumber = NormalizeOptional(command.CustomerPhoneNumber);
        order.Payment.Amount = order.TotalAmount;

        AppendStatusHistory(order, fromStatus: null, order.Status, OrderStatusChangeSource.Status, actor, note: null, now);

        db.Orders.Add(order);
        db.SaveChanges();
        transaction?.Commit();

        return ToSnapshot(order);
    }

    public OrderSnapshot? GetOrder(string orderCode)
    {
        var order = LoadOrder(orderCode, tracking: false);
        return order is null ? null : ToSnapshot(order);
    }

    public IdempotentOrderSnapshot? GetOrderByIdempotencyKey(string idempotencyKey)
    {
        var normalizedKey = idempotencyKey.Trim();
        var order = db.Orders
            .AsNoTracking()
            .Include(item => item.Payment)
            .Include(item => item.OrderItems)
            .Include(item => item.RestaurantTable)
            .Include(item => item.StatusHistory)
            .FirstOrDefault(item => item.IdempotencyKey == normalizedKey);

        if (order is null || string.IsNullOrWhiteSpace(order.RequestFingerprint))
        {
            return null;
        }

        return new IdempotentOrderSnapshot(ToCreationSnapshot(order), order.RequestFingerprint);
    }

    public UpdateOrderStatusResult UpdateOrderStatus(string orderCode, OrderStatus status, ActorContext actor)
    {
        var order = LoadOrder(orderCode, tracking: true);
        if (order is null)
        {
            return new UpdateOrderStatusResult(false, null);
        }
        if (status == OrderStatus.Cancelled && order.TableSession?.Invoice?.Status == PaymentStatus.Pending)
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "TABLE_INVOICE_PAYMENT_PENDING");
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

        // Cancelling an order cancels its still-pending items so item state never
        // contradicts the order state. (Cancellation is blocked once any item has
        // progressed past Pending, so only Pending items remain to cascade.)
        if (status == OrderStatus.Cancelled)
        {
            CancelPendingItems(order, now);
        }

        // Serving from the board is a single atomic transition: the order and every
        // non-cancelled item must agree before the update is committed.
        if (status == OrderStatus.Served)
        {
            ServeActiveItems(order, now);
        }

        // Stage the table-session close in the same unit of work as the status change so
        // a completed order and its closed session commit (or roll back) atomically.
        if (status == OrderStatus.Completed && order.TableSessionId is not null)
        {
            CloseTableSessionIfLastActiveOrder(order, now);
        }

        try
        {
            db.SaveChanges();
        }
        catch (DbUpdateConcurrencyException)
        {
            return new UpdateOrderStatusResult(true, ToSnapshot(order), "CONFLICT_STALE");
        }

        return new UpdateOrderStatusResult(true, ToSnapshot(order));
    }

    public UpdateOrderItemStatusResult UpdateOrderItemStatus(
        string orderCode,
        string orderItemId,
        OrderItemStatus status,
        ActorContext actor)
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

        if (status == OrderItemStatus.Cancelled && order.TableSession?.Invoice?.Status == PaymentStatus.Pending)
        {
            return new UpdateOrderItemStatusResult(
                true, true, ToSnapshot(order), null, "TABLE_INVOICE_PAYMENT_PENDING");
        }

        if (order.Status is OrderStatus.Completed or OrderStatus.Cancelled)
        {
            return new UpdateOrderItemStatusResult(
                true,
                true,
                ToSnapshot(order),
                null,
                "ORDER_STATUS_TERMINAL");
        }

        if (!CanTransitionItem(item.Status, status))
        {
            return new UpdateOrderItemStatusResult(
                true, true, ToSnapshot(order), null, "ORDER_ITEM_STATUS_TRANSITION_INVALID");
        }

        var now = DateTimeOffset.UtcNow;
        var previousOrderStatus = order.Status;
        item.Status = status;
        item.UpdatedAt = now;
        var aggregateStatus = DeriveAggregateKitchenStatus(order);
        if (aggregateStatus != order.Status)
        {
            order.Status = aggregateStatus;
            AppendStatusHistory(
                order,
                previousOrderStatus,
                aggregateStatus,
                OrderStatusChangeSource.Status,
                actor,
                note: null,
                now);
        }
        order.UpdatedAt = now;

        try
        {
            db.SaveChanges();
        }
        catch (DbUpdateConcurrencyException)
        {
            return new UpdateOrderItemStatusResult(true, true, ToSnapshot(order), null, "CONFLICT_STALE");
        }

        var orderSnapshot = ToSnapshot(order);
        var itemSnapshot = orderSnapshot.Items.First(snapshot =>
            snapshot.OrderItemId.Equals(item.Id, StringComparison.OrdinalIgnoreCase));

        return new UpdateOrderItemStatusResult(
            true,
            true,
            orderSnapshot,
            itemSnapshot,
            OrderStatusChanged: previousOrderStatus != order.Status);
    }

    public IReadOnlyList<OrderSnapshot> StageTableSessionCompletion(
        string tableSessionId,
        ActorContext actor,
        DateTimeOffset now)
    {
        var orders = db.Orders
            .Include(order => order.Payment)
            .Include(order => order.OrderItems)
            .Include(order => order.RestaurantTable)
            .Include(order => order.StatusHistory)
            .Where(order => order.TableSessionId == tableSessionId &&
                order.Status != OrderStatus.Completed &&
                order.Status != OrderStatus.Cancelled)
            .ToList();
        foreach (var order in orders)
        {
            var previousStatus = order.Status;
            order.Status = OrderStatus.Completed;
            order.UpdatedAt = now;
            AppendStatusHistory(
                order,
                previousStatus,
                OrderStatus.Completed,
                OrderStatusChangeSource.Status,
                actor,
                "Table invoice payment confirmed.",
                now);
        }
        return orders.Select(ToSnapshot).ToArray();
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
            .Include(order => order.TableSession)!
                .ThenInclude(session => session!.Invoice)
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

    // Dine-in orders attach only to the open session created by scanning the table QR.
    // Do not create a session here; order creation must not bypass the physical QR step.
    private TableSession? ResolveTableSession(string? tableSessionId, RestaurantTable? table, DateTimeOffset now)
    {
        if (table is null || string.IsNullOrWhiteSpace(tableSessionId))
        {
            return null;
        }

        return db.TableSessions.FirstOrDefault(session =>
            session.Id == tableSessionId
            &&
            session.RestaurantTableId == table.Id
            && session.Status == TableSessionStatus.Open
            && session.ExpiresAt > now);
    }

    // Once an order completes, close its table session unless another order on the same
    // session is still active (so a shared seating stays open until everyone is done).
    // Mutations are staged on tracked entities; the caller's SaveChanges commits them
    // together with the order status change.
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

        var chatSessions = db.ChatSessions
            .Where(chatSession => chatSession.TableSessionId == session.Id)
            .ToList();

        if (chatSessions.Count > 0)
        {
            db.ChatSessions.RemoveRange(chatSessions);
        }
    }

    // No-op transitions (current == next) return false: re-sending the same status is
    // rejected so we don't append duplicate history rows or emit spurious events.
    private static bool CanTransition(OrderStatus current, OrderStatus next)
    {
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

    // Items move forward only (skips like Pending -> Ready are allowed for fast kitchens).
    // Backward moves, no-ops, and changes out of a terminal state (Served/Cancelled) are
    // rejected. An item can be cancelled while still Pending or Preparing.
    private static bool CanTransitionItem(OrderItemStatus current, OrderItemStatus next)
    {
        if (next == OrderItemStatus.Cancelled)
        {
            return current is OrderItemStatus.Pending or OrderItemStatus.Preparing;
        }

        return current switch
        {
            OrderItemStatus.Pending => next is OrderItemStatus.Preparing
                or OrderItemStatus.Ready
                or OrderItemStatus.Served,
            OrderItemStatus.Preparing => next is OrderItemStatus.Ready or OrderItemStatus.Served,
            OrderItemStatus.Ready => next is OrderItemStatus.Served,
            _ => false
        };
    }

    private static OrderStatus DeriveAggregateKitchenStatus(Order order)
    {
        var activeItems = order.OrderItems
            .Where(item => item.Status != OrderItemStatus.Cancelled)
            .ToList();

        if (activeItems.Count == 0)
        {
            return order.Status;
        }

        if (order.Status is OrderStatus.Placed or OrderStatus.Confirmed or OrderStatus.Preparing
            && activeItems.All(item => item.Status is OrderItemStatus.Ready or OrderItemStatus.Served))
        {
            return OrderStatus.Ready;
        }

        if (order.Status == OrderStatus.Ready
            && activeItems.All(item => item.Status == OrderItemStatus.Served))
        {
            return OrderStatus.Served;
        }

        if (order.Status is OrderStatus.Placed or OrderStatus.Confirmed
            && activeItems.Any(item => item.Status is OrderItemStatus.Preparing
                or OrderItemStatus.Ready
                or OrderItemStatus.Served))
        {
            return OrderStatus.Preparing;
        }

        return order.Status;
    }

    private static void CancelPendingItems(Order order, DateTimeOffset now)
    {
        foreach (var item in order.OrderItems)
        {
            if (item.Status == OrderItemStatus.Pending)
            {
                item.Status = OrderItemStatus.Cancelled;
                item.UpdatedAt = now;
            }
        }
    }

    private static void ServeActiveItems(Order order, DateTimeOffset now)
    {
        foreach (var item in order.OrderItems)
        {
            if (item.Status != OrderItemStatus.Cancelled)
            {
                item.Status = OrderItemStatus.Served;
                item.UpdatedAt = now;
            }
        }
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
            order.SubtotalAmount,
            order.DiscountAmount,
            order.TotalAmount,
            order.PromotionCode,
            order.CreatedAt,
            order.UpdatedAt,
            order.OrderItems
                .OrderBy(item => item.CreatedAt)
                .Select(ToItemSnapshot)
                .ToList(),
            ToStatusEvents(order),
            order.CustomerAccessToken);
    }

    private static OrderSnapshot ToCreationSnapshot(Order order)
    {
        return new OrderSnapshot(
            order.Id,
            order.OrderCode,
            order.OrderType.ToString(),
            order.TableCode,
            order.TableSessionId,
            OrderStatus.Placed.ToString(),
            PaymentStatus.NotRequested.ToString(),
            PaymentMethod.Unselected.ToString(),
            order.SubtotalAmount,
            order.DiscountAmount,
            order.TotalAmount,
            order.PromotionCode,
            order.CreatedAt,
            order.CreatedAt,
            order.OrderItems
                .OrderBy(item => item.CreatedAt)
                .Select(item => new OrderItemSnapshot(
                    item.Id,
                    item.MenuItemId,
                    item.MenuItemName,
                    item.UnitPrice,
                    item.Quantity,
                    OrderItemStatus.Pending.ToString(),
                    item.UnitPrice * item.Quantity,
                    item.CreatedAt))
                .ToList(),
            order.StatusHistory
                .OrderBy(history => history.CreatedAt)
                .ThenBy(history => history.Id)
                .Take(1)
                .Select(history => new OrderStatusEventSnapshot(
                    history.ToStatus.ToString(),
                    history.Source.ToString(),
                    history.ChangedByRole,
                    history.Note,
                    history.CreatedAt))
                .ToList(),
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

    private static string? NormalizeOptional(string? value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}

// Raised when a menu item passes endpoint validation but is gone by the time the order is
// built (deactivated/deleted in the gap). Mapped to MENU_ITEM_UNAVAILABLE by the endpoint.
public sealed class MenuItemUnavailableException : Exception
{
    public MenuItemUnavailableException(string menuItemId)
        : base($"Menu item '{menuItemId}' is no longer available.")
    {
        MenuItemId = menuItemId;
    }

    public string MenuItemId { get; }
}

public sealed class TableSessionUnavailableException : Exception
{
    public TableSessionUnavailableException(string errorCode, string message, int statusCode)
        : base(message)
    {
        ErrorCode = errorCode;
        StatusCode = statusCode;
    }

    public string ErrorCode { get; }

    public int StatusCode { get; }
}

public sealed class IdempotencyKeyReuseException : Exception
{
    public IdempotencyKeyReuseException()
        : base("Idempotency key was already used with a different request.")
    {
    }
}
