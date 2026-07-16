using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Loyalty;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Realtime;
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
            if (http.User.IsInRole(UserRole.Kitchen))
            {
                return ApiResults.Forbidden(
                    "PAYMENT_ACCESS_DENIED",
                    "Kitchen users cannot access payment operations.");
            }

            var payment = await LoadPaymentAsync(db, orderCode, tracking: false, cancellationToken);
            return payment is null || !OrderAccessGuard.CanRead(http, payment.Order?.CustomerAccessToken)
                ? ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.")
                : Results.Ok(ToResponse(payment));
        })
        .WithName("GetOrderPayment")
        .WithTags("Payments");

        app.MapPost("/api/orders/{orderCode}/payment/request", async (
            string orderCode,
            PaymentRequest? request,
            RestaurantDbContext db,
            IVietQrProvider vietQrProvider,
            IOrderRealtimeNotifier realtime,
            HttpContext http,
            CancellationToken cancellationToken) =>
        {
            if (http.User.IsInRole(UserRole.Kitchen))
            {
                return ApiResults.Forbidden(
                    "PAYMENT_ACCESS_DENIED",
                    "Kitchen users cannot access payment operations.");
            }

            var payment = await LoadPaymentAsync(db, orderCode, tracking: true, cancellationToken);
            var providedOrderToken = http.Request.Headers[OrderAccessGuard.TokenHeaderName].ToString();
            if (payment?.Order is null
                || !OrderAccessGuard.HasCustomerToken(payment.Order.CustomerAccessToken, providedOrderToken))
            {
                return ApiResults.NotFound("PAYMENT_NOT_FOUND", "Payment was not found.");
            }

            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            if (!TryParseRequestedMethod(request.Method, out var method))
            {
                return ApiResults.BadRequest("PAYMENT_METHOD_INVALID", "Payment method must be COD or VietQR.");
            }

            if (!RequestIdempotency.TryRead(http.Request, out var idempotencyKey))
            {
                return http.Request.Headers.ContainsKey(RequestIdempotency.HeaderName)
                    ? ApiResults.BadRequest(
                        "IDEMPOTENCY_KEY_INVALID",
                        "Idempotency-Key must contain 1 to 100 letters, numbers, '.', '_', ':' or '-'.")
                    : ApiResults.BadRequest(
                        "IDEMPOTENCY_KEY_REQUIRED",
                        "Idempotency-Key header is required.");
            }

            var requestFingerprint = RequestIdempotency.ComputeFingerprint(new { Method = method.ToString() });
            var existingRequest = await FindPaymentRequestAsync(db, idempotencyKey, cancellationToken);
            if (existingRequest is not null)
            {
                if (existingRequest.Payment?.Order?.OrderCode != payment.Order.OrderCode
                    || existingRequest.RequestFingerprint != requestFingerprint)
                {
                    return ApiResults.Conflict(
                        "IDEMPOTENCY_KEY_REUSED",
                        "Idempotency key was already used with a different request.");
                }

                return Results.Ok(CreatePaymentRequestReplayResponse(
                    payment,
                    existingRequest,
                    vietQrProvider));
            }

            if (payment.Status is PaymentStatus.Pending
                or PaymentStatus.Confirmed
                or PaymentStatus.Paid
                or PaymentStatus.Refunded)
            {
                return ApiResults.Conflict(
                    "PAYMENT_ALREADY_REQUESTED",
                    "Payment was already requested or completed.");
            }

            VietQrPayload? payload = null;
            if (method == PaymentMethod.VietQR)
            {
                try
                {
                    payload = vietQrProvider.CreatePayload(payment.Order.OrderCode, payment.Amount);
                }
                catch (InvalidOperationException)
                {
                    return ApiResults.BadRequest("VIETQR_CONFIG_MISSING", "VietQR bank configuration is missing.");
                }
            }

            var now = DateTimeOffset.UtcNow;
            payment.Method = method;
            payment.Status = PaymentStatus.Pending;
            payment.UpdatedAt = now;
            payment.Transactions.Add(new PaymentTransaction
            {
                Id = $"ptx_{Guid.NewGuid():N}",
                PaymentId = payment.Id,
                Method = method,
                Status = PaymentStatus.Pending,
                Amount = payment.Amount,
                Provider = method.ToString(),
                ProviderTransactionId = payload?.TransferContent,
                Note = method == PaymentMethod.VietQR
                    ? "Customer requested VietQR payment."
                    : "Customer requested cash payment.",
                IdempotencyKey = idempotencyKey,
                RequestFingerprint = requestFingerprint,
                CreatedAt = now
            });
            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                db.ChangeTracker.Clear();
                var duplicate = await FindPaymentRequestAsync(db, idempotencyKey, cancellationToken);
                if (duplicate?.Payment?.Order?.OrderCode == orderCode.Trim()
                    && duplicate.RequestFingerprint == requestFingerprint)
                {
                    var reloaded = await LoadPaymentAsync(db, orderCode, tracking: false, cancellationToken);
                    if (reloaded is not null)
                    {
                        return Results.Ok(CreatePaymentRequestReplayResponse(
                            reloaded,
                            duplicate,
                            vietQrProvider));
                    }
                }

                return ApiResults.Conflict(
                    "CONFLICT_STALE",
                    "Payment was modified by another request. Reload and try again.");
            }
            catch (DbUpdateException)
            {
                db.ChangeTracker.Clear();
                var duplicate = await FindPaymentRequestAsync(db, idempotencyKey, cancellationToken);
                if (duplicate?.Payment?.Order?.OrderCode != orderCode.Trim()
                    || duplicate.RequestFingerprint != requestFingerprint)
                {
                    return ApiResults.Conflict(
                        "IDEMPOTENCY_KEY_REUSED",
                        "Idempotency key was already used with a different request.");
                }

                var reloaded = await LoadPaymentAsync(db, orderCode, tracking: false, cancellationToken);
                return reloaded is null
                    ? ApiResults.Conflict("CONFLICT_STALE", "Payment changed while the request was processed.")
                    : Results.Ok(CreatePaymentRequestReplayResponse(
                        reloaded,
                        duplicate,
                        vietQrProvider));
            }

            await realtime.PaymentRequestedAsync(
                new PaymentRequestedEvent(
                    payment.Order.Id,
                    payment.Order.OrderCode,
                    payment.Method.ToString(),
                    payment.Status.ToString(),
                    payment.Amount,
                    payment.UpdatedAt),
                payment.Order.TableCode,
                cancellationToken);

            return Results.Ok(CreatePaymentRequestResponse(payment, method, vietQrProvider));
        })
        .WithName("RequestOrderPayment")
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

            if (ValidateManualPaymentTransition(payment, PaymentStatus.Confirmed) is { } transitionError)
            {
                return transitionError;
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

            if (ValidateManualPaymentTransition(payment, PaymentStatus.Failed) is { } transitionError)
            {
                return transitionError;
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

    private static IResult? ValidateManualPaymentTransition(Payment payment, PaymentStatus nextStatus)
    {
        if (payment.Status == PaymentStatus.NotRequested || payment.Method == PaymentMethod.Unselected)
        {
            return ApiResults.BadRequest(
                "PAYMENT_NOT_REQUESTED",
                "Customer has not requested payment yet.");
        }

        if (payment.Status == PaymentStatus.Refunded)
        {
            var action = nextStatus == PaymentStatus.Confirmed ? "confirmed" : "failed";
            return ApiResults.BadRequest(
                "PAYMENT_ALREADY_REFUNDED",
                $"Refunded payment cannot be {action}.");
        }

        if (payment.Status is PaymentStatus.Confirmed or PaymentStatus.Paid)
        {
            var message = nextStatus == PaymentStatus.Confirmed
                ? "Payment was already confirmed."
                : "Confirmed payment cannot be failed.";
            return ApiResults.BadRequest("PAYMENT_ALREADY_CONFIRMED", message);
        }

        if (payment.Status == PaymentStatus.Failed)
        {
            var message = nextStatus == PaymentStatus.Confirmed
                ? "Failed payment cannot be confirmed."
                : "Payment was already failed.";
            return ApiResults.BadRequest("PAYMENT_ALREADY_FAILED", message);
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

    private static Task<PaymentTransaction?> FindPaymentRequestAsync(
        RestaurantDbContext db,
        string idempotencyKey,
        CancellationToken cancellationToken)
    {
        return db.PaymentTransactions
            .AsNoTracking()
            .Include(transaction => transaction.Payment)
                .ThenInclude(payment => payment!.Order)
            .FirstOrDefaultAsync(
                transaction => transaction.IdempotencyKey == idempotencyKey,
                cancellationToken);
    }

    private static bool TryParseRequestedMethod(string? value, out PaymentMethod method)
    {
        return Enum.TryParse(value?.Trim(), ignoreCase: false, out method)
            && method is PaymentMethod.COD or PaymentMethod.VietQR;
    }

    private static PaymentRequestResponse CreatePaymentRequestResponse(
        Payment payment,
        PaymentMethod method,
        IVietQrProvider vietQrProvider)
    {
        VietQrResponse? vietQr = null;
        if (method == PaymentMethod.VietQR && payment.Order is not null)
        {
            var payload = vietQrProvider.CreatePayload(payment.Order.OrderCode, payment.Amount);
            vietQr = new VietQrResponse(
                payment.Order.OrderCode,
                payload.Amount,
                payload.TransferContent,
                payload.BankId,
                payload.AccountNumber,
                payload.AccountName,
                payload.QuickLink,
                payload.QrPayload,
                payload.QrImageDataUri,
                PaymentStatus.Pending.ToString());
        }

        return new PaymentRequestResponse(ToResponse(payment), vietQr);
    }

    private static PaymentRequestResponse CreatePaymentRequestReplayResponse(
        Payment payment,
        PaymentTransaction requestTransaction,
        IVietQrProvider vietQrProvider)
    {
        var originalPayment = new PaymentResponse(
            payment.Id,
            payment.Order?.OrderCode ?? string.Empty,
            requestTransaction.Method.ToString(),
            requestTransaction.Status.ToString(),
            payment.Amount,
            null,
            payment.CreatedAt,
            null,
            requestTransaction.CreatedAt,
            payment.Transactions
                .Where(transaction => transaction.CreatedAt < requestTransaction.CreatedAt
                    || transaction.Id == requestTransaction.Id)
                .OrderBy(transaction => transaction.CreatedAt)
                .Select(ToTransactionResponse)
                .ToList());

        VietQrResponse? vietQr = null;
        if (requestTransaction.Method == PaymentMethod.VietQR && payment.Order is not null)
        {
            var payload = vietQrProvider.CreatePayload(payment.Order.OrderCode, payment.Amount);
            vietQr = new VietQrResponse(
                payment.Order.OrderCode,
                payload.Amount,
                payload.TransferContent,
                payload.BankId,
                payload.AccountNumber,
                payload.AccountName,
                payload.QuickLink,
                payload.QrPayload,
                payload.QrImageDataUri,
                requestTransaction.Status.ToString());
        }

        return new PaymentRequestResponse(originalPayment, vietQr);
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
                .Select(ToTransactionResponse)
                .ToList());
    }

    private static PaymentTransactionResponse ToTransactionResponse(PaymentTransaction transaction)
    {
        return new PaymentTransactionResponse(
            transaction.Id,
            transaction.Method.ToString(),
            transaction.Status.ToString(),
            transaction.Amount,
            transaction.Provider,
            transaction.ProviderTransactionId,
            transaction.Note,
            transaction.CreatedAt);
    }
}
