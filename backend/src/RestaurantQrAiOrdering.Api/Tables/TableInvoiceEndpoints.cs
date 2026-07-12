using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Tables;

public static class TableInvoiceEndpoints
{
    public static IEndpointRouteBuilder MapTableInvoiceEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/table-sessions/{sessionId}/invoice", async (
            string sessionId,
            RestaurantDbContext db,
            HttpRequest request,
            IOptions<JwtOptions> jwtOptions,
            CancellationToken cancellationToken) =>
        {
            var session = await db.TableSessions
                .AsNoTracking()
                .FirstOrDefaultAsync(item => item.Id == sessionId, cancellationToken);
            if (session is null)
            {
                return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
            }

            if (!TableSessionCapability.TryRead(request, out var token) ||
                !TableSessionCapability.IsValid(session, token, jwtOptions.Value.SigningKey))
            {
                return TableSessionCapability.Unauthorized();
            }

            var orderRounds = await db.Orders
                .AsNoTracking()
                .Include(order => order.OrderItems)
                .Where(order => order.TableSessionId == sessionId && order.Status != OrderStatus.Cancelled)
                .OrderBy(order => order.CreatedAt)
                .ToListAsync(cancellationToken);
            var persistedInvoice = await db.TableInvoices
                .AsNoTracking()
                .FirstOrDefaultAsync(invoice => invoice.TableSessionId == sessionId, cancellationToken);

            var subtotal = orderRounds.Sum(order => order.SubtotalAmount);
            var discount = persistedInvoice?.DiscountAmount ?? 0m;
            var items = orderRounds
                .SelectMany(order => order.OrderItems)
                .Where(item => item.Status != OrderItemStatus.Cancelled)
                .GroupBy(item => new { item.MenuItemId, item.MenuItemName, item.UnitPrice })
                .Select(group => new TableInvoiceLineResponse(
                    group.Key.MenuItemId,
                    group.Key.MenuItemName,
                    group.Key.UnitPrice,
                    group.Sum(item => item.Quantity),
                    group.Sum(item => item.UnitPrice * item.Quantity)))
                .OrderBy(item => item.Name)
                .ToArray();
            var rounds = orderRounds
                .Select(order => new TableInvoiceOrderRoundResponse(
                    order.OrderCode,
                    order.Status.ToString(),
                    order.SubtotalAmount,
                    order.CreatedAt))
                .ToArray();

            return Results.Ok(new TableInvoiceResponse(
                session.Id,
                session.TableCode,
                persistedInvoice?.Status.ToString() ?? PaymentStatus.NotRequested.ToString(),
                subtotal,
                discount,
                Math.Max(0m, subtotal - discount),
                persistedInvoice?.PromotionCode,
                persistedInvoice?.CustomerPhoneNumber,
                persistedInvoice?.Method.ToString() ?? PaymentMethod.Unselected.ToString(),
                rounds,
                items));
        })
        .WithName("GetTableSessionInvoice")
        .WithTags("Table Invoices");

        return app;
    }
}
