using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Loyalty;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Payments;

public static class PaymentEndpoints
{
    public static IEndpointRouteBuilder MapPaymentEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/orders/{orderCode}/payment", async (
            string orderCode,
            RestaurantDbContext db,
            HttpContext http,
            CancellationToken cancellationToken) =>
        {
            var payment = await LoadPaymentAsync(db, orderCode, tracking: false, cancellationToken);
            return payment is null || !OrderAccessGuard.CanRead(http, payment.Order?.CustomerAccessToken)
                ? ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.")
                : Results.Ok(ToResponse(payment));
        })
        .WithName("GetOrderPayment")
        .WithTags("Payments");

        app.MapPost("/api/orders/{orderCode}/payment/vietqr", async (
            string orderCode,
            RestaurantDbContext db,
            IVietQrProvider vietQrProvider,
            HttpContext http,
            CancellationToken cancellationToken) =>
        {
            var payment = await LoadPaymentAsync(db, orderCode, tracking: true, cancellationToken);
            if (payment?.Order is null || !OrderAccessGuard.CanRead(http, payment.Order.CustomerAccessToken))
            {
                return ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.");
            }

            if (payment.Method != PaymentMethod.VietQR)
            {
                return ApiResults.BadRequest("PAYMENT_METHOD_INVALID", "VietQR can only be generated for VietQR payments.");
            }

            if (payment.Status is PaymentStatus.Confirmed or PaymentStatus.Paid)
            {
                return ApiResults.BadRequest("PAYMENT_ALREADY_CONFIRMED", "Payment was already confirmed.");
            }

            VietQrPayload payload;
            try
            {
                payload = vietQrProvider.CreatePayload(payment.Order.OrderCode, payment.Amount);
            }
            catch (InvalidOperationException)
            {
                return ApiResults.BadRequest("VIETQR_CONFIG_MISSING", "VietQR bank configuration is missing.");
            }

            var now = DateTimeOffset.UtcNow;
            payment.Status = PaymentStatus.Pending;
            payment.UpdatedAt = now;
            payment.Transactions.Add(new PaymentTransaction
            {
                Id = $"ptx_{Guid.NewGuid():N}",
                PaymentId = payment.Id,
                Method = PaymentMethod.VietQR,
                Status = PaymentStatus.Pending,
                Amount = payment.Amount,
                Provider = "VietQR",
                ProviderTransactionId = payload.TransferContent,
                Note = "VietQR generated for manual reconciliation.",
                CreatedAt = now
            });
            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Payment was modified by another request. Reload and try again.");
            }

            return Results.Ok(new VietQrResponse(
                payment.Order.OrderCode,
                payload.Amount,
                payload.TransferContent,
                payload.BankId,
                payload.AccountNumber,
                payload.AccountName,
                payload.QuickLink,
                payload.QrPayload,
                payload.QrImageDataUri,
                payment.Status.ToString()));
        })
        .WithName("GenerateVietQrPayment")
        .WithTags("Payments");

        app.MapPost("/api/orders/{orderCode}/payment/confirm", async (
            string orderCode,
            ConfirmPaymentRequest? request,
            RestaurantDbContext db,
            IOrderStore orders,
            ClaimsPrincipal user,
            CancellationToken cancellationToken) =>
        {
            var noteError = ValidatePaymentNote(request?.Note);
            if (noteError is not null)
            {
                return noteError;
            }

            var payment = await LoadPaymentAsync(db, orderCode, tracking: true, cancellationToken);
            if (payment is null)
            {
                return ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.");
            }

            if (payment.Status is PaymentStatus.Confirmed or PaymentStatus.Paid)
            {
                return ApiResults.BadRequest("PAYMENT_ALREADY_CONFIRMED", "Payment was already confirmed.");
            }

            if (payment.Status == PaymentStatus.Failed)
            {
                return ApiResults.BadRequest("PAYMENT_ALREADY_FAILED", "Failed payment cannot be confirmed.");
            }

            var now = DateTimeOffset.UtcNow;
            var note = string.IsNullOrWhiteSpace(request?.Note) ? "Manual staff confirmation." : request.Note.Trim();
            payment.Status = PaymentStatus.Confirmed;
            payment.ProviderTransactionId = string.IsNullOrWhiteSpace(request?.ProviderTransactionId)
                ? payment.ProviderTransactionId
                : request.ProviderTransactionId.Trim();
            payment.PaidAt = now;
            payment.UpdatedAt = now;
            payment.Transactions.Add(new PaymentTransaction
            {
                Id = $"ptx_{Guid.NewGuid():N}",
                PaymentId = payment.Id,
                Method = payment.Method,
                Status = PaymentStatus.Confirmed,
                Amount = payment.Amount,
                Provider = payment.Method.ToString(),
                ProviderTransactionId = payment.ProviderTransactionId,
                Note = note,
                CreatedAt = now
            });
            orders.RecordPaymentStatusEvent(payment.Order!, ActorContext.FromPrincipal(user), note);

            // Accrue loyalty points on confirmed payment. The order's checkout phone takes
            // priority, falling back to the pickup phone when present.
            var loyaltyPhone = payment.Order!.CustomerPhoneNumber ?? payment.Order!.PickupCustomerPhoneNumber;
            await LoyaltyService.AccruePointsAsync(db, loyaltyPhone, payment.Amount, now, cancellationToken);

            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Payment was modified by another request. Reload and try again.");
            }

            return Results.Ok(ToResponse(payment));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.Admin))
        .WithName("ConfirmOrderPayment")
        .WithTags("Payments");

        app.MapPost("/api/orders/{orderCode}/payment/fail", async (
            string orderCode,
            FailPaymentRequest? request,
            RestaurantDbContext db,
            IOrderStore orders,
            ClaimsPrincipal user,
            CancellationToken cancellationToken) =>
        {
            var noteError = ValidatePaymentNote(request?.Note);
            if (noteError is not null)
            {
                return noteError;
            }

            var payment = await LoadPaymentAsync(db, orderCode, tracking: true, cancellationToken);
            if (payment is null)
            {
                return ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.");
            }

            if (payment.Status is PaymentStatus.Confirmed or PaymentStatus.Paid)
            {
                return ApiResults.BadRequest("PAYMENT_ALREADY_CONFIRMED", "Confirmed payment cannot be failed.");
            }

            var now = DateTimeOffset.UtcNow;
            var note = string.IsNullOrWhiteSpace(request?.Note) ? "Manual payment failure." : request.Note.Trim();
            payment.Status = PaymentStatus.Failed;
            payment.UpdatedAt = now;
            payment.Transactions.Add(new PaymentTransaction
            {
                Id = $"ptx_{Guid.NewGuid():N}",
                PaymentId = payment.Id,
                Method = payment.Method,
                Status = PaymentStatus.Failed,
                Amount = payment.Amount,
                Provider = payment.Method.ToString(),
                Note = note,
                CreatedAt = now
            });
            orders.RecordPaymentStatusEvent(payment.Order!, ActorContext.FromPrincipal(user), note);
            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Payment was modified by another request. Reload and try again.");
            }

            return Results.Ok(ToResponse(payment));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.Admin))
        .WithName("FailOrderPayment")
        .WithTags("Payments");

        app.MapPost("/api/orders/{orderCode}/payment/refund", async (
            string orderCode,
            RefundPaymentRequest? request,
            RestaurantDbContext db,
            IOrderStore orders,
            ClaimsPrincipal user,
            CancellationToken cancellationToken) =>
        {
            var noteError = ValidatePaymentNote(request?.Note);
            if (noteError is not null)
            {
                return noteError;
            }

            var payment = await LoadPaymentAsync(db, orderCode, tracking: true, cancellationToken);
            if (payment is null)
            {
                return ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.");
            }

            if (payment.Status is not (PaymentStatus.Confirmed or PaymentStatus.Paid))
            {
                return ApiResults.BadRequest("PAYMENT_NOT_REFUNDABLE", "Only a confirmed or paid payment can be refunded.");
            }

            var now = DateTimeOffset.UtcNow;
            var note = string.IsNullOrWhiteSpace(request?.Note) ? "Manual payment refund." : request.Note.Trim();
            payment.Status = PaymentStatus.Refunded;
            payment.UpdatedAt = now;
            payment.Transactions.Add(new PaymentTransaction
            {
                Id = $"ptx_{Guid.NewGuid():N}",
                PaymentId = payment.Id,
                Method = payment.Method,
                Status = PaymentStatus.Refunded,
                Amount = payment.Amount,
                Provider = payment.Method.ToString(),
                Note = note,
                CreatedAt = now
            });
            orders.RecordPaymentStatusEvent(payment.Order!, ActorContext.FromPrincipal(user), note);
            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Payment was modified by another request. Reload and try again.");
            }

            return Results.Ok(ToResponse(payment));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.Admin))
        .WithName("RefundOrderPayment")
        .WithTags("Payments");

        return app;
    }

    // Maximum length accepted for an operator-supplied payment note.
    private const int MaxPaymentNoteLength = 500;

    // Returns null when the note is acceptable, or a 400 result when it exceeds the limit.
    private static IResult? ValidatePaymentNote(string? note)
    {
        if (note is not null && note.Trim().Length > MaxPaymentNoteLength)
        {
            return ApiResults.BadRequest(
                "PAYMENT_NOTE_TOO_LONG",
                $"Payment note must be {MaxPaymentNoteLength} characters or fewer.");
        }

        return null;
    }

    private static Task<Payment?> LoadPaymentAsync(
        RestaurantDbContext db,
        string orderCode,
        bool tracking,
        CancellationToken cancellationToken)
    {
        var query = db.Payments
            .Include(payment => payment.Order)
            .Include(payment => payment.Transactions)
            .Where(payment => payment.Order != null && payment.Order.OrderCode == orderCode.Trim());

        if (!tracking)
        {
            query = query.AsNoTracking();
        }

        return query.FirstOrDefaultAsync(cancellationToken);
    }

    private static PaymentResponse ToResponse(Payment payment)
    {
        return new PaymentResponse(
            payment.Id,
            payment.Order?.OrderCode ?? string.Empty,
            payment.Method.ToString(),
            payment.Status.ToString(),
            payment.Amount,
            payment.ProviderTransactionId,
            payment.CreatedAt,
            payment.PaidAt,
            payment.UpdatedAt,
            payment.Transactions
                .OrderBy(transaction => transaction.CreatedAt)
                .Select(transaction => new PaymentTransactionResponse(
                    transaction.Id,
                    transaction.Method.ToString(),
                    transaction.Status.ToString(),
                    transaction.Amount,
                    transaction.Provider,
                    transaction.ProviderTransactionId,
                    transaction.Note,
                    transaction.CreatedAt))
                .ToList());
    }
}
