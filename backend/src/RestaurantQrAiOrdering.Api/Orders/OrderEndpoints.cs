using System.Text.RegularExpressions;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Orders;

public static partial class OrderEndpoints
{
    public static IEndpointRouteBuilder MapOrderEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/orders", async (
            CreateOrderRequest request,
            RestaurantDataStore restaurantData,
            IOrderStore orders,
            IOrderRealtimeNotifier realtime,
            CancellationToken cancellationToken) =>
        {
            var validationError = ValidateCreateOrderRequest(request, restaurantData);
            if (validationError is not null)
            {
                return validationError;
            }

            var order = orders.CreateOrder(new CreateOrderCommand(
                request.OrderType!.Trim(),
                request.TableCode?.Trim().ToUpperInvariant(),
                request.PaymentMethod!.Trim(),
                request.DeliveryInfo,
                request.Items!));

            await realtime.OrderCreatedAsync(ToOrderCreatedEvent(order), cancellationToken);

            return Results.Created($"/api/orders/{order.OrderCode}", ToResponse(order));
        })
        .WithName("CreateOrder")
        .WithTags("Orders");

        app.MapGet("/api/orders/{orderCode}", (string orderCode, IOrderStore orders) =>
        {
            var order = orders.GetOrder(orderCode);
            return order is null
                ? ApiResults.NotFound("ORDER_NOT_FOUND", "Order was not found.")
                : Results.Ok(ToResponse(order));
        })
        .WithName("GetOrder")
        .WithTags("Orders");

        app.MapPatch("/api/orders/{orderCode}/status", async (
            string orderCode,
            UpdateOrderStatusRequest request,
            IOrderStore orders,
            IOrderRealtimeNotifier realtime,
            CancellationToken cancellationToken) =>
        {
            if (!TryParseEnum<OrderStatus>(request.Status, out var status))
            {
                return ApiResults.BadRequest("ORDER_STATUS_INVALID", "Order status is invalid.");
            }

            var result = orders.UpdateOrderStatus(orderCode, status);
            if (!result.IsFound || result.Order is null)
            {
                return ApiResults.NotFound("ORDER_NOT_FOUND", "Order was not found.");
            }

            await realtime.OrderStatusChangedAsync(ToOrderStatusChangedEvent(result.Order), result.Order.TableCode, cancellationToken);

            return Results.Ok(ToResponse(result.Order));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.Admin))
        .WithName("UpdateOrderStatus")
        .WithTags("Orders");

        app.MapPatch("/api/orders/{orderCode}/items/{orderItemId}/status", async (
            string orderCode,
            string orderItemId,
            UpdateOrderItemStatusRequest request,
            IOrderStore orders,
            IOrderRealtimeNotifier realtime,
            CancellationToken cancellationToken) =>
        {
            if (!TryParseEnum<OrderItemStatus>(request.Status, out var status))
            {
                return ApiResults.BadRequest("ORDER_ITEM_STATUS_INVALID", "Order item status is invalid.");
            }

            var result = orders.UpdateOrderItemStatus(orderCode, orderItemId, status);
            if (!result.IsOrderFound || result.Order is null)
            {
                return ApiResults.NotFound("ORDER_NOT_FOUND", "Order was not found.");
            }

            if (!result.IsItemFound || result.Item is null)
            {
                return ApiResults.NotFound("ORDER_ITEM_NOT_FOUND", "Order item was not found.");
            }

            await realtime.OrderItemStatusChangedAsync(
                ToOrderItemStatusChangedEvent(result.Order, result.Item),
                result.Order.TableCode,
                cancellationToken);

            return Results.Ok(ToResponse(result.Order));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Kitchen, UserRole.Staff, UserRole.Admin))
        .WithName("UpdateOrderItemStatus")
        .WithTags("Orders");

        return app;
    }

    private static IResult? ValidateCreateOrderRequest(CreateOrderRequest request, RestaurantDataStore restaurantData)
    {
        if (!TryParseEnum<OrderType>(request.OrderType, out var orderType))
        {
            return ApiResults.BadRequest("ORDER_TYPE_INVALID", "Order type is invalid.");
        }

        if (!TryParseEnum<PaymentMethod>(request.PaymentMethod, out _))
        {
            return ApiResults.BadRequest("PAYMENT_METHOD_INVALID", "Payment method is invalid.");
        }

        if (request.Items is null || request.Items.Count == 0)
        {
            return ApiResults.BadRequest("ORDER_ITEMS_REQUIRED", "Order must contain at least one item.");
        }

        if (request.Items.Any(item => item.Quantity < 1))
        {
            return ApiResults.BadRequest("ORDER_ITEM_QUANTITY_INVALID", "Order item quantity must be at least one.");
        }

        if (orderType == OrderType.DineIn)
        {
            if (string.IsNullOrWhiteSpace(request.TableCode))
            {
                return ApiResults.BadRequest("DINE_IN_TABLE_REQUIRED", "Dine-in orders require a table code.");
            }

            if (!TableCodeRegex().IsMatch(request.TableCode))
            {
                return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
            }

            if (restaurantData.GetActiveTable(request.TableCode) is null)
            {
                return ApiResults.NotFound("TABLE_NOT_FOUND", "Active table was not found.");
            }
        }

        if (orderType == OrderType.DeliveryMock && !HasDeliveryInfo(request.DeliveryInfo))
        {
            return ApiResults.BadRequest("DELIVERY_INFO_REQUIRED", "Delivery mock orders require recipient, phone, and address.");
        }

        foreach (var item in request.Items)
        {
            if (string.IsNullOrWhiteSpace(item.MenuItemId))
            {
                return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
            }

            var menuItem = restaurantData.GetMenuItem(item.MenuItemId);
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

    private static bool HasDeliveryInfo(DeliveryInfoRequest? deliveryInfo)
    {
        return deliveryInfo is not null
            && !string.IsNullOrWhiteSpace(deliveryInfo.RecipientName)
            && !string.IsNullOrWhiteSpace(deliveryInfo.PhoneNumber)
            && !string.IsNullOrWhiteSpace(deliveryInfo.Address);
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
            order.Status,
            order.PaymentStatus,
            order.PaymentMethod,
            order.DeliveryInfo is null
                ? null
                : new DeliveryInfoResponse(
                    order.DeliveryInfo.RecipientName,
                    order.DeliveryInfo.PhoneNumber,
                    order.DeliveryInfo.Address,
                    order.DeliveryInfo.Note),
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
                .Select(item => new OrderStatusEventResponse(item.Status, item.CreatedAt))
                .ToList());
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

    [GeneratedRegex("^T\\d{2}$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex TableCodeRegex();
}
