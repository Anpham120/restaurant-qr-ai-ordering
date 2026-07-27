using System.Data;
using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Npgsql;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Loyalty;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Payments;
using RestaurantQrAiOrdering.Api.Counter;
using RestaurantQrAiOrdering.Api.Promotions;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;
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
            IVietQrProvider vietQrProvider,
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

            var vietQrPayload = CreateVietQrPayload(persistedInvoice, vietQrProvider);
            return Results.Ok(CreateInvoiceResponse(session, persistedInvoice, orderRounds, vietQrPayload));
        })
        .WithName("GetTableSessionInvoice")
        .WithTags("Table Invoices");

        app.MapPost("/api/table-sessions/{sessionId}/invoice/payment-request", async (
            string sessionId,
            TableInvoicePaymentRequest? paymentRequest,
            RestaurantDbContext db,
            HttpRequest request,
            IOptions<JwtOptions> jwtOptions,
            IVietQrProvider vietQrProvider,
            IOrderRealtimeNotifier realtime,
            CancellationToken cancellationToken) =>
        {
            var executionStrategy = db.Database.CreateExecutionStrategy();
            return await executionStrategy.ExecuteAsync<IResult>(async () =>
            {
                db.ChangeTracker.Clear();
            await using var transaction = db.Database.IsRelational()
                ? await db.Database.BeginTransactionAsync(IsolationLevel.Serializable, cancellationToken)
                : null;
            var session = await db.TableSessions
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
            if (!session.IsActiveAt(DateTimeOffset.UtcNow))
            {
                return ApiResults.BadRequest("TABLE_SESSION_NOT_OPEN", "Only an open table session can request payment.");
            }
            if (!Enum.TryParse<PaymentMethod>(paymentRequest?.Method, true, out var method) ||
                method is not (PaymentMethod.COD or PaymentMethod.VietQR))
            {
                return ApiResults.BadRequest("PAYMENT_METHOD_INVALID", "Payment method must be COD or VietQR.");
            }
            if (!RequestIdempotency.TryRead(request, out var idempotencyKey))
            {
                return ApiResults.BadRequest("IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key header is required.");
            }

            var orderRounds = await db.Orders
                .Include(order => order.OrderItems)
                .Where(order => order.TableSessionId == sessionId && order.Status != OrderStatus.Cancelled)
                .OrderBy(order => order.CreatedAt)
                .ToListAsync(cancellationToken);
            var subtotal = CalculateInvoiceSubtotal(orderRounds);
            if (subtotal <= 0 || orderRounds.Count == 0)
            {
                return ApiResults.BadRequest("TABLE_INVOICE_EMPTY", "The table session has no order rounds to settle.");
            }

            var promotionCode = PromotionCalculator.NormalizeCode(paymentRequest?.PromotionCode);
            var phone = PromotionCalculator.NormalizePhone(paymentRequest?.CustomerPhoneNumber);
            var requestFingerprint = RequestIdempotency.ComputeFingerprint(new
            {
                SessionId = sessionId,
                Method = method.ToString(),
                PromotionCode = promotionCode,
                CustomerPhoneNumber = phone,
                Subtotal = subtotal
            });
            var invoice = await db.TableInvoices
                .Include(item => item.Payment)!
                    .ThenInclude(payment => payment!.Transactions)
                .FirstOrDefaultAsync(item => item.TableSessionId == sessionId, cancellationToken);

            var originalRequest = invoice?.Payment?.Transactions
                .FirstOrDefault(transaction => transaction.IdempotencyKey == idempotencyKey);
            if (originalRequest is not null)
            {
                if (originalRequest.RequestFingerprint != requestFingerprint)
                {
                    return ApiResults.Conflict(
                        "IDEMPOTENCY_KEY_REUSED",
                        "The idempotency key was already used with a different payment request.");
                }
                if (invoice!.Status != PaymentStatus.Pending)
                {
                    return ApiResults.Conflict(
                        "PAYMENT_REQUEST_ATTEMPT_CLOSED",
                        "This payment request attempt is closed. Start a new request with a new idempotency key.");
                }

                var replayPayload = invoice.Method == PaymentMethod.VietQR
                    ? vietQrProvider.CreatePayload(invoice.InvoiceCode, invoice.TotalAmount)
                    : null;
                return Results.Ok(CreatePaymentResponse(session, invoice, orderRounds, replayPayload));
            }
            if (invoice?.Payment is not null && invoice.Status == PaymentStatus.Pending)
            {
                return ApiResults.Conflict(
                    "TABLE_INVOICE_PAYMENT_PENDING",
                    "Payment has already been requested for this table invoice.");
            }

            PromotionDiscountResult? promotion;
            try
            {
                promotion = await PromotionCalculator.TryApplyAsync(
                    db,
                    promotionCode,
                    subtotal,
                    DateTimeOffset.UtcNow,
                    cancellationToken);
            }
            catch (PromotionInvalidException exception)
            {
                return ApiResults.BadRequest(exception.ErrorCode, exception.Message);
            }

            var now = DateTimeOffset.UtcNow;
            session.UpdatedAt = now;
            invoice ??= new TableInvoice
            {
                Id = $"tinv_{Guid.NewGuid():N}",
                InvoiceCode = $"INV-{now:yyyyMMdd}-{Guid.NewGuid():N}"[..21].ToUpperInvariant(),
                TableSessionId = session.Id,
                CreatedAt = now
            };
            if (db.Entry(invoice).State == EntityState.Detached)
            {
                db.TableInvoices.Add(invoice);
            }

            invoice.Status = PaymentStatus.Pending;
            invoice.SubtotalAmount = subtotal;
            invoice.DiscountAmount = promotion?.DiscountAmount ?? 0m;
            invoice.TotalAmount = promotion?.TotalAmount ?? subtotal;
            invoice.PromotionId = promotion?.Promotion.Id;
            invoice.PromotionCode = promotion?.Promotion.Code;
            invoice.CustomerPhoneNumber = phone;
            invoice.Method = method;
            invoice.UpdatedAt = now;

            var vietQrPayload = method == PaymentMethod.VietQR
                ? vietQrProvider.CreatePayload(invoice.InvoiceCode, invoice.TotalAmount)
                : null;
            var payment = invoice.Payment ?? new Payment
            {
                Id = $"pay_{Guid.NewGuid():N}",
                TableInvoice = invoice,
                TableInvoiceId = invoice.Id,
                CreatedAt = now
            };
            invoice.Payment = payment;
            payment.Method = method;
            payment.Status = PaymentStatus.Pending;
            payment.Amount = invoice.TotalAmount;
            payment.UpdatedAt = now;
            payment.Transactions.Add(new PaymentTransaction
            {
                Id = $"ptx_{Guid.NewGuid():N}",
                Payment = payment,
                PaymentId = payment.Id,
                Method = method,
                Status = PaymentStatus.Pending,
                Amount = invoice.TotalAmount,
                Provider = method.ToString(),
                ProviderTransactionId = vietQrPayload?.TransferContent,
                Note = "Customer requested settlement of the table invoice.",
                IdempotencyKey = idempotencyKey,
                RequestFingerprint = requestFingerprint,
                CreatedAt = now
            });

            try
            {
                await db.SaveChangesAsync(cancellationToken);
                if (transaction is not null)
                {
                    await transaction.CommitAsync(cancellationToken);
                }
            }
            catch (Exception exception) when (IsSerializationFailure(exception))
            {
                if (transaction is not null)
                {
                    await transaction.RollbackAsync(cancellationToken);
                }
                return ApiResults.Conflict(
                    "TABLE_SESSION_SETTLEMENT_CONFLICT",
                    "The table session changed while settlement was starting. Reload the invoice and try again.");
            }
            catch (DbUpdateException)
            {
                if (transaction is not null)
                {
                    await transaction.RollbackAsync(cancellationToken);
                }
                db.ChangeTracker.Clear();
                var persistedInvoice = await db.TableInvoices
                    .AsNoTracking()
                    .Include(item => item.Payment)!
                        .ThenInclude(existingPayment => existingPayment!.Transactions)
                    .FirstOrDefaultAsync(item => item.TableSessionId == sessionId, cancellationToken);
                var persistedRequest = persistedInvoice?.Payment?.Transactions.FirstOrDefault(
                    transaction => transaction.IdempotencyKey == idempotencyKey);
                if (persistedInvoice is null) throw;
                if (persistedInvoice?.Status == PaymentStatus.Pending && persistedRequest is null)
                {
                    return ApiResults.Conflict(
                        "TABLE_INVOICE_PAYMENT_PENDING",
                        "Payment has already been requested for this table invoice.");
                }
                if (persistedRequest?.RequestFingerprint != requestFingerprint)
                {
                    return ApiResults.Conflict(
                        "IDEMPOTENCY_KEY_REUSED",
                        "The idempotency key was already used with a different payment request.");
                }
                var persistedVietQr = CreateVietQrPayload(persistedInvoice, vietQrProvider);
                return Results.Ok(CreatePaymentResponse(session, persistedInvoice!, orderRounds, persistedVietQr));
            }

            await realtime.PaymentRequestedAsync(
                new PaymentRequestedEvent(
                    invoice!.Id,
                    invoice.InvoiceCode,
                    payment.Method.ToString(),
                    payment.Status.ToString(),
                    payment.Amount,
                    payment.UpdatedAt,
                    session.TableCode),
                session.TableCode,
                cancellationToken);

                return Results.Ok(CreatePaymentResponse(session, invoice!, orderRounds, vietQrPayload));
            });
        })
        .WithName("RequestTableInvoicePayment")
        .WithTags("Table Invoices");

        app.MapGet("/api/table-invoices", async (
            string? status,
            RestaurantDbContext db,
            IVietQrProvider vietQrProvider,
            CancellationToken cancellationToken) =>
        {
            PaymentStatus? parsedStatus = null;
            if (!string.IsNullOrWhiteSpace(status))
            {
                if (!Enum.TryParse<PaymentStatus>(status, true, out var nextStatus))
                {
                    return ApiResults.BadRequest("PAYMENT_STATUS_INVALID", "Payment status is invalid.");
                }
                parsedStatus = nextStatus;
            }

            var invoiceQuery = db.TableInvoices
                .AsNoTracking()
                .Include(invoice => invoice.TableSession)
                .AsQueryable();
            if (parsedStatus.HasValue)
            {
                invoiceQuery = invoiceQuery.Where(invoice => invoice.Status == parsedStatus.Value);
            }
            var invoices = await invoiceQuery
                .OrderByDescending(invoice => invoice.UpdatedAt)
                .ToListAsync(cancellationToken);
            var sessionIds = invoices.Select(invoice => invoice.TableSessionId).ToList();
            var orderRounds = await db.Orders
                .AsNoTracking()
                .Include(order => order.OrderItems)
                .Where(order => sessionIds.Contains(order.TableSessionId!) && order.Status != OrderStatus.Cancelled)
                .OrderBy(order => order.CreatedAt)
                .ToListAsync(cancellationToken);

            return Results.Ok(invoices.Select(invoice => CreateInvoiceResponse(
                invoice.TableSession!,
                invoice,
                orderRounds.Where(order => order.TableSessionId == invoice.TableSessionId).ToArray(),
                CreateVietQrPayload(invoice, vietQrProvider))).ToArray());
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.CounterStaff, UserRole.Staff, UserRole.Admin))
        .WithName("ListTableInvoices")
        .WithTags("Table Invoices");

        app.MapPost("/api/table-sessions/{sessionId}/invoice/payment/confirm", async (
            string sessionId,
            TableInvoiceSettlementActionRequest? request,
            RestaurantDbContext db,
            IChatStore chatStore,
            IOrderStore orders,
            IOrderRealtimeNotifier realtime,
            ClaimsPrincipal user,
            IVietQrProvider vietQrProvider,
            CancellationToken cancellationToken) =>
        {
            if (ValidateNote(request?.Note) is { } noteError)
            {
                return noteError;
            }
            var invoice = await LoadSettlementInvoiceAsync(db, sessionId, cancellationToken);
            if (invoice?.Payment is null || invoice.TableSession is null)
            {
                return ApiResults.NotFound("TABLE_INVOICE_PAYMENT_NOT_FOUND", "Table invoice payment was not found.");
            }
            if (invoice.Status != PaymentStatus.Pending || invoice.Payment.Status != PaymentStatus.Pending)
            {
                return ApiResults.Conflict("PAYMENT_TRANSITION_INVALID", "Only a pending table invoice payment can be confirmed.");
            }

            var now = DateTimeOffset.UtcNow;
            var note = string.IsNullOrWhiteSpace(request?.Note) ? "Staff confirmed table invoice payment." : request.Note.Trim();
            invoice.Status = PaymentStatus.Confirmed;
            invoice.UpdatedAt = now;
            invoice.Payment.Status = PaymentStatus.Confirmed;
            invoice.Payment.PaidAt = now;
            invoice.Payment.UpdatedAt = now;
            invoice.Payment.Transactions.Add(CreateSettlementTransaction(invoice.Payment, PaymentStatus.Confirmed, note, now));
            invoice.TableSession.Status = TableSessionStatus.Closed;
            invoice.TableSession.ClosedAt = now;
            invoice.TableSession.UpdatedAt = now;
            await LoyaltyService.AccruePointsAsync(
                db,
                invoice.CustomerPhoneNumber,
                invoice.TotalAmount,
                now,
                cancellationToken);

            IReadOnlyList<OrderSnapshot> completedOrders;
            try
            {
                completedOrders = orders.StageTableSessionCompletion(
                    sessionId,
                    ActorContext.FromPrincipal(user),
                    now);
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateException)
            {
                return ApiResults.Conflict("CONFLICT_STALE", "Payment was modified by another request. Reload and try again.");
            }
            chatStore.DeleteSessionsByTableSession(sessionId);
            if (invoice.Method == PaymentMethod.COD)
            {
                await CounterShiftEndpoints.RecordCashPaymentAsync(
                    db,
                    invoice.TotalAmount,
                    sessionId,
                    invoice.InvoiceCode,
                    user.FindFirstValue(ClaimTypes.NameIdentifier) ?? string.Empty,
                    cancellationToken);
            }
            foreach (var order in completedOrders)
            {
                await realtime.OrderStatusChangedAsync(
                    OrderEndpoints.ToOrderStatusChangedEvent(order),
                    order.TableCode,
                    cancellationToken);
            }

            var orderRounds = await LoadOrderRoundsAsync(db, sessionId, cancellationToken);
            var invoiceResponse = CreateInvoiceResponse(invoice.TableSession, invoice, orderRounds, CreateVietQrPayload(invoice, vietQrProvider));
            await realtime.TableInvoicePaymentConfirmedAsync(
                new TableInvoicePaymentConfirmedEvent(invoiceResponse, now),
                invoice.TableSession.TableCode,
                cancellationToken);

            return Results.Ok(invoiceResponse);
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.CounterStaff, UserRole.Staff, UserRole.Admin))
        .WithName("ConfirmTableInvoicePayment")
        .WithTags("Table Invoices");

        app.MapPost("/api/table-sessions/{sessionId}/invoice/payment/cancel", async (
            string sessionId,
            TableInvoiceSettlementActionRequest? request,
            RestaurantDbContext db,
            IVietQrProvider vietQrProvider,
            CancellationToken cancellationToken) =>
        {
            if (ValidateNote(request?.Note) is { } noteError)
            {
                return noteError;
            }
            var invoice = await LoadSettlementInvoiceAsync(db, sessionId, cancellationToken);
            if (invoice?.Payment is null || invoice.TableSession is null)
            {
                return ApiResults.NotFound("TABLE_INVOICE_PAYMENT_NOT_FOUND", "Table invoice payment was not found.");
            }
            if (invoice.Status != PaymentStatus.Pending || invoice.Payment.Status != PaymentStatus.Pending)
            {
                return ApiResults.Conflict("PAYMENT_TRANSITION_INVALID", "Only a pending table invoice payment can be cancelled.");
            }

            var now = DateTimeOffset.UtcNow;
            var note = string.IsNullOrWhiteSpace(request?.Note) ? "Staff cancelled table invoice payment." : request.Note.Trim();
            invoice.Status = PaymentStatus.Cancelled;
            invoice.SubtotalAmount = CalculateInvoiceSubtotal(await LoadOrderRoundsAsync(db, sessionId, cancellationToken));
            invoice.DiscountAmount = 0m;
            invoice.TotalAmount = invoice.SubtotalAmount;
            invoice.PromotionId = null;
            invoice.PromotionCode = null;
            invoice.CustomerPhoneNumber = null;
            invoice.Method = PaymentMethod.Unselected;
            invoice.UpdatedAt = now;
            invoice.Payment.Status = PaymentStatus.Cancelled;
            invoice.Payment.UpdatedAt = now;
            invoice.Payment.Transactions.Add(CreateSettlementTransaction(invoice.Payment, PaymentStatus.Cancelled, note, now));
            try
            {
                await db.SaveChangesAsync(cancellationToken);
            }
            catch (DbUpdateConcurrencyException)
            {
                return ApiResults.Conflict("CONFLICT_STALE", "Payment was modified by another request. Reload and try again.");
            }

            var orderRounds = await LoadOrderRoundsAsync(db, sessionId, cancellationToken);
            return Results.Ok(CreateInvoiceResponse(invoice.TableSession, invoice, orderRounds, CreateVietQrPayload(invoice, vietQrProvider)));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.CounterStaff, UserRole.Staff, UserRole.Admin))
        .WithName("CancelTableInvoicePayment")
        .WithTags("Table Invoices");

        return app;
    }

    private static IResult? ValidateNote(string? note) =>
        note?.Trim().Length > 500
            ? ApiResults.BadRequest("PAYMENT_NOTE_INVALID", "Payment note must be 500 characters or fewer.")
            : null;

    private static bool IsSerializationFailure(Exception exception) =>
        exception is PostgresException { SqlState: PostgresErrorCodes.SerializationFailure } ||
        (exception.InnerException is not null && IsSerializationFailure(exception.InnerException));

    private static Task<TableInvoice?> LoadSettlementInvoiceAsync(
        RestaurantDbContext db,
        string sessionId,
        CancellationToken cancellationToken) =>
        db.TableInvoices
            .Include(invoice => invoice.TableSession)
            .Include(invoice => invoice.Payment)!
                .ThenInclude(payment => payment!.Transactions)
            .FirstOrDefaultAsync(invoice => invoice.TableSessionId == sessionId, cancellationToken);

    private static async Task<IReadOnlyList<Order>> LoadOrderRoundsAsync(
        RestaurantDbContext db,
        string sessionId,
        CancellationToken cancellationToken) =>
        await db.Orders
            .AsNoTracking()
            .Include(order => order.OrderItems)
            .Where(order => order.TableSessionId == sessionId && order.Status != OrderStatus.Cancelled)
            .OrderBy(order => order.CreatedAt)
            .ToListAsync(cancellationToken);

    private static PaymentTransaction CreateSettlementTransaction(
        Payment payment,
        PaymentStatus status,
        string note,
        DateTimeOffset now) =>
        new()
        {
            Id = $"ptx_{Guid.NewGuid():N}",
            PaymentId = payment.Id,
            Method = payment.Method,
            Status = status,
            Amount = payment.Amount,
            Provider = payment.Method.ToString(),
            ProviderTransactionId = payment.ProviderTransactionId,
            Note = note,
            CreatedAt = now
        };

    private static TableInvoicePaymentRequestResponse CreatePaymentResponse(
        TableSession session,
        TableInvoice invoice,
        IReadOnlyList<Order> orderRounds,
        VietQrPayload? vietQrPayload)
    {
        return new TableInvoicePaymentRequestResponse(
            CreateInvoiceResponse(session, invoice, orderRounds, vietQrPayload),
            new TableInvoicePaymentStateResponse(
                invoice.Payment!.Id,
                invoice.Payment.Status.ToString(),
                invoice.Payment.Method.ToString(),
                invoice.Payment.Amount),
            vietQrPayload is null
                ? null
                : new TableInvoiceVietQrResponse(
                    invoice.InvoiceCode,
                    vietQrPayload.Amount,
                    vietQrPayload.TransferContent,
                    vietQrPayload.QuickLink,
                    vietQrPayload.QrImageDataUri));
    }

    private static TableInvoiceResponse CreateInvoiceResponse(
        TableSession session,
        TableInvoice? invoice,
        IReadOnlyList<Order> orderRounds,
        VietQrPayload? vietQrPayload)
    {
        var subtotal = CalculateInvoiceSubtotal(orderRounds);
        var discount = invoice?.DiscountAmount ?? 0m;
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

        return new TableInvoiceResponse(
            session.Id,
            invoice?.InvoiceCode,
            session.TableCode,
            invoice?.Status.ToString() ?? PaymentStatus.NotRequested.ToString(),
            subtotal,
            discount,
            Math.Max(0m, subtotal - discount),
            invoice?.PromotionCode,
            invoice?.CustomerPhoneNumber,
            invoice?.Method.ToString() ?? PaymentMethod.Unselected.ToString(),
            rounds,
            items,
            CreateVietQrResponse(invoice, vietQrPayload));
    }

    private static decimal CalculateInvoiceSubtotal(IEnumerable<Order> orderRounds) =>
        orderRounds
            .SelectMany(order => order.OrderItems)
            .Where(item => item.Status != OrderItemStatus.Cancelled)
            .Sum(item => item.UnitPrice * item.Quantity);

    private static VietQrPayload? CreateVietQrPayload(TableInvoice? invoice, IVietQrProvider vietQrProvider) =>
        invoice is { Status: PaymentStatus.Pending, Method: PaymentMethod.VietQR }
            ? vietQrProvider.CreatePayload(invoice.InvoiceCode, invoice.TotalAmount)
            : null;

    private static TableInvoiceVietQrResponse? CreateVietQrResponse(
        TableInvoice? invoice,
        VietQrPayload? vietQrPayload) =>
        invoice is null || vietQrPayload is null
            ? null
            : new TableInvoiceVietQrResponse(
                invoice.InvoiceCode,
                vietQrPayload.Amount,
                vietQrPayload.TransferContent,
                vietQrPayload.QuickLink,
                vietQrPayload.QrImageDataUri);
}
