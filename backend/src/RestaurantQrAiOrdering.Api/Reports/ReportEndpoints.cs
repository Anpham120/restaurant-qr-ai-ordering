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
            var orders = await db.Orders
                .AsNoTracking()
                .Include(o => o.Payment)
                .Include(o => o.OrderItems)
                .Where(o => o.CreatedAt >= range.From && o.CreatedAt < range.To)
                .ToListAsync(cancellationToken);

            var paidOrders = orders
                .Where(o => o.Payment is not null
                    && (o.Payment.Status == PaymentStatus.Paid || o.Payment.Status == PaymentStatus.Confirmed))
                .ToList();

            var topItems = paidOrders
                .SelectMany(o => o.OrderItems)
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

            var dailyRevenue = paidOrders
                .GroupBy(o => o.CreatedAt.UtcDateTime.Date)
                .Select(group => new DailyRevenueReport(
                    group.Key.ToString("yyyy-MM-dd"),
                    group.Count(),
                    group.Sum(o => o.TotalAmount)))
                .OrderBy(day => day.Date)
                .ToList();

            return Results.Ok(new ReportSummaryResponse(
                range.From,
                range.To,
                orders.Count,
                paidOrders.Count,
                paidOrders.Sum(o => o.SubtotalAmount),
                paidOrders.Sum(o => o.DiscountAmount),
                paidOrders.Sum(o => o.TotalAmount),
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
