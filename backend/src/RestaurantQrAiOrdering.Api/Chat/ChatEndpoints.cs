using RestaurantQrAiOrdering.Api.Categories;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatEndpoints
{
    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/chat/sessions", (
            CreateChatSessionRequest? request,
            IChatStore chatStore,
            ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Chat.ChatEndpoints");
            var session = chatStore.CreateSession(request?.TableCode, request?.TableSessionId);
            logger.LogInformation("Created chat session {ChatSessionId}.", session.Id);

            return Results.Created(
                $"/api/chat/sessions/{session.Id}",
                new CreateChatSessionResponse(session.Id, session.CreatedAt));
        })
        .WithName("CreateChatSession")
        .WithTags("Chat");

        app.MapPost("/api/chat/sessions/{chatSessionId}/messages", async (
            string chatSessionId,
            SendChatMessageRequest? request,
            IChatStore chatStore,
            IChatAssistantService assistant,
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

        app.MapGet("/api/chat/sessions/{chatSessionId}/messages", (string chatSessionId, IChatStore chatStore, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Chat.ChatEndpoints");
            var session = chatStore.GetSession(chatSessionId);
            if (session is null)
            {
                logger.LogWarning("Rejected chat history request because session {ChatSessionId} was not found.", chatSessionId);
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
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
}
