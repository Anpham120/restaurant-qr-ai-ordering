using RestaurantQrAiOrdering.Api.Categories;

namespace RestaurantQrAiOrdering.Api.Chat;

public static class ChatEndpoints
{
    public static IEndpointRouteBuilder MapChatEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/chat/sessions", (IChatStore chatStore) =>
        {
            var session = chatStore.CreateSession();
            return Results.Created(
                $"/api/chat/sessions/{session.Id}",
                new CreateChatSessionResponse(session.Id, session.CreatedAt));
        })
        .WithName("CreateChatSession")
        .WithTags("Chat");

        app.MapPost("/api/chat/sessions/{chatSessionId}/messages", async (
            string chatSessionId,
            SendChatMessageRequest request,
            IChatStore chatStore,
            IChatAssistantService assistant,
            CancellationToken cancellationToken) =>
        {
            if (string.IsNullOrWhiteSpace(request.Content))
            {
                return ApiResults.BadRequest("CHAT_MESSAGE_EMPTY", "Chat message content is required.");
            }

            if (chatStore.GetSession(chatSessionId) is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            var userMessage = chatStore.AddMessage(chatSessionId, "user", request.Content.Trim());
            if (userMessage is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            var history = chatStore.GetMessages(chatSessionId) ?? [];
            var assistantReply = await assistant.GenerateReplyAsync(userMessage.Content, history, cancellationToken);
            var assistantMessage = chatStore.AddMessage(
                chatSessionId,
                "assistant",
                assistantReply.Content,
                assistantReply.SuggestedCartActions);

            return assistantMessage is null
                ? ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.")
                : Results.Ok(new SendChatMessageResponse(
                    ToResponse(assistantMessage),
                    assistantReply.SuggestedCartActions,
                    assistantReply.GuardrailFlags));
        })
        .WithName("SendChatMessage")
        .WithTags("Chat");

        app.MapGet("/api/chat/sessions/{chatSessionId}/messages", (string chatSessionId, IChatStore chatStore) =>
        {
            var session = chatStore.GetSession(chatSessionId);
            if (session is null)
            {
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
