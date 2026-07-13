using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatEndpoints
{
    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/chat/sessions", async (
            CreateChatSessionRequest? request,
            IChatStore chatStore,
            RestaurantDbContext db,
            IOptions<JwtOptions> jwtOptions,
            IWebHostEnvironment environment,
            HttpResponse httpResponse,
            ILoggerFactory loggerFactory,
            CancellationToken cancellationToken) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Chat.ChatEndpoints");
            var tableSessionId = request?.TableSessionId?.Trim();
            var tableCode = request?.TableCode?.Trim();

            if (!string.IsNullOrWhiteSpace(tableSessionId))
            {
                var tableSession = await db.TableSessions
                    .FirstOrDefaultAsync(session => session.Id == tableSessionId, cancellationToken);
                if (tableSession is null)
                {
                    return ApiResults.NotFound("TABLE_SESSION_NOT_FOUND", "Table session was not found.");
                }

                var now = DateTimeOffset.UtcNow;
                if (!tableSession.IsActiveAt(now))
                {
                    if (tableSession.ExpireIfPast(now))
                    {
                        await db.SaveChangesAsync(cancellationToken);
                    }

                    chatStore.DeleteSessionsByTableSession(tableSession.Id);
                    return ApiErrorFactory.Result(
                        StatusCodes.Status410Gone,
                        "TABLE_SESSION_INACTIVE",
                        "Table session is closed or expired. Please scan QR again.");
                }

                if (!string.IsNullOrWhiteSpace(tableCode) &&
                    !string.Equals(tableSession.TableCode, tableCode, StringComparison.OrdinalIgnoreCase))
                {
                    return ApiResults.BadRequest("CHAT_TABLE_MISMATCH", "Table code does not match the table session.");
                }

                tableSessionId = tableSession.Id;
                tableCode = tableSession.TableCode;
            }

            var sessionResult = chatStore.CreateOrGetSession(tableCode, tableSessionId);
            var session = sessionResult.Session;
            var accessToken = ChatSessionCapability.CreateToken(session, jwtOptions.Value.SigningKey);
            httpResponse.Cookies.Append("cmc_chat_session", accessToken, new CookieOptions
            {
                HttpOnly = true,
                IsEssential = true,
                SameSite = SameSiteMode.Strict,
                Secure = !environment.IsDevelopment(),
                MaxAge = TimeSpan.FromHours(4)
            });
            logger.LogInformation(
                "{ChatSessionAction} chat session {ChatSessionId}.",
                sessionResult.Reused ? "Restored" : "Created",
                session.Id);

            var response = new CreateChatSessionResponse(
                session.Id,
                session.CreatedAt,
                session.UpdatedAt,
                accessToken,
                sessionResult.Reused,
                session.Messages.Select(ToResponse).ToList());

            return sessionResult.Reused
                ? Results.Ok(response)
                : Results.Created($"/api/chat/sessions/{session.Id}", response);
        })
        .WithName("CreateChatSession")
        .WithTags("Chat");

        app.MapPost("/api/chat/sessions/{chatSessionId}/messages", async (
            string chatSessionId,
            SendChatMessageRequest? request,
            IChatStore chatStore,
            IChatAssistantService assistant,
            IOptions<JwtOptions> jwtOptions,
            HttpRequest httpRequest,
            ILoggerFactory loggerFactory,
            CancellationToken cancellationToken) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Chat.ChatEndpoints");
            if (request is null)
            {
                logger.LogWarning("Rejected chat message for session {ChatSessionId} because request body is missing.", chatSessionId);
                return ApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            if (string.IsNullOrWhiteSpace(request.Content))
            {
                logger.LogWarning("Rejected empty chat message for session {ChatSessionId}.", chatSessionId);
                return ApiResults.BadRequest("CHAT_MESSAGE_EMPTY", "Chat message content is required.");
            }

            var chatSession = chatStore.GetSession(chatSessionId);
            if (chatSession is null)
            {
                logger.LogWarning("Rejected chat message because session {ChatSessionId} was not found.", chatSessionId);
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            if (!HasValidAccessToken(httpRequest, chatSession, jwtOptions.Value.SigningKey))
            {
                return UnauthorizedChatCapability();
            }

            var userMessage = chatStore.AddMessage(chatSessionId, "user", request.Content.Trim());
            if (userMessage is null)
            {
                logger.LogWarning("Rejected chat message because session {ChatSessionId} disappeared before storage.", chatSessionId);
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            var history = chatStore.GetMessages(chatSessionId) ?? [];
            var tableCode = string.IsNullOrWhiteSpace(request.TableCode)
                ? chatSession.TableCode
                : request.TableCode.Trim();
            var assistantReply = await assistant.GenerateReplyAsync(userMessage.Content, history, tableCode, cancellationToken);
            var assistantMessage = chatStore.AddMessage(
                chatSessionId,
                "assistant",
                assistantReply.Content,
                assistantReply.SuggestedCartActions);

            if (assistantMessage is null)
            {
                logger.LogWarning("Failed to store assistant reply because session {ChatSessionId} was not found.", chatSessionId);
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            logger.LogInformation(
                "Stored chat exchange for session {ChatSessionId} with {SuggestedActionCount} suggested actions and {GuardrailCount} guardrail flags.",
                chatSessionId,
                assistantReply.SuggestedCartActions.Count,
                assistantReply.GuardrailFlags.Count);

            return Results.Ok(new SendChatMessageResponse(
                ToResponse(userMessage),
                ToResponse(assistantMessage),
                assistantReply.SuggestedCartActions,
                assistantReply.GuardrailFlags));
        })
        .WithName("SendChatMessage")
        .WithTags("Chat");

        app.MapGet("/api/chat/sessions/{chatSessionId}/messages", (string chatSessionId, HttpRequest httpRequest, IChatStore chatStore, IOptions<JwtOptions> jwtOptions, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Chat.ChatEndpoints");
            var session = chatStore.GetSession(chatSessionId);
            if (session is null)
            {
                logger.LogWarning("Rejected chat history request because session {ChatSessionId} was not found.", chatSessionId);
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            if (!HasValidAccessToken(httpRequest, session, jwtOptions.Value.SigningKey))
            {
                return UnauthorizedChatCapability();
            }

            var response = new ChatHistoryResponse(
                session.Id,
                session.CreatedAt,
                session.UpdatedAt,
                session.Messages.Select(ToResponse).ToList());

            return Results.Ok(response);
        })
        .WithName("GetChatHistory")
        .WithTags("Chat");

        return app;
    }

    private static ChatMessageResponse ToResponse(ChatMessageSnapshot message)
    {
        return new ChatMessageResponse(
            message.Id,
            message.Role,
            message.Content,
            message.CreatedAt);
    }

    private static bool HasValidAccessToken(HttpRequest request, ChatSessionSnapshot session, string signingKey)
    {
        var suppliedToken = request.Headers.TryGetValue("X-Chat-Session-Token", out var values) && values.Count == 1
            ? values[0]
            : request.Cookies["cmc_chat_session"];
        if (string.IsNullOrWhiteSpace(suppliedToken))
        {
            return false;
        }

        return ChatSessionCapability.IsValid(session, suppliedToken, signingKey);
    }

    private static IResult UnauthorizedChatCapability() => ApiErrorFactory.Result(
        StatusCodes.Status401Unauthorized,
        "CHAT_SESSION_TOKEN_INVALID",
        "A valid chat session token is required.");
}
