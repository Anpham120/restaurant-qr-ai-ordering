using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Counter;

public static class CounterShiftEndpoints
{
    public static IEndpointRouteBuilder MapCounterShiftEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/counter/shifts/current", async (
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var shift = await db.CounterShifts
                .AsNoTracking()
                .Include(item => item.OpenedByUser)
                .Include(item => item.ClosedByUser)
                .Where(item => item.Status == CounterShiftStatus.Open)
                .OrderByDescending(item => item.OpenedAt)
                .FirstOrDefaultAsync(cancellationToken);

            return shift is null
                ? Results.Content("null", "application/json")
                : Results.Ok(ToSummary(shift));
        })
        .RequireAuthorization("CounterOrAdmin")
        .WithName("GetCurrentCounterShift")
        .WithTags("Counter");

        app.MapPost("/api/counter/shifts/open", async (
            OpenCounterShiftRequest? request,
            RestaurantDbContext db,
            ClaimsPrincipal user,
            CancellationToken cancellationToken) =>
        {
            if (request is null || request.OpeningCashBalance < 0)
            {
                return ApiResults.BadRequest("COUNTER_SHIFT_OPEN_INVALID", "Opening cash balance must be zero or greater.");
            }

            var hasOpenShift = await db.CounterShifts.AnyAsync(
                item => item.Status == CounterShiftStatus.Open,
                cancellationToken);
            if (hasOpenShift)
            {
                return ApiResults.Conflict("COUNTER_SHIFT_ALREADY_OPEN", "Close the current shift before opening a new one.");
            }

            var userId = user.FindFirstValue(ClaimTypes.NameIdentifier) ?? string.Empty;
            var now = DateTimeOffset.UtcNow;
            var shift = new CounterShift
            {
                Id = $"shift_{Guid.NewGuid():N}",
                OpenedByUserId = userId,
                Status = CounterShiftStatus.Open,
                OpeningCashBalance = request.OpeningCashBalance,
                ExpectedCashTotal = request.OpeningCashBalance,
                OpenedAt = now,
                UpdatedAt = now,
            };
            db.CounterShifts.Add(shift);
            await db.SaveChangesAsync(cancellationToken);

            shift = await db.CounterShifts
                .AsNoTracking()
                .Include(item => item.OpenedByUser)
                .FirstAsync(item => item.Id == shift.Id, cancellationToken);
            return Results.Ok(ToSummary(shift));
        })
        .RequireAuthorization("CounterOrAdmin")
        .WithName("OpenCounterShift")
        .WithTags("Counter");

        app.MapPost("/api/counter/shifts/{shiftId}/close", async (
            string shiftId,
            CloseCounterShiftRequest? request,
            RestaurantDbContext db,
            ClaimsPrincipal user,
            CancellationToken cancellationToken) =>
        {
            if (request is null || request.ActualCashTotal < 0)
            {
                return ApiResults.BadRequest("COUNTER_SHIFT_CLOSE_INVALID", "Actual cash total must be zero or greater.");
            }

            var shift = await db.CounterShifts
                .Include(item => item.OpenedByUser)
                .Include(item => item.ClosedByUser)
                .FirstOrDefaultAsync(item => item.Id == shiftId, cancellationToken);
            if (shift is null)
            {
                return ApiResults.NotFound("COUNTER_SHIFT_NOT_FOUND", "Counter shift was not found.");
            }
            if (shift.Status != CounterShiftStatus.Open)
            {
                return ApiResults.Conflict("COUNTER_SHIFT_ALREADY_CLOSED", "This shift is already closed.");
            }

            var now = DateTimeOffset.UtcNow;
            shift.Status = CounterShiftStatus.Closed;
            shift.ClosedByUserId = user.FindFirstValue(ClaimTypes.NameIdentifier);
            shift.ActualCashTotal = request.ActualCashTotal;
            shift.CashVariance = request.ActualCashTotal - shift.ExpectedCashTotal;
            shift.CloseNote = string.IsNullOrWhiteSpace(request.CloseNote) ? null : request.CloseNote.Trim();
            shift.ClosedAt = now;
            shift.UpdatedAt = now;
            await db.SaveChangesAsync(cancellationToken);

            return Results.Ok(ToSummary(shift));
        })
        .RequireAuthorization("CounterOrAdmin")
        .WithName("CloseCounterShift")
        .WithTags("Counter");

        app.MapPost("/api/counter/shifts/{shiftId}/adjustments", async (
            string shiftId,
            RecordCounterAdjustmentRequest? request,
            RestaurantDbContext db,
            ClaimsPrincipal user,
            CancellationToken cancellationToken) =>
        {
            if (request is null || string.IsNullOrWhiteSpace(request.ReasonCode))
            {
                return ApiResults.BadRequest("COUNTER_ADJUSTMENT_INVALID", "Reason code is required.");
            }

            var shift = await db.CounterShifts.FirstOrDefaultAsync(item => item.Id == shiftId, cancellationToken);
            if (shift is null)
            {
                return ApiResults.NotFound("COUNTER_SHIFT_NOT_FOUND", "Counter shift was not found.");
            }
            if (shift.Status != CounterShiftStatus.Open)
            {
                return ApiResults.Conflict("COUNTER_SHIFT_CLOSED", "Adjustments are only allowed on an open shift.");
            }

            var now = DateTimeOffset.UtcNow;
            db.CounterShiftTransactions.Add(new CounterShiftTransaction
            {
                Id = $"cst_{Guid.NewGuid():N}",
                CounterShiftId = shift.Id,
                Type = CounterTransactionType.Adjustment,
                Amount = request.Amount,
                ReasonCode = request.ReasonCode.Trim(),
                Note = string.IsNullOrWhiteSpace(request.Note) ? null : request.Note.Trim(),
                CreatedByUserId = user.FindFirstValue(ClaimTypes.NameIdentifier) ?? string.Empty,
                CreatedAt = now,
            });
            shift.ExpectedCashTotal += request.Amount;
            shift.UpdatedAt = now;
            await db.SaveChangesAsync(cancellationToken);
            return Results.Ok(new { ok = true });
        })
        .RequireAuthorization("CounterOrAdmin")
        .WithName("RecordCounterAdjustment")
        .WithTags("Counter");

        return app;
    }

    internal static async Task RecordCashPaymentAsync(
        RestaurantDbContext db,
        decimal amount,
        string tableSessionId,
        string? invoiceCode,
        string createdByUserId,
        CancellationToken cancellationToken)
    {
        var shift = await db.CounterShifts
            .FirstOrDefaultAsync(item => item.Status == CounterShiftStatus.Open, cancellationToken);
        if (shift is null)
        {
            return;
        }

        var now = DateTimeOffset.UtcNow;
        db.CounterShiftTransactions.Add(new CounterShiftTransaction
        {
            Id = $"cst_{Guid.NewGuid():N}",
            CounterShiftId = shift.Id,
            Type = CounterTransactionType.CashPayment,
            Amount = amount,
            TableSessionId = tableSessionId,
            InvoiceCode = invoiceCode,
            ReasonCode = "INVOICE_COD",
            CreatedByUserId = createdByUserId,
            CreatedAt = now,
        });
        shift.ExpectedCashTotal += amount;
        shift.UpdatedAt = now;
    }

    private static CounterShiftSummaryResponse ToSummary(CounterShift shift) =>
        new(
            shift.Id,
            shift.Status.ToString(),
            shift.OpeningCashBalance,
            shift.ExpectedCashTotal,
            shift.ActualCashTotal,
            shift.CashVariance,
            shift.OpenedByUser?.FullName ?? "Unknown",
            shift.ClosedByUser?.FullName,
            shift.OpenedAt,
            shift.ClosedAt);
}
