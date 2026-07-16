using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatAdminEndpoints
{
    public static IEndpointRouteBuilder MapChatAdminEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/admin/chat/feedback", async (
            RestaurantDbContext db,
            string? rating,
            int take = 50,
            CancellationToken cancellationToken = default) =>
        {
            take = Math.Clamp(take, 1, 200);
            var query = db.ChatFeedbacks.AsNoTracking().AsQueryable();
            if (!string.IsNullOrWhiteSpace(rating))
            {
                var normalized = rating.Trim().ToLowerInvariant();
                query = query.Where(f => f.Rating == normalized);
            }

            var rows = await query
                .OrderByDescending(f => f.CreatedAt)
                .Take(take)
                .Join(
                    db.ChatMessages.AsNoTracking(),
                    f => f.MessageId,
                    m => m.Id,
                    (f, m) => new
                    {
                        f.Id,
                        f.ChatSessionId,
                        f.MessageId,
                        f.Rating,
                        f.Reason,
                        f.CreatedAt,
                        messageRole = m.Role,
                        messageContent = m.Content
                    })
                .ToListAsync(cancellationToken);

            var response = rows.Select(r => new
            {
                r.Id,
                r.ChatSessionId,
                r.MessageId,
                r.Rating,
                r.Reason,
                r.CreatedAt,
                r.messageRole,
                messagePreview = r.messageContent.Length > 240
                    ? r.messageContent.Substring(0, 240)
                    : r.messageContent
            });

            return Results.Ok(response);
        })
        .RequireAuthorization("AdminOnly")
        .WithName("AdminListChatFeedback")
        .WithTags("Admin Chat");

        return app;
    }
}
