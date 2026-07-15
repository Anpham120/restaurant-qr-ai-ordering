using System.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Tables;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Cart;

public static class CartEndpoints
{
    private const int MaxQuantityPerItem = 99;

    public static IEndpointRouteBuilder MapCartEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/table-sessions/{tableSessionId}/cart", async (
            string tableSessionId,
            HttpRequest request,
            RestaurantDbContext db,
            IOptions<JwtOptions> jwtOptions,
            CancellationToken cancellationToken) =>
        {
            var sessionResult = await ValidateTableSessionAsync(
                tableSessionId,
                request,
                db,
                jwtOptions.Value.SigningKey,
                cancellationToken);
            if (sessionResult.Error is not null)
            {
                return sessionResult.Error;
            }

            return Results.Ok(await BuildCartResponseAsync(tableSessionId, db, cancellationToken));
        })
        .WithName("GetTableSessionCart")
        .WithTags("Cart");

        app.MapPost("/api/table-sessions/{tableSessionId}/cart/items", async (
            string tableSessionId,
            UpdateCartItemRequest? request,
            HttpRequest httpRequest,
            RestaurantDbContext db,
            IOptions<JwtOptions> jwtOptions,
            IOrderRealtimeNotifier realtime,
            CancellationToken cancellationToken) =>
        {
            if (request is null || string.IsNullOrWhiteSpace(request.MenuItemId))
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "menuItemId is required.");
            }

            if (request.Delta == 0)
            {
                return ApiResults.BadRequest("CART_DELTA_INVALID", "delta must not be zero.");
            }

            var sessionResult = await ValidateTableSessionAsync(
                tableSessionId,
                httpRequest,
                db,
                jwtOptions.Value.SigningKey,
                cancellationToken);
            if (sessionResult.Error is not null)
            {
                return sessionResult.Error;
            }

            await using var transaction = db.Database.IsRelational()
                ? await db.Database.BeginTransactionAsync(IsolationLevel.Serializable, cancellationToken)
                : null;

            var menuItemId = request.MenuItemId.Trim();
            if (request.Delta > 0)
            {
                var menuItem = await db.MenuItems
                    .AsNoTracking()
                    .FirstOrDefaultAsync(item => item.Id == menuItemId, cancellationToken);
                if (menuItem is null)
                {
                    return ApiResults.NotFound("MENU_ITEM_NOT_FOUND", "Menu item was not found.");
                }

                if (!menuItem.IsAvailable)
                {
                    return ApiResults.BadRequest("MENU_ITEM_UNAVAILABLE", "Menu item is unavailable.");
                }
            }

            var cartItem = await db.TableSessionCartItems
                .FirstOrDefaultAsync(
                    item => item.TableSessionId == tableSessionId && item.MenuItemId == menuItemId,
                    cancellationToken);

            var nextQuantity = (cartItem?.Quantity ?? 0) + request.Delta;
            if (nextQuantity <= 0)
            {
                if (cartItem is not null)
                {
                    db.TableSessionCartItems.Remove(cartItem);
                }
            }
            else
            {
                if (nextQuantity > MaxQuantityPerItem)
                {
                    return ApiResults.BadRequest(
                        "CART_ITEM_QUANTITY_INVALID",
                        $"Cart item quantity must be between 1 and {MaxQuantityPerItem}.");
                }

                var now = DateTimeOffset.UtcNow;
                if (cartItem is null)
                {
                    cartItem = new TableSessionCartItem
                    {
                        Id = $"cart_{Guid.NewGuid():N}",
                        TableSessionId = tableSessionId,
                        MenuItemId = menuItemId,
                        Quantity = nextQuantity,
                        Note = NormalizeNote(request.Note),
                        UpdatedAt = now
                    };
                    db.TableSessionCartItems.Add(cartItem);
                }
                else
                {
                    cartItem.Quantity = nextQuantity;
                    if (request.Note is not null)
                    {
                        cartItem.Note = NormalizeNote(request.Note);
                    }

                    cartItem.UpdatedAt = now;
                }
            }

            await db.SaveChangesAsync(cancellationToken);
            if (transaction is not null)
            {
                await transaction.CommitAsync(cancellationToken);
            }

            var cart = await BuildCartResponseAsync(tableSessionId, db, cancellationToken);
            await realtime.NotifyCartUpdatedAsync(
                ToCartUpdatedEvent(sessionResult.Session!, cart),
                cancellationToken);

            return Results.Ok(cart);
        })
        .WithName("UpdateTableSessionCartItem")
        .WithTags("Cart");

        app.MapDelete("/api/table-sessions/{tableSessionId}/cart", async (
            string tableSessionId,
            HttpRequest request,
            RestaurantDbContext db,
            IOptions<JwtOptions> jwtOptions,
            IOrderRealtimeNotifier realtime,
            CancellationToken cancellationToken) =>
        {
            var sessionResult = await ValidateTableSessionAsync(
                tableSessionId,
                request,
                db,
                jwtOptions.Value.SigningKey,
                cancellationToken);
            if (sessionResult.Error is not null)
            {
                return sessionResult.Error;
            }

            await using var transaction = db.Database.IsRelational()
                ? await db.Database.BeginTransactionAsync(IsolationLevel.Serializable, cancellationToken)
                : null;

            var cartItems = await db.TableSessionCartItems
                .Where(item => item.TableSessionId == tableSessionId)
                .ToListAsync(cancellationToken);
            if (cartItems.Count > 0)
            {
                db.TableSessionCartItems.RemoveRange(cartItems);
                await db.SaveChangesAsync(cancellationToken);
            }

            if (transaction is not null)
            {
                await transaction.CommitAsync(cancellationToken);
            }

            var cart = await BuildCartResponseAsync(tableSessionId, db, cancellationToken);
            await realtime.NotifyCartUpdatedAsync(
                ToCartUpdatedEvent(sessionResult.Session!, cart),
                cancellationToken);

            return Results.Ok(cart);
        })
        .WithName("ClearTableSessionCart")
        .WithTags("Cart");

        return app;
    }

    private static async Task<(TableSession? Session, IResult? Error)> ValidateTableSessionAsync(
        string tableSessionId,
        HttpRequest request,
        RestaurantDbContext db,
        string signingKey,
        CancellationToken cancellationToken)
    {
        if (!TableSessionCapability.TryRead(request, out var suppliedToken))
        {
            return (null, TableSessionCapability.Unauthorized());
        }

        var session = await db.TableSessions
            .FirstOrDefaultAsync(item => item.Id == tableSessionId, cancellationToken);
        if (session is null)
        {
            return (null, ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found."));
        }

        if (!TableSessionCapability.IsValid(session, suppliedToken, signingKey))
        {
            return (null, TableSessionCapability.Unauthorized());
        }

        var now = DateTimeOffset.UtcNow;
        if (!session.IsActiveAt(now))
        {
            if (session.ExpireIfPast(now))
            {
                await db.SaveChangesAsync(cancellationToken);
            }

            return (null, ApiErrorFactory.Result(
                StatusCodes.Status410Gone,
                "TABLE_SESSION_INACTIVE",
                "Table session is closed or expired. Please scan QR again."));
        }

        return (session, null);
    }

    private static async Task<CartResponse> BuildCartResponseAsync(
        string tableSessionId,
        RestaurantDbContext db,
        CancellationToken cancellationToken)
    {
        var cartItems = await db.TableSessionCartItems
            .AsNoTracking()
            .Where(item => item.TableSessionId == tableSessionId)
            .Include(item => item.MenuItem)
                .ThenInclude(menuItem => menuItem!.Category)
            .OrderBy(item => item.UpdatedAt)
            .ThenBy(item => item.MenuItemId)
            .ToListAsync(cancellationToken);

        var items = cartItems
            .Select(item =>
            {
                var menuItem = item.MenuItem!;
                return new CartItemResponse(
                    item.Id,
                    item.MenuItemId,
                    menuItem.Name,
                    menuItem.Description,
                    menuItem.Price,
                    menuItem.CategoryId,
                    menuItem.Category?.Name ?? string.Empty,
                    menuItem.ImageUrl,
                    menuItem.IsAvailable,
                    item.Quantity,
                    item.Note,
                    menuItem.Price * item.Quantity,
                    item.UpdatedAt);
            })
            .ToList();

        var itemCount = items.Sum(item => item.Quantity);
        var subtotal = items.Sum(item => item.LineTotal);
        var updatedAt = items.Count == 0
            ? DateTimeOffset.UtcNow
            : items.Max(item => item.UpdatedAt);

        return new CartResponse(tableSessionId, items, itemCount, subtotal, updatedAt);
    }

    private static CartUpdatedEvent ToCartUpdatedEvent(TableSession session, CartResponse cart)
    {
        return new CartUpdatedEvent(
            cart.TableSessionId,
            session.TableCode,
            cart.ItemCount,
            cart.Subtotal,
            cart.UpdatedAt);
    }

    private static string? NormalizeNote(string? note)
    {
        if (note is null)
        {
            return null;
        }

        var trimmed = note.Trim();
        return trimmed.Length == 0 ? null : trimmed;
    }
}
