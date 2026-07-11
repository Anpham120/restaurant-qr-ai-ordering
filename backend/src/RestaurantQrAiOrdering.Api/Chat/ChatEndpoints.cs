using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Errors;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatEndpoints
{
    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/chat/sessions", (
            CreateChatSessionRequest? request,
            IChatStore chatStore,
            IOptions<JwtOptions> jwtOptions,
            IWebHostEnvironment environment,
            HttpResponse httpResponse,
            ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Chat.ChatEndpoints");
            var session = chatStore.CreateSession(request?.TableCode, request?.TableSessionId);
            var accessToken = CreateAccessToken(session, jwtOptions.Value.SigningKey);
            httpResponse.Cookies.Append("cmc_chat_session", accessToken, new CookieOptions
            {
                HttpOnly = true,
                IsEssential = true,
                SameSite = SameSiteMode.Strict,
                Secure = !environment.IsDevelopment(),
                MaxAge = TimeSpan.FromHours(4)
            });
            logger.LogInformation("Created chat session {ChatSessionId}.", session.Id);

            return Results.Created(
                $"/api/chat/sessions/{session.Id}",
                new CreateChatSessionResponse(session.Id, session.CreatedAt, accessToken));
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

        try
        {
            var supplied = Base64Url.Decode(suppliedToken);
            return CryptographicOperations.FixedTimeEquals(supplied, CreateAccessTokenBytes(session, signingKey));
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static string CreateAccessToken(ChatSessionSnapshot session, string signingKey) =>
        Base64Url.Encode(CreateAccessTokenBytes(session, signingKey));

    private static byte[] CreateAccessTokenBytes(ChatSessionSnapshot session, string signingKey)
    {
        var purpose = Encoding.UTF8.GetBytes("restaurant-qr-ai-ordering:chat-session-capability:v1");
        var key = HMACSHA256.HashData(Encoding.UTF8.GetBytes(signingKey), purpose);
        return HMACSHA256.HashData(key, Encoding.UTF8.GetBytes($"{session.Id}\n{session.CreatedAt.UtcDateTime.Ticks}"));
    }

    private static IResult UnauthorizedChatCapability() => ApiErrorFactory.Result(
        StatusCodes.Status401Unauthorized,
        "CHAT_SESSION_TOKEN_INVALID",
        "A valid chat session token is required.");
}
