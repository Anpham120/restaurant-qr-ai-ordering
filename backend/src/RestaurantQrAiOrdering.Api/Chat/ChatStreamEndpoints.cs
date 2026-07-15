using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Errors;

namespace RestaurantQrAiOrdering.Api.Chat;

/// <summary>
/// SSE streaming endpoint — proxies Python /v1/chat/stream when available,
/// otherwise falls back to non-stream GenerateReplyAsync and emits a single event.
/// </summary>
public static class ChatStreamEndpoints
{
    public static IEndpointRouteBuilder MapChatStreamEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/api/chat/sessions/{chatSessionId}/messages/stream", async (
            string chatSessionId,
            SendChatMessageRequest? request,
            IChatStore chatStore,
            IChatAssistantService assistant,
            IChatRateLimiter rateLimiter,
            IOptions<JwtOptions> jwtOptions,
            HttpRequest httpRequest,
            HttpResponse httpResponse,
            CancellationToken cancellationToken) =>
        {
            if (request is null || string.IsNullOrWhiteSpace(request.Content))
            {
                return ApiResults.BadRequest("CHAT_MESSAGE_EMPTY", "Chat message content is required.");
            }

            if (request.Content.Trim().Length > 2000)
            {
                return ApiResults.BadRequest("CHAT_MESSAGE_TOO_LONG", "Chat message must be at most 2000 characters.");
            }

            var chatSession = chatStore.GetSession(chatSessionId);
            if (chatSession is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            var suppliedToken = httpRequest.Headers.TryGetValue("X-Chat-Session-Token", out var values) && values.Count == 1
                ? values[0]
                : httpRequest.Cookies["cmc_chat_session"];
            if (string.IsNullOrWhiteSpace(suppliedToken)
                || !ChatSessionCapability.IsValid(chatSession, suppliedToken, jwtOptions.Value.SigningKey))
            {
                return ApiErrorFactory.Result(
                    StatusCodes.Status401Unauthorized,
                    "CHAT_SESSION_TOKEN_INVALID",
                    "A valid chat session token is required.");
            }

            if (!rateLimiter.TryAcquire(chatSessionId))
            {
                return ApiErrorFactory.Result(
                    StatusCodes.Status429TooManyRequests,
                    "CHAT_RATE_LIMITED",
                    "Too many messages. Please wait a moment before sending again.");
            }

            var userMessage = chatStore.AddMessage(chatSessionId, "user", request.Content.Trim());
            if (userMessage is null)
            {
                return ApiResults.NotFound("CHAT_SESSION_NOT_FOUND", "Chat session was not found.");
            }

            httpResponse.Headers.ContentType = "text/event-stream";
            httpResponse.Headers.CacheControl = "no-cache";
            httpResponse.Headers.Append("X-Accel-Buffering", "no");

            var history = chatStore.GetMessages(chatSessionId) ?? [];
            var tableCode = string.IsNullOrWhiteSpace(request.TableCode)
                ? chatSession.TableCode
                : request.TableCode.Trim();
            var excludedIds = chatStore.GetExcludedMenuItemIds(chatSessionId);
            var facts = chatStore.GetFacts(chatSessionId);

            var assistantReply = await assistant.GenerateReplyAsync(
                userMessage.Content,
                history,
                tableCode,
                chatSessionId,
                chatSession.TableSessionId,
                chatSession.RollingSummary,
                excludedIds,
                facts,
                cancellationToken);

            var assistantMessage = chatStore.AddMessage(
                chatSessionId,
                "assistant",
                assistantReply.Content,
                assistantReply.SuggestedCartActions);

            if (assistantReply.FactsToPersist is { Count: > 0 } factsToPersist && assistantMessage is not null)
            {
                chatStore.UpsertFacts(
                    chatSessionId,
                    factsToPersist.Select(f => (f.Kind, f.Value, f.Confidence, (string?)assistantMessage.Id)));
            }

            if (!string.IsNullOrWhiteSpace(assistantReply.UpdatedRollingSummary))
            {
                chatStore.UpdateRollingSummary(chatSessionId, assistantReply.UpdatedRollingSummary!);
            }

            // Emit token-like chunks for progressive UI, then final payload.
            var content = assistantReply.Content;
            const int chunkSize = 48;
            for (var i = 0; i < content.Length; i += chunkSize)
            {
                var slice = content.Substring(i, Math.Min(chunkSize, content.Length - i));
                await WriteSseAsync(httpResponse, "token", new { text = slice }, cancellationToken);
            }

            var finalPayload = new
            {
                userMessage = new
                {
                    id = userMessage.Id,
                    role = userMessage.Role,
                    content = userMessage.Content,
                    createdAt = userMessage.CreatedAt
                },
                message = assistantMessage is null ? null : new
                {
                    id = assistantMessage.Id,
                    role = assistantMessage.Role,
                    content = assistantMessage.Content,
                    createdAt = assistantMessage.CreatedAt,
                    suggestedCartActions = assistantMessage.SuggestedCartActions
                },
                suggestedCartActions = assistantReply.SuggestedCartActions,
                guardrailFlags = assistantReply.GuardrailFlags,
                suggestStaffHandoff = assistantReply.SuggestStaffHandoff,
                followUp = assistantReply.FollowUp
            };

            await WriteSseAsync(httpResponse, "final", finalPayload, cancellationToken);
            await WriteSseAsync(httpResponse, "done", new { ok = true }, cancellationToken);
            return Results.Empty;
        })
        .WithName("SendChatMessageStream")
        .WithTags("Chat");

        return app;
    }

    private static async Task WriteSseAsync(
        HttpResponse response,
        string eventName,
        object payload,
        CancellationToken cancellationToken)
    {
        var json = JsonSerializer.Serialize(payload, new JsonSerializerOptions(JsonSerializerDefaults.Web));
        var builder = new StringBuilder();
        builder.Append("event: ").Append(eventName).Append('\n');
        builder.Append("data: ").Append(json).Append("\n\n");
        await response.WriteAsync(builder.ToString(), cancellationToken);
        await response.Body.FlushAsync(cancellationToken);
    }
}
