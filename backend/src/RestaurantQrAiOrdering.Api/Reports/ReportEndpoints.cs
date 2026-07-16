using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Reports;

public static class ReportEndpoints
{
    public static IEndpointRouteBuilder MapReportEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/admin/reports/summary", async (
            DateTimeOffset? from,
            DateTimeOffset? to,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var range = ResolveRange(from, to);
            var paidInvoices = await db.TableInvoices
                .AsNoTracking()
                .Include(invoice => invoice.Payment)
                .Where(invoice =>
                    invoice.Payment != null &&
                    invoice.Payment.PaidAt >= range.From &&
                    invoice.Payment.PaidAt < range.To &&
                    (invoice.Status == PaymentStatus.Paid || invoice.Status == PaymentStatus.Confirmed))
                .ToListAsync(cancellationToken);
            var paidSessionIds = paidInvoices.Select(invoice => invoice.TableSessionId).ToHashSet();
            var orders = await db.Orders
                .AsNoTracking()
                .Include(o => o.Payment)
                .Include(o => o.OrderItems)
                .Where(o =>
                    (o.CreatedAt >= range.From && o.CreatedAt < range.To) ||
                    (o.TableSessionId != null && paidSessionIds.Contains(o.TableSessionId)))
                .ToListAsync(cancellationToken);

            var legacyPaidOrders = orders
                .Where(o => o.Payment is not null
                    && (o.Payment.Status == PaymentStatus.Paid || o.Payment.Status == PaymentStatus.Confirmed)
                    && (o.TableSessionId is null || !paidSessionIds.Contains(o.TableSessionId)))
                .ToList();
            var paidOrderRounds = orders
                .Where(order => order.TableSessionId is not null && paidSessionIds.Contains(order.TableSessionId))
                .ToList();
            var revenueOrders = paidOrderRounds.Concat(legacyPaidOrders).ToList();

            var topItems = revenueOrders
                .SelectMany(o => o.OrderItems)
                .Where(item => item.Status != OrderItemStatus.Cancelled)
                .GroupBy(item => new { item.MenuItemId, item.MenuItemName })
                .Select(group => new TopMenuItemReport(
                    group.Key.MenuItemId,
                    group.Key.MenuItemName,
                    group.Sum(item => item.Quantity),
                    group.Sum(item => item.UnitPrice * item.Quantity)))
                .OrderByDescending(item => item.QuantitySold)
                .ThenByDescending(item => item.Revenue)
                .Take(10)
                .ToList();

            var dailyRevenue = paidInvoices
                .Select(invoice => new { PaidAt = invoice.Payment!.PaidAt!.Value, invoice.TotalAmount })
                .Concat(legacyPaidOrders.Select(order => new
                {
                    PaidAt = order.Payment!.PaidAt ?? order.UpdatedAt,
                    order.TotalAmount
                }))
                .GroupBy(entry => entry.PaidAt.UtcDateTime.Date)
                .Select(group => new DailyRevenueReport(
                    group.Key.ToString("yyyy-MM-dd"),
                    group.Count(),
                    group.Sum(entry => entry.TotalAmount)))
                .OrderBy(day => day.Date)
                .ToList();

            return Results.Ok(new ReportSummaryResponse(
                range.From,
                range.To,
                orders.Count(order => order.CreatedAt >= range.From && order.CreatedAt < range.To),
                paidInvoices.Count + legacyPaidOrders.Count,
                paidInvoices.Sum(invoice => invoice.SubtotalAmount) + legacyPaidOrders.Sum(order => order.SubtotalAmount),
                paidInvoices.Sum(invoice => invoice.DiscountAmount) + legacyPaidOrders.Sum(order => order.DiscountAmount),
                paidInvoices.Sum(invoice => invoice.TotalAmount) + legacyPaidOrders.Sum(order => order.TotalAmount),
                topItems,
                dailyRevenue));
        })
        .RequireAuthorization("AdminOnly")
        .WithName("AdminGetReportSummary")
        .WithTags("Admin Reports");

        return app;
    }

    private static (DateTimeOffset From, DateTimeOffset To) ResolveRange(DateTimeOffset? from, DateTimeOffset? to)
    {
        var now = DateTimeOffset.UtcNow;
        var resolvedTo = to ?? now;
        var resolvedFrom = from ?? resolvedTo.AddDays(-30);

        if (resolvedFrom >= resolvedTo)
        {
            resolvedFrom = resolvedTo.AddDays(-30);
        }

        return (resolvedFrom, resolvedTo);
    }
}

public sealed record TopMenuItemReport(
    string MenuItemId,
    string Name,
    int QuantitySold,
    decimal Revenue);

public sealed record DailyRevenueReport(
    string Date,
    int OrderCount,
    decimal Revenue);

public sealed record ReportSummaryResponse(
    DateTimeOffset From,
    DateTimeOffset To,
    int TotalOrders,
    int PaidOrders,
    decimal GrossRevenue,
    decimal TotalDiscount,
    decimal NetRevenue,
    IReadOnlyList<TopMenuItemReport> TopItems,
    IReadOnlyList<DailyRevenueReport> DailyRevenue);
