using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatEndpoints
{
    private const int MaxMessageLength = 1000;

    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/chat/sessions", async (
            CreateChatSessionRequest? request,
            IChatStore chatStore,
            RestaurantDbContext db,
            CancellationToken cancellationToken) =>
        {
            var tableSessionId = NormalizeOptional(request?.TableSessionId);
            string? tableCode = null;
            if (tableSessionId is not null)
            {
                var now = DateTimeOffset.UtcNow;
                var tableSession = await db.TableSessions.AsNoTracking().FirstOrDefaultAsync(
                    session => session.Id == tableSessionId,
                    cancellationToken);
                if (tableSession is null)
                {
                    return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
                }
                if (tableSession.Status != TableSessionStatus.Open || tableSession.ExpiresAt <= now)
                {
                    return ApiErrorFactory.Result(
                        StatusCodes.Status410Gone,
                        "TABLE_SESSION_EXPIRED",
                        "Table session is closed or expired. Please scan the QR code again.");
                }
                tableCode = tableSession.TableCode;
            }
            else
            {
                tableCode = NormalizeOptional(request?.TableCode);
            }

            var (session, reused) = await chatStore.CreateOrGetSessionAsync(
                tableCode,
                tableSessionId,
                cancellationToken);
            return Results.Ok(new CreateChatSessionResponse(session.Id, session.CreatedAt, reused));
        })
        .WithName("CreateOrRestoreChatSession")
        .WithTags("Chat");

        app.MapPost("/api/chat/sessions/{chatSessionId}/messages", async (
            string chatSessionId,
            SendChatMessageRequest? request,
            IChatStore chatStore,
            IChatAssistantService assistant,
            CancellationToken cancellationToken) =>
        {
            if (request is null)
            {
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }
            var content = request.Content?.Trim();
            if (string.IsNullOrWhiteSpace(content))
            {
                return ApiResults.BadRequest("CHAT_MESSAGE_EMPTY", "Chat message content is required.");
            }
            if (content.Length > MaxMessageLength)
            {
                return ApiResults.BadRequest(
                    "CHAT_MESSAGE_TOO_LONG",
                    $"Chat message must not exceed {MaxMessageLength} characters.");
            }

            var session = await chatStore.GetSessionAsync(chatSessionId, cancellationToken);
            if (session is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            // Read history before persisting the current turn so the user message is
            // represented exactly once in the downstream prompt.
            var history = await chatStore.GetMessagesAsync(chatSessionId, 6, cancellationToken);
            var userMessage = await chatStore.AddMessageAsync(
                chatSessionId, "user", content, null, cancellationToken);
            if (userMessage is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            var reply = await assistant.GenerateReplyAsync(
                content,
                history,
                session.TableCode,
                cancellationToken);
            var assistantMessage = await chatStore.AddMessageAsync(
                chatSessionId,
                "assistant",
                reply.Content,
                reply.SuggestedCartActions,
                cancellationToken);
            if (assistantMessage is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            return Results.Ok(new SendChatMessageResponse(
                ToResponse(assistantMessage),
                reply.SuggestedCartActions,
                reply.GuardrailFlags,
                reply.Diagnostics));
        })
        .WithName("SendChatMessage")
        .WithTags("Chat");

        app.MapGet("/api/chat/sessions/{chatSessionId}/messages", async (
            string chatSessionId,
            IChatStore chatStore,
            CancellationToken cancellationToken) =>
        {
            var session = await chatStore.GetSessionAsync(chatSessionId, cancellationToken);
            if (session is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }
            var messages = await chatStore.GetMessagesAsync(chatSessionId, null, cancellationToken);
            return Results.Ok(new ChatHistoryResponse(
                session.Id,
                session.CreatedAt,
                session.UpdatedAt,
                messages.Select(ToResponse).ToList()));
        })
        .WithName("GetChatHistory")
        .WithTags("Chat");

        return app;
    }

    private static ChatMessageResponse ToResponse(ChatMessageSnapshot message) => new(
        message.Id,
        message.Role,
        message.Content,
        message.CreatedAt,
        message.SuggestedCartActions);

    private static string? NormalizeOptional(string? value) =>
        string.IsNullOrWhiteSpace(value) ? null : value.Trim();
}
