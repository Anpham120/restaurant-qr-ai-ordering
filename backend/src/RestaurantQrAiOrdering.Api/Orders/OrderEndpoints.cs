using System.Security.Claims;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Orders;

public static partial class OrderEndpoints
{
    private const int MaxItemLinesPerOrder = 50;
    private const int MaxQuantityPerItem = 99;

    public static IEndpointRouteBuilder MapOrderEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/orders", async (
            CreateOrderRequest? request,
            RestaurantDbContext db,
            IOrderStore orders,
            ClaimsPrincipal user,
            IOrderRealtimeNotifier realtime,
            ILoggerFactory loggerFactory,
            CancellationToken cancellationToken) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Orders.OrderEndpoints");
            var validationError = await ValidateCreateOrderRequestAsync(request, db, cancellationToken);
            if (validationError is not null)
            {
                logger.LogWarning("Rejected order creation request during validation.");
                return validationError;
            }

            var validatedRequest = request!;
            OrderSnapshot order;
            try
            {
                order = orders.CreateOrder(
                    new CreateOrderCommand(
                        validatedRequest.OrderType!.Trim(),
                        validatedRequest.TableCode?.Trim().ToUpperInvariant(),
                        validatedRequest.QrToken?.Trim(),
                        validatedRequest.TableSessionId?.Trim(),
                        validatedRequest.PaymentMethod!.Trim(),
                        validatedRequest.Items!),
                    ActorContext.FromPrincipal(user));
            }
            catch (MenuItemUnavailableException ex)
            {
                logger.LogWarning("Rejected order creation because menu item {MenuItemId} became unavailable.", ex.MenuItemId);
                return ApiResults.BadRequest("MENU_ITEM_UNAVAILABLE", "Menu item is unavailable.");
            }

            await realtime.OrderCreatedAsync(ToOrderCreatedEvent(order), cancellationToken);
            logger.LogInformation(
                "Created order {OrderCode} with {ItemCount} items for order type {OrderType}.",
                order.OrderCode,
                order.Items.Count,
                order.OrderType);

            return Results.Created($"/api/orders/{order.OrderCode}", ToResponse(order));
        })
        .WithName("CreateOrder")
        .WithTags("Orders");

        app.MapGet("/api/orders/{orderCode}", (string orderCode, IOrderStore orders, HttpContext http) =>
        {
            var order = orders.GetOrder(orderCode);
            return order is null || !OrderAccessGuard.CanRead(http, order.CustomerAccessToken)
                ? ApiResults.NotFound("ORDER_NOT_FOUND", "Order was not found.")
                : Results.Ok(ToResponse(order));
        })
        .WithName("GetOrder")
        .WithTags("Orders");

        app.MapGet("/api/orders", async (
            string? status,
            string? tableCode,
            DateTimeOffset? updatedSince,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var query = db.Orders
                .AsNoTracking()
                .Include(order => order.Payment)
                .Include(order => order.OrderItems)
                .Include(order => order.RestaurantTable)
                .Include(order => order.StatusHistory)
                .AsQueryable();

            if (!string.IsNullOrWhiteSpace(status))
            {
                if (!TryParseEnum<OrderStatus>(status, out var parsedStatus))
                {
                    return ApiResults.BadRequest("ORDER_STATUS_INVALID", "Order status is invalid.");
                }

                query = query.Where(order => order.Status == parsedStatus);
            }

            if (!string.IsNullOrWhiteSpace(tableCode))
            {
                var normalizedTableCode = tableCode.Trim().ToUpperInvariant();
                query = query.Where(order => order.TableCode == normalizedTableCode);
            }

            if (updatedSince is not null)
            {
                query = query.Where(order => order.UpdatedAt >= updatedSince.Value);
            }

            var orders = await query
                .OrderByDescending(order => order.UpdatedAt)
                .ThenByDescending(order => order.CreatedAt)
                .Take(100)
                .ToListAsync(cancellationToken);

            var response = orders
                .Select(order => ToResponse(order))
                .ToList();

            return Results.Ok(new OrderListResponse(response, response.Count));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Kitchen, UserRole.Staff, UserRole.Admin))
        .WithName("ListOrders")
        .WithTags("Orders");

        app.MapPatch("/api/orders/{orderCode}/status", async (
            string orderCode,
            UpdateOrderStatusRequest? request,
            IOrderStore orders,
            ClaimsPrincipal user,
            IOrderRealtimeNotifier realtime,
            ILoggerFactory loggerFactory,
            CancellationToken cancellationToken) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Orders.OrderEndpoints");
            if (request is null)
            {
                logger.LogWarning("Rejected status update for order {OrderCode} because request body is missing.", orderCode);
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            if (!TryParseEnum<OrderStatus>(request.Status, out var status))
            {
                logger.LogWarning(
                    "Rejected status update for order {OrderCode} because status {Status} is invalid.",
                    orderCode,
                    request.Status);

                return ApiResults.BadRequest("ORDER_STATUS_INVALID", "Order status is invalid.");
            }

            var result = orders.UpdateOrderStatus(orderCode, status, ActorContext.FromPrincipal(user));
            if (!result.IsFound || result.Order is null)
            {
                logger.LogWarning("Rejected status update because order {OrderCode} was not found.", orderCode);
                return ApiResults.NotFound("ORDER_NOT_FOUND", "Order was not found.");
            }

            if (result.ErrorCode == "ORDER_CANCEL_NOT_ALLOWED")
            {
                logger.LogWarning(
                    "Rejected cancellation for order {OrderCode} because the order or an item has reached Preparing.",
                    orderCode);

                return ApiResults.BadRequest(
                    "ORDER_CANCEL_NOT_ALLOWED",
                    "Order cannot be cancelled after it or any item reaches Preparing.");
            }

            if (result.ErrorCode == "ORDER_STATUS_TRANSITION_INVALID")
            {
                logger.LogWarning(
                    "Rejected status update for order {OrderCode} because transition to {Status} is invalid.",
                    orderCode,
                    status);

                return ApiResults.BadRequest(
                    "ORDER_STATUS_TRANSITION_INVALID",
                    "Order status transition is not allowed.");
            }

            if (result.ErrorCode == "ORDER_COMPLETE_REQUIRES_PAYMENT")
            {
                logger.LogWarning(
                    "Rejected completion for order {OrderCode} because its payment is not confirmed.",
                    orderCode);

                return ApiResults.BadRequest(
                    "ORDER_COMPLETE_REQUIRES_PAYMENT",
                    "Order cannot be completed until its payment is confirmed.");
            }

            if (result.ErrorCode == "CONFLICT_STALE")
            {
                logger.LogWarning(
                    "Rejected status update for order {OrderCode} because it was modified by another request.",
                    orderCode);

                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Order was modified by another request. Reload and try again.");
            }

            await realtime.OrderStatusChangedAsync(ToOrderStatusChangedEvent(result.Order), result.Order.TableCode, cancellationToken);
            logger.LogInformation("Updated order {OrderCode} status to {Status}.", result.Order.OrderCode, result.Order.Status);

            return Results.Ok(ToResponse(result.Order));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Kitchen, UserRole.Staff, UserRole.Admin))
        .WithName("UpdateOrderStatus")
        .WithTags("Orders");

        app.MapPatch("/api/orders/{orderCode}/items/{orderItemId}/status", async (
            string orderCode,
            string orderItemId,
            UpdateOrderItemStatusRequest? request,
            IOrderStore orders,
            IOrderRealtimeNotifier realtime,
            ILoggerFactory loggerFactory,
            CancellationToken cancellationToken) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Orders.OrderEndpoints");
            if (request is null)
            {
                logger.LogWarning(
                    "Rejected item status update for order {OrderCode}, item {OrderItemId} because request body is missing.",
                    orderCode,
                    orderItemId);

                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            if (!TryParseEnum<OrderItemStatus>(request.Status, out var status))
            {
                logger.LogWarning(
                    "Rejected item status update for order {OrderCode}, item {OrderItemId} because status {Status} is invalid.",
                    orderCode,
                    orderItemId,
                    request.Status);

                return ApiResults.BadRequest("ORDER_ITEM_STATUS_INVALID", "Order item status is invalid.");
            }

            var result = orders.UpdateOrderItemStatus(orderCode, orderItemId, status);
            if (!result.IsOrderFound || result.Order is null)
            {
                logger.LogWarning("Rejected item status update because order {OrderCode} was not found.", orderCode);
                return ApiResults.NotFound("ORDER_NOT_FOUND", "Order was not found.");
            }

            if (!result.IsItemFound)
            {
                logger.LogWarning(
                    "Rejected item status update because item {OrderItemId} was not found in order {OrderCode}.",
                    orderItemId,
                    orderCode);

                return ApiResults.NotFound("ORDER_ITEM_NOT_FOUND", "Order item was not found.");
            }

            if (result.ErrorCode == "ORDER_ITEM_STATUS_TRANSITION_INVALID")
            {
                logger.LogWarning(
                    "Rejected item status update for order {OrderCode}, item {OrderItemId} because transition to {Status} is invalid.",
                    orderCode,
                    orderItemId,
                    status);

                return ApiResults.BadRequest(
                    "ORDER_ITEM_STATUS_TRANSITION_INVALID",
                    "Order item status transition is not allowed.");
            }

            if (result.ErrorCode == "CONFLICT_STALE")
            {
                logger.LogWarning(
                    "Rejected item status update for order {OrderCode} because it was modified by another request.",
                    orderCode);

                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Order was modified by another request. Reload and try again.");
            }

            if (result.Item is null)
            {
                return ApiResults.NotFound("ORDER_ITEM_NOT_FOUND", "Order item was not found.");
            }

            await realtime.OrderItemStatusChangedAsync(
                ToOrderItemStatusChangedEvent(result.Order, result.Item),
                result.Order.TableCode,
                cancellationToken);
            logger.LogInformation(
                "Updated order {OrderCode} item {OrderItemId} status to {Status}.",
                result.Order.OrderCode,
                result.Item.OrderItemId,
                result.Item.Status);

            return Results.Ok(ToResponse(result.Order));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Kitchen, UserRole.Staff, UserRole.Admin))
        .WithName("UpdateOrderItemStatus")
        .WithTags("Orders");

        return app;
    }

    private static async Task<IResult?> ValidateCreateOrderRequestAsync(
        CreateOrderRequest? request,
        RestaurantDbContext db,
        CancellationToken cancellationToken)
    {
        if (request is null)
        {
            return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

        if (!TryParseEnum<OrderType>(request.OrderType, out var orderType))
        {
            return ApiResults.BadRequest("ORDER_TYPE_INVALID", "Order type is invalid.");
        }

        if (orderType != OrderType.DineIn)
        {
            return ApiResults.BadRequest("ORDER_TYPE_UNSUPPORTED", "Only dine-in QR table orders are supported.");
        }

        if (!TryParseEnum<PaymentMethod>(request.PaymentMethod, out _))
        {
            return ApiResults.BadRequest("PAYMENT_METHOD_INVALID", "Payment method is invalid.");
        }

        if (request.Items is null || request.Items.Count == 0)
        {
            return ApiResults.BadRequest("ORDER_ITEMS_REQUIRED", "Order must contain at least one item.");
        }

        if (request.Items.Count > MaxItemLinesPerOrder)
        {
            return ApiResults.BadRequest(
                "ORDER_ITEMS_TOO_MANY",
                $"Order cannot contain more than {MaxItemLinesPerOrder} item lines.");
        }

        if (request.Items.Any(item => item.Quantity < 1 || item.Quantity > MaxQuantityPerItem))
        {
            return ApiResults.BadRequest(
                "ORDER_ITEM_QUANTITY_INVALID",
                $"Order item quantity must be between 1 and {MaxQuantityPerItem}.");
        }

        var requestedMenuItemIds = request.Items
            .Where(item => !string.IsNullOrWhiteSpace(item.MenuItemId))
            .Select(item => item.MenuItemId!.Trim())
            .ToList();
        if (requestedMenuItemIds.Count != requestedMenuItemIds.Distinct(StringComparer.OrdinalIgnoreCase).Count())
        {
            return ApiResults.BadRequest(
                "ORDER_ITEM_DUPLICATE",
                "Each menu item can appear only once per order; combine quantities instead.");
        }

        if (string.IsNullOrWhiteSpace(request.TableCode))
        {
            return ApiResults.BadRequest("DINE_IN_TABLE_REQUIRED", "Dine-in orders require a table code.");
        }

        if (!TableCodeRegex().IsMatch(request.TableCode))
        {
            return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
        }

        if (string.IsNullOrWhiteSpace(request.QrToken))
        {
            return ApiResults.BadRequest(
                "QR_TOKEN_INVALID",
                "Dine-in orders require the table QR token. Please scan the table QR to order.");
        }

        if (string.IsNullOrWhiteSpace(request.TableSessionId))
        {
            return ApiResults.BadRequest(
                "TABLE_SESSION_REQUIRED",
                "Dine-in orders require an active table session. Please scan the table QR to start ordering.");
        }

        var normalizedTableCode = request.TableCode.Trim().ToUpperInvariant();
        var qrToken = request.QrToken.Trim();
        var tableSessionId = request.TableSessionId.Trim();
        var session = await db.TableSessions
            .Include(tableSession => tableSession.RestaurantTable)
            .AsNoTracking()
            .FirstOrDefaultAsync(tableSession => tableSession.Id == tableSessionId, cancellationToken);

        if (session is null)
        {
            return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found. Please scan QR again.");
        }

        if (session.Status != TableSessionStatus.Open || session.ExpiresAt <= DateTimeOffset.UtcNow)
        {
            return ApiErrorFactory.Result(
                StatusCodes.Status410Gone,
                "TABLE_SESSION_EXPIRED",
                "Table session has expired. Please scan QR again.");
        }

        if (session.OrderType != OrderType.DineIn || session.RestaurantTable is null)
        {
            return ApiResults.BadRequest("TABLE_SESSION_INVALID", "Table session is not valid for dine-in ordering.");
        }

        if (session.TableCode != normalizedTableCode)
        {
            return ApiResults.BadRequest("TABLE_SESSION_TABLE_MISMATCH", "Table session does not match the requested table.");
        }

        if (!string.Equals(session.QrToken, qrToken, StringComparison.Ordinal))
        {
            return ApiResults.BadRequest("QR_TABLE_MISMATCH", "QR token does not match the active table session.");
        }

        foreach (var item in request.Items)
        {
            if (string.IsNullOrWhiteSpace(item.MenuItemId))
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var menuItemId = item.MenuItemId.Trim();
            var menuItem = await db.MenuItems
                .AsNoTracking()
                .FirstOrDefaultAsync(menuItem => menuItem.Id == menuItemId, cancellationToken);
            if (menuItem is null)
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            if (!menuItem.IsAvailable)
            {
                return ApiResults.BadRequest("MENU_ITEM_UNAVAILABLE", "Menu item is unavailable.");
            }
        }

        return null;
    }

    private static bool TryParseEnum<TEnum>(string? value, out TEnum parsed)
        where TEnum : struct
    {
        return Enum.TryParse(value?.Trim(), ignoreCase: false, out parsed);
    }

    private static OrderResponse ToResponse(OrderSnapshot order)
    {
        return new OrderResponse(
            order.OrderId,
            order.OrderCode,
            order.OrderType,
            order.TableCode,
            order.TableSessionId,
            order.Status,
            order.PaymentStatus,
            order.PaymentMethod,
            order.SubtotalAmount,
            order.TotalAmount,
            order.CreatedAt,
            order.UpdatedAt,
            order.Items
                .Select(item => new OrderItemResponse(
                    item.OrderItemId,
                    item.MenuItemId,
                    item.Name,
                    item.UnitPrice,
                    item.Quantity,
                    item.Status,
                    item.LineTotal,
                    item.UpdatedAt))
                .ToList(),
            order.Events
                .Select(item => new OrderStatusEventResponse(
                    item.Status,
                    item.Source,
                    item.ChangedByRole,
                    item.Note,
                    item.CreatedAt))
                .ToList(),
            order.CustomerAccessToken);
    }

    private static OrderResponse ToResponse(Order order)
    {
        var payment = order.Payment;
        return new OrderResponse(
            order.Id,
            order.OrderCode,
            order.OrderType.ToString(),
            order.TableCode,
            order.TableSessionId,
            order.Status.ToString(),
            (payment?.Status ?? PaymentStatus.Unpaid).ToString(),
            (payment?.Method ?? PaymentMethod.COD).ToString(),
            order.SubtotalAmount,
            order.TotalAmount,
            order.CreatedAt,
            order.UpdatedAt,
            order.OrderItems
                .OrderBy(item => item.CreatedAt)
                .Select(item => new OrderItemResponse(
                    item.Id,
                    item.MenuItemId,
                    item.MenuItemName,
                    item.UnitPrice,
                    item.Quantity,
                    item.Status.ToString(),
                    item.UnitPrice * item.Quantity,
                    item.UpdatedAt))
                .ToList(),
            order.StatusHistory
                .OrderBy(history => history.CreatedAt)
                .ThenBy(history => history.Id)
                .Select(history => new OrderStatusEventResponse(
                    history.ToStatus.ToString(),
                    history.Source.ToString(),
                    history.ChangedByRole,
                    history.Note,
                    history.CreatedAt))
                .ToList(),
            // Listing is operators-only; don't bulk-expose per-order customer tokens.
            null);
    }

    private static OrderCreatedEvent ToOrderCreatedEvent(OrderSnapshot order)
    {
        return new OrderCreatedEvent(
            order.OrderId,
            order.OrderCode,
            order.OrderType,
            order.TableCode,
            order.Status,
            order.CreatedAt);
    }

    private static OrderStatusChangedEvent ToOrderStatusChangedEvent(OrderSnapshot order)
    {
        return new OrderStatusChangedEvent(
            order.OrderId,
            order.OrderCode,
            order.Status,
            order.UpdatedAt);
    }

    private static OrderItemStatusChangedEvent ToOrderItemStatusChangedEvent(OrderSnapshot order, OrderItemSnapshot item)
    {
        return new OrderItemStatusChangedEvent(
            order.OrderId,
            order.OrderCode,
            item.OrderItemId,
            item.Name,
            item.Status,
            item.UpdatedAt);
    }

    [GeneratedRegex("^T(0[1-9]|[1-9][0-9])$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex TableCodeRegex();
}
