namespace RestaurantQrAiOrdering.Api.Chat;

/// <summary>
/// Applies the final assistant state through one shared path so streaming and
/// non-streaming requests cannot drift. Legacy top-level fields remain supported
/// for one release when a V2 session_updates object is absent.
/// </summary>
public static class ChatSessionStatePersistence
{
    public static void ApplyAssistantReply(
        IChatStore chatStore,
        string chatSessionId,
        ChatAssistantReply reply,
        string? assistantTurnId,
        string? userTurnId)
    {
        if (reply.SessionUpdates is not null)
        {
            chatStore.ApplyAiSessionUpdates(
                chatSessionId,
                reply.SessionUpdates,
                assistantTurnId,
                userTurnId);
            return;
        }

        if (reply.FactsToPersist is { Count: > 0 } facts)
        {
            chatStore.UpsertFacts(
                chatSessionId,
                facts.Select(fact =>
                    (fact.Kind, fact.Value, fact.Confidence, assistantTurnId)));
        }

        if (!string.IsNullOrWhiteSpace(reply.UpdatedRollingSummary))
        {
            chatStore.UpdateRollingSummary(chatSessionId, reply.UpdatedRollingSummary);
        }

        if (reply.RejectedMenuItemIds is { Count: > 0 } rejectedIds)
        {
            chatStore.UpsertRecommendations(
                chatSessionId,
                rejectedIds.Select(id => (id, "rejected", userTurnId)));
        }
    }
}
