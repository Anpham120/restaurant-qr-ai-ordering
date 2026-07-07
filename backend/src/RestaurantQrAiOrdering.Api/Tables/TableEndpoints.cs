using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Tables;

public static partial class TableEndpoints
{
    private static readonly TimeSpan DefaultSessionLifetime = TimeSpan.FromHours(4);

    public static IEndpointRouteBuilder MapTableEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/tables", async (
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var tables = await db.RestaurantTables
                .AsNoTracking()
                .OrderBy(t => t.TableCode)
                .ToListAsync(cancellationToken);

            var items = tables
                .Select(ToTableResponse)
                .ToList();

            return Results.Ok(new TableListResponse(items, items.Count));
        })
        .WithName("ListTables")
        .WithTags("Tables");

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
        .RequireAuthorization(policy => policy.RequireRole(UserRole.Staff, UserRole.Admin))
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
                : Results.Ok(ToTableResponse(table));
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
                    table.DisplayName,
                    normalizedQrToken,
                    BuildCustomerPath(table.TableCode, normalizedQrToken)));
        })
        .WithName("ResolveTableQr")
        .WithTags("Tables");

        app.MapPost("/api/table-sessions", async (
            OpenTableSessionRequest? request,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            return await OpenDineInSessionAsync(request, db, cancellationToken);
        })
        .WithName("OpenTableSession")
        .WithTags("Tables");

        app.MapGet("/api/table-sessions/{sessionId}", async (
            string sessionId,
            RestaurantDbContext db,
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
            if (IsExpired(session, now))
            {
                await MarkExpiredAsync(session, db, now, cancellationToken);
                return ApiErrorFactory.Result(
                    StatusCodes.Status410Gone,
                    "TABLE_SESSION_EXPIRED",
                    "Table session has expired. Please scan QR again.");
            }

            return Results.Ok(ToSessionResponse(session, now));
        })
        .WithName("GetTableSession")
        .WithTags("Tables");

        app.MapPost("/api/table-sessions/{sessionId}/close", async (
            string sessionId,
            RestaurantDbContext db,
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
                await db.SaveChangesAsync(cancellationToken);
            }

            return Results.Ok(ToSessionResponse(session, now));
        })
        .WithName("CloseTableSession")
        .WithTags("Tables");

        return app;
    }

    private static async Task<IResult> OpenDineInSessionAsync(
        OpenTableSessionRequest request,
        RestaurantDbContext db,
        CancellationToken cancellationToken)
    {
        var normalizedQrToken = NormalizeQrToken(request.QrToken);
        if (normalizedQrToken is null)
        {
            return ApiResults.BadRequest("QR_TOKEN_INVALID", "Dine-in sessions require a QR token.");
        }

        var table = await db.RestaurantTables
            .FirstOrDefaultAsync(t => t.QrToken == normalizedQrToken && t.IsActive, cancellationToken);

        if (table is null)
        {
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

        var now = DateTimeOffset.UtcNow;
        var session = await db.TableSessions
            .Include(s => s.RestaurantTable)
            .Where(s =>
                s.RestaurantTableId == table.Id &&
                s.Status == TableSessionStatus.Open &&
                s.ClosedAt == null &&
                s.ExpiresAt > now)
            .OrderByDescending(s => s.OpenedAt)
            .FirstOrDefaultAsync(cancellationToken);

        if (session is null)
        {
            session = new TableSession
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
            db.TableSessions.Add(session);
            await db.SaveChangesAsync(cancellationToken);
        }

        return Results.Ok(ToSessionResponse(session, now));
    }

    private static async Task MarkExpiredAsync(
        TableSession session,
        RestaurantDbContext db,
        DateTimeOffset now,
        CancellationToken cancellationToken)
    {
        if (session.Status == TableSessionStatus.Expired)
        {
            return;
        }

        session.Status = TableSessionStatus.Expired;
        session.ClosedAt ??= now;
        session.UpdatedAt = now;
        await db.SaveChangesAsync(cancellationToken);
    }

    private static TableResponse ToTableResponse(RestaurantTable table)
    {
        return new TableResponse(
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
            session.QrToken,
            BuildCustomerPath(session.TableCode, session.QrToken),
            session.OpenedAt,
            session.ExpiresAt,
            session.ClosedAt,
            IsExpired(session, now));
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

    [GeneratedRegex("^T(0[1-9]|[1-9][0-9])$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex TableCodeRegex();
}
