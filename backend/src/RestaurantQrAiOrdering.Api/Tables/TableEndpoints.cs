using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Chat;
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
        .RequireAuthorization("AdminOnly")
        .WithName("AdminListTables")
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
            if (!TryGetTableSessionToken(request, out var suppliedToken))
            {
                return UnauthorizedSessionCapability();
            }

            var session = await db.TableSessions
                .Include(s => s.RestaurantTable)
                .FirstOrDefaultAsync(s => s.Id == sessionId, cancellationToken);

            if (session is null)
            {
                return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
            }

            if (!IsValidTableSessionToken(session, suppliedToken, jwtOptions.Value.SigningKey))
            {
                return UnauthorizedSessionCapability();
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

        return Results.Ok(ToOpenSessionResponse(session, now, signingKey));
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
        string signingKey)
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
            CreateTableSessionToken(session, signingKey));
    }

    private static bool TryGetTableSessionToken(HttpRequest request, out string token)
    {
        token = string.Empty;
        if (!request.Headers.TryGetValue("X-Table-Session-Token", out var values) || values.Count != 1)
        {
            return false;
        }

        var supplied = values[0];
        if (string.IsNullOrWhiteSpace(supplied))
        {
            return false;
        }

        token = supplied;
        return true;
    }

    private static bool IsValidTableSessionToken(
        TableSession session,
        string suppliedToken,
        string signingKey)
    {
        byte[] suppliedSignature;
        try
        {
            suppliedSignature = Base64Url.Decode(suppliedToken);
        }
        catch (FormatException)
        {
            return false;
        }

        var expectedSignature = CreateTableSessionSignature(session, signingKey);
        return CryptographicOperations.FixedTimeEquals(expectedSignature, suppliedSignature);
    }

    private static string CreateTableSessionToken(TableSession session, string signingKey)
    {
        return Base64Url.Encode(CreateTableSessionSignature(session, signingKey));
    }

    private static byte[] CreateTableSessionSignature(TableSession session, string signingKey)
    {
        if (string.IsNullOrWhiteSpace(signingKey))
        {
            throw new InvalidOperationException("JWT signing key is required for table session capabilities.");
        }

        var signingKeyBytes = Encoding.UTF8.GetBytes(signingKey);
        var purpose = Encoding.UTF8.GetBytes("restaurant-qr-ai-ordering:table-session-capability:v1");
        var purposeKey = HMACSHA256.HashData(signingKeyBytes, purpose);
        var payload = Encoding.UTF8.GetBytes(
            $"{session.Id}\n{session.OpenedAt.UtcDateTime.Ticks}\n{session.ExpiresAt.UtcDateTime.Ticks}");

        return HMACSHA256.HashData(purposeKey, payload);
    }

    private static IResult UnauthorizedSessionCapability()
    {
        return ApiErrorFactory.Result(
            StatusCodes.Status401Unauthorized,
            "TABLE_SESSION_TOKEN_INVALID",
            "A valid table session token is required.");
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
