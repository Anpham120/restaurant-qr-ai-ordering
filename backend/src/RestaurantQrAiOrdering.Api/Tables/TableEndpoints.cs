using System.Collections.Concurrent;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Tables;

public static partial class TableEndpoints
{
    private static readonly TimeSpan DefaultSessionLifetime = TimeSpan.FromHours(4);
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> SessionOpenGates = new();
    // Multi-device dine-in requires a stable table QR. Single-use rotation is disabled.
    private static readonly bool SingleUseQrEnabled = false;

    public static IEndpointRouteBuilder MapTableEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/admin/tables", async (
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var tables = await db.RestaurantTables
                .AsNoTracking()
                .OrderBy(t => t.TableCode)
                .ToListAsync(cancellationToken);

            var items = tables
                .Select(ToAdminTableResponse)
                .ToList();

            return Results.Ok(new TableListResponse(items, items.Count));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.CounterStaff, UserRole.Admin))
        .WithName("AdminListTables")
        .WithTags("Admin Tables");

        app.MapPost("/api/admin/tables", async (
            CreateTableRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            if (request is null || string.IsNullOrWhiteSpace(request.DisplayName))
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "displayName is required.");
            }

            string? tableCode;
            if (string.IsNullOrWhiteSpace(request.TableCode))
            {
                tableCode = await AllocateNextTableCodeAsync(db, cancellationToken);
                if (tableCode is null)
                {
                    return ApiResults.Conflict("TABLE_CAPACITY_REACHED", "No available table codes remain.");
                }
            }
            else
            {
                tableCode = NormalizeTableCode(request.TableCode);
                if (tableCode is null)
                {
                    return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
                }
            }

            var exists = await db.RestaurantTables
                .AnyAsync(table => table.TableCode == tableCode, cancellationToken);
            if (exists)
            {
                return ApiResults.Conflict("TABLE_CODE_EXISTS", "Table code is already in use.");
            }

            var now = DateTimeOffset.UtcNow;
            var table = new RestaurantTable
            {
                Id = $"tbl_{Guid.NewGuid():N}",
                TableCode = tableCode,
                DisplayName = request.DisplayName.Trim(),
                IsActive = true,
                CreatedAt = now,
                UpdatedAt = now,
            };
            TableQrTokenRotator.RotateTableQrToken(table);
            db.RestaurantTables.Add(table);
            await db.SaveChangesAsync(cancellationToken);

            return Results.Created($"/api/admin/tables/{tableCode}", ToAdminTableResponse(table));
        })
        .RequireAuthorization("AdminOnly")
        .WithName("AdminCreateTable")
        .WithTags("Admin Tables");

        app.MapPatch("/api/admin/tables/{tableCode}", async (
            string tableCode,
            UpdateTableRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            var normalizedTableCode = NormalizeTableCode(tableCode);
            if (normalizedTableCode is null)
            {
                return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
            }

            var table = await db.RestaurantTables
                .FirstOrDefaultAsync(item => item.TableCode == normalizedTableCode, cancellationToken);
            if (table is null)
            {
                return ApiResults.NotFound("TABLE_NOT_FOUND", "Table was not found.");
            }

            if (request.IsActive == false && table.IsActive)
            {
                var blockReason = await GetTableMutationBlockReasonAsync(db, table.Id, cancellationToken);
                if (blockReason is not null)
                {
                    return blockReason;
                }
            }

            if (request.DisplayName is not null)
            {
                var trimmedName = request.DisplayName.Trim();
                if (trimmedName.Length == 0)
                {
                    return ApiResults.BadRequest("DISPLAY_NAME_INVALID", "displayName must not be empty.");
                }

                table.DisplayName = trimmedName;
            }

            if (request.IsActive.HasValue)
            {
                table.IsActive = request.IsActive.Value;
            }

            table.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(cancellationToken);

            return Results.Ok(ToAdminTableResponse(table));
        })
        .RequireAuthorization("AdminOnly")
        .WithName("AdminUpdateTable")
        .WithTags("Admin Tables");

        app.MapPost("/api/admin/tables/{tableCode}/qr/rotate", async (
            string tableCode,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var normalizedTableCode = NormalizeTableCode(tableCode);
            if (normalizedTableCode is null)
            {
                return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
            }

            var table = await db.RestaurantTables
                .FirstOrDefaultAsync(item => item.TableCode == normalizedTableCode, cancellationToken);
            if (table is null)
            {
                return ApiResults.NotFound("TABLE_NOT_FOUND", "Table was not found.");
            }

            var blockReason = await GetTableMutationBlockReasonAsync(db, table.Id, cancellationToken);
            if (blockReason is not null)
            {
                return blockReason;
            }

            TableQrTokenRotator.RotateTableQrToken(table);
            await db.SaveChangesAsync(cancellationToken);

            return Results.Ok(ToAdminTableResponse(table));
        })
        .RequireAuthorization("AdminOnly")
        .WithName("AdminRotateTableQr")
        .WithTags("Admin Tables");

        app.MapGet("/api/admin/table-sessions", async (
            string? status,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var query = db.TableSessions
                .AsNoTracking()
                .Include(s => s.RestaurantTable)
                .AsQueryable();

            if (!string.IsNullOrWhiteSpace(status))
            {
                if (!Enum.TryParse<TableSessionStatus>(status.Trim(), ignoreCase: true, out var parsedStatus))
                {
                    return ApiResults.BadRequest("TABLE_SESSION_STATUS_INVALID", "Table session status is invalid.");
                }

                query = query.Where(s => s.Status == parsedStatus);
            }

            var now = DateTimeOffset.UtcNow;
            var sessions = await query
                .OrderByDescending(s => s.OpenedAt)
                .ToListAsync(cancellationToken);

            var activeOrderCounts = await db.Orders
                .AsNoTracking()
                .Where(o =>
                    o.TableSessionId != null &&
                    o.Status != OrderStatus.Completed &&
                    o.Status != OrderStatus.Cancelled)
                .GroupBy(o => o.TableSessionId!)
                .Select(g => new { SessionId = g.Key, Count = g.Count() })
                .ToDictionaryAsync(x => x.SessionId, x => x.Count, cancellationToken);

            var items = sessions
                .Select(session => new AdminTableSessionSummaryResponse(
                    session.Id,
                    session.TableCode ?? session.RestaurantTable?.TableCode ?? string.Empty,
                    session.RestaurantTable?.DisplayName,
                    session.Status.ToString(),
                    session.OpenedAt,
                    session.ExpiresAt,
                    session.ClosedAt,
                    IsExpired(session, now),
                    activeOrderCounts.GetValueOrDefault(session.Id)))
                .ToList();

            return Results.Ok(new AdminTableSessionListResponse(items, items.Count));
        })
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.CounterStaff, UserRole.Admin))
        .WithName("AdminListTableSessions")
        .WithTags("Tables");

        app.MapGet("/api/tables/{tableCode}", async (
            string tableCode,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var normalizedTableCode = NormalizeTableCode(tableCode);
            if (normalizedTableCode is null)
            {
                return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
            }

            var table = await db.RestaurantTables
                .AsNoTracking()
                .FirstOrDefaultAsync(t => t.TableCode == normalizedTableCode && t.IsActive, cancellationToken);

            return table is null
                ? ApiResults.NotFound("TABLE_NOT_FOUND", "Active table was not found.")
                : Results.Ok(ToPublicTableResponse(table));
        })
        .WithName("GetTable")
        .WithTags("Tables");

        app.MapGet("/api/tables/qr/{qrToken}", async (
            string qrToken,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var normalizedQrToken = NormalizeQrToken(qrToken);
            if (normalizedQrToken is null)
            {
                return ApiResults.BadRequest("QR_TOKEN_INVALID", "QR token is required.");
            }

            var table = await db.RestaurantTables
                .AsNoTracking()
                .FirstOrDefaultAsync(t => t.QrToken == normalizedQrToken && t.IsActive, cancellationToken);

            return table is null
                ? ApiResults.NotFound("QR_NOT_FOUND", "QR token does not match an active table.")
                : Results.Ok(new TableQrResponse(
                    table.TableCode,
                    table.DisplayName));
        })
        .WithName("ResolveTableQr")
        .WithTags("Tables");

        app.MapPost("/api/table-sessions", async (
            OpenTableSessionRequest? request,
            RestaurantDbContext db,
            IChatStore chatStore,
            IOptions<JwtOptions> jwtOptions,
            ILoggerFactory loggerFactory,
            CancellationToken cancellationToken) =>
        {
            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            return await OpenDineInSessionAsync(
                request,
                db,
                chatStore,
                jwtOptions.Value.SigningKey,
                loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Tables.TableSession"),
                cancellationToken);
        })
        .WithName("OpenTableSession")
        .WithTags("Tables");

        app.MapGet("/api/table-sessions/{sessionId}", async (
            string sessionId,
            HttpRequest request,
            RestaurantDbContext db,
            IChatStore chatStore,
            IOptions<JwtOptions> jwtOptions,
            CancellationToken cancellationToken) =>
        {
            if (!TableSessionCapability.TryRead(request, out var suppliedToken))
            {
                return TableSessionCapability.Unauthorized();
            }

            var session = await db.TableSessions
                .Include(s => s.RestaurantTable)
                .FirstOrDefaultAsync(s => s.Id == sessionId, cancellationToken);

            if (session is null)
            {
                return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
            }

            if (!TableSessionCapability.IsValid(session, suppliedToken, jwtOptions.Value.SigningKey))
            {
                return TableSessionCapability.Unauthorized();
            }

            var now = DateTimeOffset.UtcNow;
            if (IsExpired(session, now))
            {
                await MarkExpiredAsync(session, db, chatStore, now, cancellationToken);
                return ApiErrorFactory.Result(
                    StatusCodes.Status410Gone,
                    "TABLE_SESSION_EXPIRED",
                    "Table session has expired. Please scan QR again.");
            }

            return Results.Ok(ToSessionResponse(session, now));
        })
        .WithName("GetTableSession")
        .WithTags("Tables");

        app.MapGet("/api/table-sessions/{sessionId}/orders", async (
            string sessionId,
            HttpRequest request,
            RestaurantDbContext db,
            IOptions<JwtOptions> jwtOptions,
            CancellationToken cancellationToken) =>
        {
            if (!TableSessionCapability.TryRead(request, out var suppliedToken))
            {
                return TableSessionCapability.Unauthorized();
            }

            var tableSession = await db.TableSessions
                .FirstOrDefaultAsync(session => session.Id == sessionId, cancellationToken);
            if (tableSession is null)
            {
                return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
            }

            if (!TableSessionCapability.IsValid(tableSession, suppliedToken, jwtOptions.Value.SigningKey))
            {
                return TableSessionCapability.Unauthorized();
            }

            var now = DateTimeOffset.UtcNow;
            if (!tableSession.IsActiveAt(now))
            {
                if (tableSession.ExpireIfPast(now))
                {
                    await db.SaveChangesAsync(cancellationToken);
                }

                return ApiErrorFactory.Result(
                    StatusCodes.Status410Gone,
                    "TABLE_SESSION_INACTIVE",
                    "Table session is closed or expired. Please scan QR again.");
            }

            var orders = await db.Orders
                .AsNoTracking()
                .Where(order => order.TableSessionId == tableSession.Id)
                .Include(order => order.OrderItems)
                .Include(order => order.Payment)
                .Include(order => order.StatusHistory)
                .OrderByDescending(order => order.CreatedAt)
                .ToListAsync(cancellationToken);

            return Results.Ok(new OrderListResponse(
                orders.Select(OrderEndpoints.ToResponse).ToList(),
                orders.Count));
        })
        .WithName("GetTableSessionOrders")
        .WithTags("Tables", "Orders");

        app.MapPost("/api/table-sessions/{sessionId}/close", async (
            string sessionId,
            RestaurantDbContext db,
            IChatStore chatStore,
            CancellationToken cancellationToken) =>
        {
            var session = await db.TableSessions
                .Include(s => s.RestaurantTable)
                .FirstOrDefaultAsync(s => s.Id == sessionId, cancellationToken);

            if (session is null)
            {
                return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
            }

            var now = DateTimeOffset.UtcNow;
            if (session.Status != TableSessionStatus.Closed)
            {
                session.Status = TableSessionStatus.Closed;
                session.ClosedAt = now;
                session.UpdatedAt = now;
                if (SingleUseQrEnabled && session.RestaurantTable is not null)
                {
                    TableQrTokenRotator.RotateTableQrToken(session.RestaurantTable);
                }

                await db.SaveChangesAsync(cancellationToken);
            }

            chatStore.DeleteSessionsByTableSession(session.Id);

            return Results.Ok(ToSessionResponse(session, now));
        })
        .RequireAuthorization("StaffOrAdmin")
        .WithName("CloseTableSession")
        .WithTags("Tables");

        return app;
    }

    private static async Task<IResult> OpenDineInSessionAsync(
        OpenTableSessionRequest request,
        RestaurantDbContext db,
        IChatStore chatStore,
        string signingKey,
        ILogger logger,
        CancellationToken cancellationToken)
    {
        var normalizedQrToken = NormalizeQrToken(request.QrToken);
        if (normalizedQrToken is null)
        {
            return ApiResults.BadRequest("QR_TOKEN_INVALID", "Dine-in sessions require a QR token.");
        }

        var now = DateTimeOffset.UtcNow;
        var table = await db.RestaurantTables
            .FirstOrDefaultAsync(t => t.QrToken == normalizedQrToken && t.IsActive, cancellationToken);

        if (table is null)
        {
            if (SingleUseQrEnabled)
            {
                var consumedSession = await db.TableSessions
                    .AsNoTracking()
                    .Include(session => session.RestaurantTable)
                    .FirstOrDefaultAsync(
                        session =>
                            session.QrToken == normalizedQrToken &&
                            session.RestaurantTable != null &&
                            session.RestaurantTable.IsActive &&
                            session.Status == TableSessionStatus.Open &&
                            session.ClosedAt == null &&
                            session.ExpiresAt > now,
                        cancellationToken);

                if (consumedSession is not null)
                {
                    return QrAlreadyUsedResult();
                }
            }

            return ApiResults.NotFound("QR_NOT_FOUND", "QR token does not match an active table.");
        }

        var normalizedTableCode = NormalizeTableCode(request.TableCode);
        if (!string.IsNullOrWhiteSpace(request.TableCode) && normalizedTableCode is null)
        {
            return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
        }

        if (normalizedTableCode is not null &&
            !table.TableCode.Equals(normalizedTableCode, StringComparison.OrdinalIgnoreCase))
        {
            return ApiResults.BadRequest("QR_TABLE_MISMATCH", "QR token does not belong to the requested table.");
        }

        var openGate = SessionOpenGates.GetOrAdd(table.Id, _ => new SemaphoreSlim(1, 1));
        await openGate.WaitAsync(cancellationToken);
        try
        {
            var expiredSessions = await db.TableSessions
                .Where(s =>
                    s.RestaurantTableId == table.Id &&
                    s.Status == TableSessionStatus.Open &&
                    s.ExpiresAt <= now)
                .ToListAsync(cancellationToken);

            foreach (var expiredSession in expiredSessions)
            {
                await MarkExpiredAsync(expiredSession, db, chatStore, now, cancellationToken);
            }

            var session = await FindActiveSessionAsync(db, table.Id, now, cancellationToken);
            var reusedSession = session is not null;

            if (reusedSession && SingleUseQrEnabled)
            {
                return QrAlreadyUsedResult();
            }

            if (session is null)
            {
                var newSession = new TableSession
                {
                    Id = $"ts_{Guid.NewGuid():N}",
                    RestaurantTableId = table.Id,
                    RestaurantTable = table,
                    TableCode = table.TableCode,
                    QrToken = normalizedQrToken,
                    OrderType = OrderType.DineIn,
                    Status = TableSessionStatus.Open,
                    OpenedAt = now,
                    ExpiresAt = now.Add(DefaultSessionLifetime),
                    CreatedAt = now,
                    UpdatedAt = now
                };
                db.TableSessions.Add(newSession);
                try
                {
                    await db.SaveChangesAsync(cancellationToken);
                    session = newSession;
                    if (SingleUseQrEnabled)
                    {
                        TableQrTokenRotator.RotateTableQrToken(table);
                        await db.SaveChangesAsync(cancellationToken);
                    }
                }
                catch (DbUpdateException)
                {
                    db.Entry(newSession).State = EntityState.Detached;
                    session = await FindActiveSessionAsync(db, table.Id, now, cancellationToken);
                    if (session is null)
                    {
                        throw;
                    }

                    if (SingleUseQrEnabled)
                    {
                        return QrAlreadyUsedResult();
                    }
                }
            }

            var resumeState = await ResolveResumeStateAsync(db, session!.Id, cancellationToken);
            logger.LogInformation(
                "Resolved table session {SessionId} for table {TableCode}; reused={ReusedSession}; resumeState={ResumeState}.",
                session.Id,
                table.TableCode,
                reusedSession,
                resumeState);

            return Results.Ok(ToOpenSessionResponse(session, now, signingKey, resumeState));
        }
        finally
        {
            openGate.Release();
        }
    }

    private static async Task<TableSessionResumeState> ResolveResumeStateAsync(
        RestaurantDbContext db,
        string tableSessionId,
        CancellationToken cancellationToken)
    {
        var cartItemCount = await db.TableSessionCartItems
            .AsNoTracking()
            .CountAsync(
                item => item.TableSessionId == tableSessionId && item.Quantity > 0,
                cancellationToken);
        var orderStatuses = await db.Orders
            .AsNoTracking()
            .Where(order => order.TableSessionId == tableSessionId)
            .Select(order => order.Status)
            .ToListAsync(cancellationToken);
        var invoiceStatus = await db.TableInvoices
            .AsNoTracking()
            .Where(invoice => invoice.TableSessionId == tableSessionId)
            .Select(invoice => (PaymentStatus?)invoice.Status)
            .FirstOrDefaultAsync(cancellationToken);

        return TableSessionResumeStateResolver.Resolve(cartItemCount, orderStatuses, invoiceStatus);
    }

    private static Task<TableSession?> FindActiveSessionAsync(
        RestaurantDbContext db,
        string tableId,
        DateTimeOffset now,
        CancellationToken cancellationToken)
    {
        return db.TableSessions
            .Include(session => session.RestaurantTable)
            .Where(session =>
                session.RestaurantTableId == tableId &&
                session.Status == TableSessionStatus.Open &&
                session.ClosedAt == null &&
                session.ExpiresAt > now)
            .OrderByDescending(session => session.OpenedAt)
            .FirstOrDefaultAsync(cancellationToken);
    }

    private static async Task MarkExpiredAsync(
        TableSession session,
        RestaurantDbContext db,
        IChatStore chatStore,
        DateTimeOffset now,
        CancellationToken cancellationToken)
    {
        if (!session.ExpireIfPast(now))
        {
            chatStore.DeleteSessionsByTableSession(session.Id);
            return;
        }

        await db.SaveChangesAsync(cancellationToken);
        chatStore.DeleteSessionsByTableSession(session.Id);
    }

    private static async Task<string?> AllocateNextTableCodeAsync(
        RestaurantDbContext db,
        CancellationToken cancellationToken)
    {
        var existingCodes = await db.RestaurantTables
            .AsNoTracking()
            .Select(table => table.TableCode)
            .ToListAsync(cancellationToken);

        for (var index = 1; index <= 99; index++)
        {
            var candidate = RestaurantTableSeed.FormatTableCode(index);
            if (!existingCodes.Contains(candidate, StringComparer.OrdinalIgnoreCase))
            {
                return candidate;
            }
        }

        return null;
    }

    private static async Task<IResult?> GetTableMutationBlockReasonAsync(
        RestaurantDbContext db,
        string tableId,
        CancellationToken cancellationToken)
    {
        var now = DateTimeOffset.UtcNow;
        var hasOpenSession = await db.TableSessions
            .AsNoTracking()
            .AnyAsync(
                session =>
                    session.RestaurantTableId == tableId &&
                    session.Status == TableSessionStatus.Open &&
                    session.ClosedAt == null &&
                    session.ExpiresAt > now,
                cancellationToken);
        if (hasOpenSession)
        {
            return ApiResults.Conflict(
                "TABLE_SESSION_OPEN",
                "Close the open table session before deactivating the table or rotating its QR code.");
        }

        var hasPendingInvoice = await (
            from invoice in db.TableInvoices.AsNoTracking()
            join session in db.TableSessions.AsNoTracking() on invoice.TableSessionId equals session.Id
            where invoice.Status == PaymentStatus.Pending && session.RestaurantTableId == tableId
            select invoice.Id).AnyAsync(cancellationToken);
        if (hasPendingInvoice)
        {
            return ApiResults.Conflict(
                "TABLE_INVOICE_PAYMENT_PENDING",
                "Complete or cancel the pending table invoice before deactivating the table or rotating its QR code.");
        }

        return null;
    }

    private static TableResponse ToPublicTableResponse(RestaurantTable table)
    {
        return new TableResponse(
            table.TableCode,
            table.DisplayName,
            table.IsActive);
    }

    private static AdminTableResponse ToAdminTableResponse(RestaurantTable table)
    {
        return new AdminTableResponse(
            table.TableCode,
            table.DisplayName,
            table.IsActive,
            table.QrToken,
            BuildCustomerPath(table.TableCode, table.QrToken));
    }

    private static TableSessionResponse ToSessionResponse(TableSession session, DateTimeOffset now)
    {
        return new TableSessionResponse(
            session.Id,
            session.OrderType.ToString(),
            session.Status.ToString(),
            session.TableCode,
            session.RestaurantTable?.DisplayName,
            session.OpenedAt,
            session.ExpiresAt,
            session.ClosedAt,
            IsExpired(session, now));
    }

    private static OpenTableSessionResponse ToOpenSessionResponse(
        TableSession session,
        DateTimeOffset now,
        string signingKey,
        TableSessionResumeState resumeState)
    {
        return new OpenTableSessionResponse(
            session.Id,
            session.OrderType.ToString(),
            session.Status.ToString(),
            session.TableCode,
            session.RestaurantTable?.DisplayName,
            session.OpenedAt,
            session.ExpiresAt,
            session.ClosedAt,
            IsExpired(session, now),
            TableSessionCapability.CreateToken(session, signingKey),
            resumeState.ToString());
    }

    private static bool IsExpired(TableSession session, DateTimeOffset now)
    {
        return session.Status == TableSessionStatus.Expired ||
               (session.Status == TableSessionStatus.Open && session.ExpiresAt <= now);
    }

    private static string? NormalizeTableCode(string? tableCode)
    {
        if (string.IsNullOrWhiteSpace(tableCode))
        {
            return null;
        }

        var normalized = tableCode.Trim().ToUpperInvariant();
        return TableCodeRegex().IsMatch(normalized) ? normalized : null;
    }

    private static string? NormalizeQrToken(string? qrToken)
    {
        return string.IsNullOrWhiteSpace(qrToken) ? null : qrToken.Trim();
    }

    private static string BuildCustomerPath(string? tableCode, string? qrToken)
    {
        if (string.IsNullOrWhiteSpace(tableCode) || string.IsNullOrWhiteSpace(qrToken))
        {
            return "/";
        }

        return $"/table/{Uri.EscapeDataString(tableCode)}?qr={Uri.EscapeDataString(qrToken)}";
    }

    private static IResult QrAlreadyUsedResult() =>
        ApiErrorFactory.Result(
            StatusCodes.Status410Gone,
            "QR_ALREADY_USED",
            "This table QR code has already been scanned. Continue on the device that opened the session, or ask staff for a new QR code.");

    [GeneratedRegex("^T(0[1-9]|[1-9][0-9])$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex TableCodeRegex();
}
