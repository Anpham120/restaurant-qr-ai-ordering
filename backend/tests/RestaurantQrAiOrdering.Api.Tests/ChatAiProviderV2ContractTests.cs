using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class ChatAiProviderV2ContractTests
{
    [Fact]
    public async Task GenerateAsync_SerializesDefaultConversationFrameForNewPersistedState()
    {
        var handler = new RecordingHandler(_ => JsonResponse(MinimalResponse));
        var provider = CreateProvider(handler);
        var newSessionState = new ChatSessionStateSnapshot(
            [],
            new Dictionary<string, JsonElement>(),
            [],
            [],
            [],
            [],
            [],
            null,
            "v1",
            ConversationFrame: null);

        await provider.GenerateAsync(
            Request([], [Menu("m-1", "Pho", 85000)]) with
            {
                SessionState = newSessionState
            },
            CancellationToken.None);

        using var document = JsonDocument.Parse(Assert.Single(handler.RequestBodies));
        var frame = document.RootElement
            .GetProperty("session_state")
            .GetProperty("conversation_frame");

        Assert.Equal(JsonValueKind.Object, frame.ValueKind);
        Assert.Equal(0, frame.GetProperty("turn_sequence").GetInt32());
        Assert.Empty(frame.GetProperty("focus_menu_item_ids").EnumerateArray());
        Assert.Empty(frame.GetProperty("resolved_tags").EnumerateArray());
        Assert.Equal(JsonValueKind.Object, frame.GetProperty("constraint_provenance").ValueKind);
    }

    [Fact]
    public async Task GenerateAsync_ClassifiesUpstreamContractErrorsWithoutExposingDetails()
    {
        const string upstreamDetail = "conversation_frame must be an object";
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.UnprocessableEntity)
        {
            Content = new StringContent(
                $$"""{"detail":"{{upstreamDetail}}"}""",
                Encoding.UTF8,
                "application/json")
        });
        var provider = CreateProvider(handler);

        var result = await provider.GenerateAsync(
            Request([], [Menu("m-1", "Pho", 85000)]),
            CancellationToken.None);

        Assert.False(result.ProviderAvailable);
        Assert.Contains("AI_UPSTREAM_CONTRACT_ERROR", result.GuardrailFlags!);
        Assert.DoesNotContain(upstreamDetail, result.Content, StringComparison.Ordinal);
    }

    [Fact]
    public async Task GenerateStreamAsync_ClassifiesUpstreamContractErrors()
    {
        var handler = new RecordingHandler(_ => new HttpResponseMessage(HttpStatusCode.UnprocessableEntity)
        {
            Content = new StringContent(
                """{"detail":"conversation_frame must be an object"}""",
                Encoding.UTF8,
                "application/json")
        });
        var provider = CreateProvider(handler);
        JsonElement? final = null;

        await foreach (var streamEvent in provider.GenerateStreamAsync(
                           Request([], [Menu("m-1", "Pho", 85000)]),
                           CancellationToken.None))
        {
            if (streamEvent.EventType == "final")
            {
                final = streamEvent.Data;
            }
        }

        var payload = Assert.IsType<JsonElement>(final);
        Assert.Contains(
            payload.GetProperty("guardrail_flags").EnumerateArray(),
            flag => flag.GetString() == "AI_UPSTREAM_CONTRACT_ERROR");
    }

    [Fact]
    public async Task GenerateAsync_SendsBoundedTypedV2ContextWithDeterministicCatalogVersion()
    {
        var handler = new RecordingHandler(_ => JsonResponse(MinimalResponse));
        var provider = CreateProvider(handler);
        var history = Enumerable.Range(0, 14)
            .Select(index => new ChatMessageSnapshot(
                $"msg-{index}",
                "chat-1",
                index % 2 == 0 ? "user" : "assistant",
                $"turn {index}",
                DateTimeOffset.UnixEpoch.AddMinutes(index),
                index == 3
                    ? [new SuggestedCartActionResponse("m-1", "Pho", 85000, 1, "", true, "pending")]
                    : []))
            .ToList();
        var firstMenuOrder = new[]
        {
            Menu("m-2", "Bun cha", 79000),
            Menu("m-1", "Pho", 85000)
        };
        var secondMenuOrder = firstMenuOrder.Reverse().ToArray();

        await provider.GenerateAsync(
            Request(history, firstMenuOrder),
            CancellationToken.None);
        await provider.GenerateAsync(
            Request(history, secondMenuOrder),
            CancellationToken.None);
        await provider.GenerateAsync(
            Request(history, [Menu("m-2", "Bun cha", 79000), Menu("m-1", "Pho", 86000)]),
            CancellationToken.None);

        Assert.Equal(3, handler.RequestBodies.Count);
        using var first = JsonDocument.Parse(handler.RequestBodies[0]);
        using var second = JsonDocument.Parse(handler.RequestBodies[1]);
        using var changed = JsonDocument.Parse(handler.RequestBodies[2]);
        var root = first.RootElement;

        Assert.Equal("v2", root.GetProperty("contract_version").GetString());
        // Khong con gui `pipeline_profile`: khai niem "pipeline profile" da bi bo cung he thong
        // AI cu. Kiem no VANG chu khong xoa dong nay — mot truong bi bo phai co phep kiem canh,
        // neu khong thi no quay lai duoc ma khong ai thay.
        Assert.False(root.TryGetProperty("pipeline_profile", out _));
        var boundedHistory = root.GetProperty("history");
        Assert.Equal(12, boundedHistory.GetArrayLength());
        Assert.Equal("turn 2", boundedHistory[0].GetProperty("content").GetString());
        Assert.Equal("turn 13", boundedHistory[11].GetProperty("content").GetString());

        var state = root.GetProperty("session_state");
        Assert.Equal("Guest prefers soup.", state.GetProperty("rolling_summary").GetString());
        Assert.Equal("v1", state.GetProperty("memory_version").GetString());
        Assert.Equal("party_size", state.GetProperty("facts")[0].GetProperty("kind").GetString());
        Assert.Equal("4", state.GetProperty("facts")[0].GetProperty("value").GetString());
        Assert.Equal(JsonValueKind.Object, state.GetProperty("constraints").ValueKind);
        Assert.Contains("m-1", state.GetProperty("suggested_menu_item_ids")
            .EnumerateArray().Select(value => value.GetString()));
        Assert.Contains("m-9", state.GetProperty("suggested_menu_item_ids")
            .EnumerateArray().Select(value => value.GetString()));
        Assert.Empty(state.GetProperty("rejected_menu_item_ids").EnumerateArray());

        var liveContext = root.GetProperty("live_context");
        var catalogVersion = liveContext.GetProperty("catalog_version").GetString();
        Assert.False(string.IsNullOrWhiteSpace(catalogVersion));
        Assert.Equal(catalogVersion, root.GetProperty("catalog_version").GetString());
        Assert.Equal(catalogVersion, root.GetProperty("menu_version").GetString());
        Assert.Equal(catalogVersion,
            second.RootElement.GetProperty("live_context").GetProperty("catalog_version").GetString());
        Assert.NotEqual(catalogVersion,
            changed.RootElement.GetProperty("live_context").GetProperty("catalog_version").GetString());
        Assert.Equal(2, liveContext.GetProperty("menu_items").GetArrayLength());
        Assert.Equal("T01", liveContext.GetProperty("table_code").GetString());
        Assert.Equal(1, liveContext.GetProperty("cart_items").GetArrayLength());
        Assert.Contains("m-1", state.GetProperty("referenced_menu_item_ids")
            .EnumerateArray().Select(value => value.GetString()));
        Assert.Empty(state.GetProperty("accepted_menu_item_ids").EnumerateArray());
        Assert.Contains("m-1", state.GetProperty("added_to_cart_menu_item_ids")
            .EnumerateArray().Select(value => value.GetString()));
    }

    [Fact]
    public async Task GenerateAsync_UsesPersistedTypedStateWithoutReconstructingItFromHistory()
    {
        var handler = new RecordingHandler(_ => JsonResponse(MinimalResponse));
        var provider = CreateProvider(handler);
        var persistedState = new ChatSessionStateSnapshot(
            [new ChatSessionFactSnapshot("party_size", "8", 0.99, "turn-1")],
            new Dictionary<string, JsonElement>
            {
                ["diet"] = JsonSerializer.SerializeToElement("vegan")
            },
            ["m-reference"],
            ["m-suggested"],
            ["m-rejected"],
            ["m-accepted"],
            ["m-cart-ledger"],
            "Persisted summary",
            "v7",
            new ChatConversationFrame(
                "menu",
                "recommendation",
                ["m-reference"],
                "Noodles",
                ["soup"],
                3,
                null,
                new Dictionary<string, JsonElement>()));
        var request = Request([], [Menu("m-1", "Pho", 85000)]) with
        {
            SessionState = persistedState
        };

        await provider.GenerateAsync(request, CancellationToken.None);

        using var document = JsonDocument.Parse(Assert.Single(handler.RequestBodies));
        var state = document.RootElement.GetProperty("session_state");
        Assert.Equal("Persisted summary", state.GetProperty("rolling_summary").GetString());
        Assert.Equal("v7", state.GetProperty("memory_version").GetString());
        Assert.Equal("vegan", state.GetProperty("constraints").GetProperty("diet").GetString());
        Assert.Equal(["m-reference"], Strings(state, "referenced_menu_item_ids"));
        Assert.Equal(["m-suggested"], Strings(state, "suggested_menu_item_ids"));
        Assert.Equal(["m-rejected"], Strings(state, "rejected_menu_item_ids"));
        Assert.Equal(["m-accepted"], Strings(state, "accepted_menu_item_ids"));
        Assert.Equal(["m-cart-ledger", "m-1"], Strings(state, "added_to_cart_menu_item_ids"));
        Assert.Equal("recommendation",
            state.GetProperty("conversation_frame").GetProperty("active_intent").GetString());
        Assert.Equal(["m-reference"],
            Strings(state.GetProperty("conversation_frame"), "focus_menu_item_ids"));
    }

    [Fact]
    public async Task GenerateAsync_ParsesTypedV2ResponseAndPrefersSessionUpdatesOverLegacyFields()
    {
        var handler = new RecordingHandler(_ => JsonResponse(V2Response));
        var provider = CreateProvider(handler);

        var result = await provider.GenerateAsync(
            Request([], [Menu("m-1", "Pho", 85000)]),
            CancellationToken.None);

        Assert.Equal("party_size", Assert.Single(result.Facts!).Kind);
        Assert.Equal("4", Assert.Single(result.Facts!).Value);
        Assert.Equal(["m-2"], result.RejectedMenuItemIds);
        Assert.Equal("V2 summary", result.UpdatedRollingSummary);
        Assert.Equal("oc/deepseek-v4-flash-free", result.Model);
        Assert.Equal(["m-1"], result.ResolvedMenuItemIds);
        Assert.Equal("passed", result.VerifierResult);

        var decision = Assert.IsType<ChatDecisionTrace>(result.Decision);
        Assert.Equal("live_menu", decision.Route);
        Assert.Equal(0.91, decision.Confidence);
        Assert.True(decision.EvidenceSufficient);

        var evidence = Assert.Single(result.Evidence!);
        Assert.Equal("live_menu", evidence.Source);
        Assert.Equal("m-1", evidence.MenuItemId);
        Assert.Equal(1.0, evidence.Score);

        var claim = Assert.Single(result.Claims!);
        Assert.Equal("Pho is available.", claim.Text);
        Assert.True(claim.Verified);
        Assert.Equal(["m-1"], claim.EvidenceIds);

        var updates = Assert.IsType<ChatSessionUpdates>(result.SessionUpdates);
        Assert.Equal("v2", updates.MemoryVersion);
        Assert.Equal("V2 summary", updates.RollingSummary);
        Assert.Equal(["m-1"], updates.ReferencedMenuItemIds);
        Assert.Equal(["m-1"], updates.SuggestedMenuItemIds);
        Assert.Equal(["m-2"], updates.RejectedMenuItemIds);
        Assert.Equal(["m-3"], updates.AcceptedMenuItemIds);
        Assert.Equal(["m-4"], updates.AddedToCartMenuItemIds);
        Assert.Equal("lunch", updates.Constraints["meal"].GetString());
        var frame = Assert.IsType<ChatConversationFrame>(updates.ConversationFrame);
        Assert.Equal("recommendation", frame.ActiveIntent);
        Assert.Equal(["m-1"], frame.FocusMenuItemIds);
    }

    [Fact]
    public async Task GenerateAsync_KeepsLegacyStateFallbackWhenSessionUpdatesAreAbsent()
    {
        var handler = new RecordingHandler(_ => JsonResponse(LegacyResponse));
        var provider = CreateProvider(handler);

        var result = await provider.GenerateAsync(
            Request([], [Menu("m-1", "Pho", 85000)]),
            CancellationToken.None);

        var fact = Assert.Single(result.Facts!);
        Assert.Equal("legacy_fact", fact.Kind);
        Assert.Equal("kept", fact.Value);
        Assert.Equal(["m-legacy"], result.RejectedMenuItemIds);
        Assert.Equal("Legacy-only summary", result.UpdatedRollingSummary);
        Assert.Null(result.SessionUpdates);
    }

    [Fact]
    public async Task GenerateAsync_IgnoresMalformedOptionalV2FieldsWithoutThrowing()
    {
        var handler = new RecordingHandler(_ => JsonResponse(MalformedOptionalFieldsResponse));
        var provider = CreateProvider(handler);

        var result = await provider.GenerateAsync(
            Request([], [Menu("m-1", "Pho", 85000)]),
            CancellationToken.None);

        Assert.Equal("Safe content.", result.Content);
        Assert.Empty(result.SuggestedCartActions!);
        Assert.Null(result.Decision!.Confidence);
        Assert.Null(Assert.Single(result.Evidence!).Score);
        Assert.Equal(0.8, Assert.Single(result.Facts!).Confidence);
        Assert.Equal(0, result.FollowUp!.RemainingCount);
    }

    [Fact]
    public async Task StreamAndNonStream_RejectForgedTrustedTransitionsButPersistSafeV2State()
    {
        var handler = new RecordingHandler(request =>
            request.RequestUri!.AbsolutePath.EndsWith("/stream", StringComparison.Ordinal)
                ? StreamResponse(V2Response)
                : JsonResponse(V2Response));
        var provider = CreateProvider(handler);
        await using var db = CreateDatabase();
        using var cache = new MemoryCache(new MemoryCacheOptions());
        var service = new ChatAssistantService(
            db,
            provider,
            cache,
            NullLogger<ChatAssistantService>.Instance);

        var nonStream = await service.GenerateReplyAsync(
            "Recommend soup",
            [],
            "T01",
            "chat-1",
            null,
            "Prior summary",
            new HashSet<string>(StringComparer.OrdinalIgnoreCase),
            [],
            null,
            CancellationToken.None);

        ChatAssistantReply? streamed = null;
        await service.StreamReplyAsync(
            "Recommend soup",
            [],
            "T01",
            "chat-1",
            null,
            "Prior summary",
            new HashSet<string>(StringComparer.OrdinalIgnoreCase),
            [],
            null,
            (reply, _) =>
            {
                streamed = reply;
                return Task.CompletedTask;
            },
            (_, _) => Task.CompletedTask,
            CancellationToken.None);

        Assert.NotNull(streamed);
        Assert.Equal(nonStream.FactsToPersist, streamed!.FactsToPersist);
        Assert.Equal(nonStream.RejectedMenuItemIds, streamed.RejectedMenuItemIds);
        Assert.Equal(nonStream.UpdatedRollingSummary, streamed.UpdatedRollingSummary);
        Assert.NotNull(nonStream.SessionUpdates);
        Assert.NotNull(streamed.SessionUpdates);
        Assert.Equal(
            nonStream.SessionUpdates!.ReferencedMenuItemIds,
            streamed.SessionUpdates!.ReferencedMenuItemIds);
        Assert.Equal(
            nonStream.SessionUpdates.SuggestedMenuItemIds,
            streamed.SessionUpdates.SuggestedMenuItemIds);
        Assert.Equal(
            nonStream.SessionUpdates.RejectedMenuItemIds,
            streamed.SessionUpdates.RejectedMenuItemIds);
        Assert.Equal(
            nonStream.SessionUpdates.AcceptedMenuItemIds,
            streamed.SessionUpdates.AcceptedMenuItemIds);
        Assert.Equal(
            nonStream.SessionUpdates.AddedToCartMenuItemIds,
            streamed.SessionUpdates.AddedToCartMenuItemIds);
        Assert.Equal(nonStream.SessionUpdates.RollingSummary, streamed.SessionUpdates.RollingSummary);
        Assert.Equal(nonStream.SessionUpdates.MemoryVersion, streamed.SessionUpdates.MemoryVersion);
        Assert.Equal(["m-1"], nonStream.SessionUpdates!.ReferencedMenuItemIds);
        Assert.Empty(nonStream.SessionUpdates.AcceptedMenuItemIds);
        Assert.Empty(nonStream.SessionUpdates.AddedToCartMenuItemIds);
        Assert.Empty(streamed.SessionUpdates.AcceptedMenuItemIds);
        Assert.Empty(streamed.SessionUpdates.AddedToCartMenuItemIds);
        Assert.Equal("v2", nonStream.SessionUpdates.MemoryVersion);
        var nonStreamAction = Assert.Single(nonStream.SuggestedCartActions);
        var streamedAction = Assert.Single(streamed.SuggestedCartActions);
        Assert.Equal(nonStreamAction.MenuItemId, streamedAction.MenuItemId);
        Assert.Equal(nonStreamAction.Quantity, streamedAction.Quantity);
        Assert.Equal(nonStreamAction.EvidenceIds, streamedAction.EvidenceIds);

        ChatSessionStateSnapshot PersistThroughEndpointPath(ChatAssistantReply reply, string suffix)
        {
            var store = new DbChatStore(db);
            var session = store.CreateOrGetSession($"T-{suffix}").Session;
            store.UpsertRecommendations(
                session.Id,
                [
                    ($"trusted-accepted-{suffix}", "accepted", (string?)$"user-{suffix}"),
                    ($"trusted-cart-{suffix}", "added_to_cart", (string?)$"cart-{suffix}")
                ]);
            var user = Assert.IsType<ChatMessageSnapshot>(
                store.AddMessage(session.Id, "user", "Recommend soup"));
            var assistantMessage = Assert.IsType<ChatMessageSnapshot>(
                store.AddMessage(session.Id, "assistant", reply.Content, reply.SuggestedCartActions));
            ChatSessionStatePersistence.ApplyAssistantReply(
                store,
                session.Id,
                reply,
                assistantMessage.Id,
                user.Id);
            return Assert.IsType<ChatSessionStateSnapshot>(store.GetSessionState(session.Id));
        }

        var nonStreamState = PersistThroughEndpointPath(nonStream, "nonstream");
        var streamState = PersistThroughEndpointPath(streamed, "stream");
        foreach (var state in new[] { nonStreamState, streamState })
        {
            Assert.DoesNotContain("m-3", state.AcceptedMenuItemIds);
            Assert.DoesNotContain("m-4", state.AddedToCartMenuItemIds);
            Assert.Contains(state.AcceptedMenuItemIds, id => id.StartsWith("trusted-accepted-"));
            Assert.Contains(state.AddedToCartMenuItemIds, id => id.StartsWith("trusted-cart-"));
            Assert.Contains("m-1", state.ReferencedMenuItemIds);
            Assert.Contains("m-1", state.SuggestedMenuItemIds);
            Assert.Contains("m-2", state.RejectedMenuItemIds);
            Assert.Equal("v2", state.MemoryVersion);
        }
    }

    [Fact]
    public async Task StreamAndNonStream_ForwardTheSamePersistedTypedState()
    {
        var provider = new StateRecordingProvider();
        await using var db = CreateDatabase();
        using var cache = new MemoryCache(new MemoryCacheOptions());
        var service = new ChatAssistantService(
            db,
            provider,
            cache,
            NullLogger<ChatAssistantService>.Instance);
        var state = new ChatSessionStateSnapshot(
            [new ChatSessionFactSnapshot("party_size", "5", 1, "turn")],
            new Dictionary<string, JsonElement>
            {
                ["diet"] = JsonSerializer.SerializeToElement("vegan")
            },
            ["m-1"],
            ["m-1"],
            [],
            [],
            [],
            "State summary",
            "v3");

        await service.GenerateReplyAsync(
            "Use my saved preferences",
            [],
            "T01",
            "chat-1",
            null,
            state.RollingSummary,
            new HashSet<string>(StringComparer.OrdinalIgnoreCase),
            state.Facts,
            state,
            CancellationToken.None);
        await service.StreamReplyAsync(
            "Use my saved preferences",
            [],
            "T01",
            "chat-1",
            null,
            state.RollingSummary,
            new HashSet<string>(StringComparer.OrdinalIgnoreCase),
            state.Facts,
            state,
            (_, _) => Task.CompletedTask,
            (_, _) => Task.CompletedTask,
            CancellationToken.None);

        Assert.Equal(2, provider.Requests.Count);
        Assert.All(provider.Requests, request => Assert.Same(state, request.SessionState));
    }

    private static ChatAiRequest Request(
        IReadOnlyList<ChatMessageSnapshot> history,
        IReadOnlyList<ChatMenuItemContext> menuItems) =>
        new(
            "Recommend soup",
            history,
            menuItems,
            TableCode: "T01",
            SessionMemory: "bounded memory",
            ChatSessionId: "chat-1",
            TableSessionId: "table-session-1",
            RollingSummary: "Guest prefers soup.",
            ExcludedMenuItemIds: new HashSet<string>(["m-9"], StringComparer.OrdinalIgnoreCase),
            Facts: [new ChatSessionFactSnapshot("party_size", "4", 0.95, "turn-1")],
            CartItems: [new { menu_item_id = "m-1", quantity = 1 }],
            Orders: [new { order_code = "O-1", status = "Preparing" }],
            Promotions: [new { id = "promo-1", title = "Lunch" }],
            LocalTime: "2026-07-22T12:00:00+07:00",
            MealPeriod: "lunch");

    private static ChatMenuItemContext Menu(string id, string name, decimal price) =>
        new(id, name, $"{name} description", price, "cat-1", "Noodles", ["soup"], true);

    private static string[] Strings(JsonElement root, string property) => root
        .GetProperty(property)
        .EnumerateArray()
        .Select(value => value.GetString()!)
        .ToArray();

    private static PythonRagChatProvider CreateProvider(HttpMessageHandler handler)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["AI_SERVICE_URL"] = "https://ai.internal",
                ["AI_INTERNAL_TOKEN"] = "test-token"
            })
            .Build();
        return new PythonRagChatProvider(
            new HttpClient(handler),
            configuration,
            NullLogger<PythonRagChatProvider>.Instance);
    }

    private static RestaurantDbContext CreateDatabase()
    {
        var options = new DbContextOptionsBuilder<RestaurantDbContext>()
            .UseInMemoryDatabase($"chat-v2-{Guid.NewGuid():N}")
            .Options;
        var db = new RestaurantDbContext(options);
        db.Database.EnsureCreated();
        db.Categories.Add(new Category
        {
            Id = "cat-test-v2",
            Name = "Test V2",
            IsActive = true
        });
        db.MenuItems.Add(new MenuItem
        {
            Id = "m-1",
            CategoryId = "cat-test-v2",
            Name = "Pho",
            Description = "Soup",
            Price = 85000,
            IsAvailable = true,
            Tags = ["soup"]
        });
        db.SaveChanges();
        return db;
    }

    private static HttpResponseMessage JsonResponse(string json) => new(HttpStatusCode.OK)
    {
        Content = new StringContent(json, Encoding.UTF8, "application/json")
    };

    private static HttpResponseMessage StreamResponse(string finalJson)
    {
        using var document = JsonDocument.Parse(finalJson);
        var compactFinalJson = JsonSerializer.Serialize(document.RootElement);
        return new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                $"event: token\ndata: {{\"text\":\"Pho\"}}\n\n" +
                $"event: final\ndata: {compactFinalJson}\n\n" +
                "event: done\ndata: {\"ok\":true}\n\n",
                Encoding.UTF8,
                "text/event-stream")
        };
    }

    private const string MinimalResponse = """
        {
          "contract_version": "v2",
          "content": "OK",
          "provider_available": true,
          "model": "oc/deepseek-v4-flash-free",
          "pipeline_profile": "planner_state_v3",
          "resolved_menu_item_ids": ["m-1"],
          "verifier_result": "passed",
          "suggested_cart_actions": [],
          "guardrail_flags": []
        }
        """;

    private const string V2Response = """
        {
          "contract_version": "v2",
          "content": "Pho is available.",
          "provider_available": true,
          "model": "oc/deepseek-v4-flash-free",
          "pipeline_profile": "planner_state_v3",
          "resolved_menu_item_ids": ["m-1"],
          "verifier_result": "passed",
          "decision": {
            "intent": "menu_query",
            "route": "live_menu",
            "confidence": 0.91,
            "evidence_sufficient": true
          },
          "evidence": [
            {"source":"live_menu","title":"Pho","menu_item_id":"m-1","score":1.0}
          ],
          "claims": [
            {"text":"Pho is available.","evidence_ids":["m-1"],"verified":true}
          ],
          "session_updates": {
            "facts": [{"kind":"party_size","value":4,"confidence":0.95}],
            "constraints": {"meal":"lunch"},
            "referenced_menu_item_ids": ["m-1"],
            "suggested_menu_item_ids": ["m-1"],
            "rejected_menu_item_ids": ["m-2"],
            "accepted_menu_item_ids": ["m-3"],
            "added_to_cart_menu_item_ids": ["m-4"],
            "rolling_summary": "V2 summary",
            "memory_version": "v2",
            "conversation_frame": {
              "active_topic": "menu",
              "active_intent": "recommendation",
              "focus_menu_item_ids": ["m-1"],
              "resolved_category": "Noodles",
              "resolved_tags": ["soup"],
              "turn_sequence": 2,
              "pending_clarification": null,
              "constraint_provenance": {}
            }
          },
          "facts": [{"kind":"legacy","value":"ignored","confidence":0.1}],
          "rejected_menu_item_ids": ["legacy-rejected"],
          "updated_rolling_summary": "Legacy summary",
          "suggested_cart_actions": [
            {"menu_item_id":"m-1","name":"Pho","quantity":1,"reason":"Fits","evidence_ids":["m-1"]}
          ],
          "guardrail_flags": [],
          "follow_up": {"can_show_more":false,"remaining_count":0},
          "suggest_staff_handoff": false
        }
        """;

    private const string LegacyResponse = """
        {
          "content": "Legacy response.",
          "provider_available": true,
          "model": "legacy-test",
          "facts": [{"kind":"legacy_fact","value":"kept","confidence":0.8}],
          "rejected_menu_item_ids": ["m-legacy"],
          "updated_rolling_summary": "Legacy-only summary",
          "suggested_cart_actions": [],
          "guardrail_flags": []
        }
        """;

    private const string MalformedOptionalFieldsResponse = """
        {
          "contract_version": "v2",
          "content": "Safe content.",
          "provider_available": true,
          "model": "test",
          "decision": {"route":"live_menu","confidence":"high","evidence_sufficient":true},
          "evidence": [{"source":"live_menu","menu_item_id":"m-1","score":"one"}],
          "claims": [{"text":"Safe content.","evidence_ids":["m-1"],"verified":true}],
          "session_updates": {
            "facts": [{"kind":"party_size","value":4,"confidence":"certain"}],
            "rejected_menu_item_ids": [],
            "memory_version": "v2"
          },
          "suggested_cart_actions": [17, {"menu_item_id":42}],
          "guardrail_flags": [],
          "follow_up": {"can_show_more":false,"remaining_count":"many"}
        }
        """;

    private sealed class RecordingHandler(Func<HttpRequestMessage, HttpResponseMessage> responseFactory)
        : HttpMessageHandler
    {
        public List<string> RequestBodies { get; } = [];

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            RequestBodies.Add(await request.Content!.ReadAsStringAsync(cancellationToken));
            return responseFactory(request);
        }
    }

    private sealed class StateRecordingProvider : IChatAiProvider
    {
        public List<ChatAiRequest> Requests { get; } = [];

        public Task<ChatAiResult> GenerateAsync(
            ChatAiRequest request,
            CancellationToken cancellationToken)
        {
            Requests.Add(request);
            return Task.FromResult(new ChatAiResult("Safe reply", ProviderAvailable: true));
        }

        public async IAsyncEnumerable<ChatStreamEvent> GenerateStreamAsync(
            ChatAiRequest request,
            [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken cancellationToken)
        {
            Requests.Add(request);
            await Task.Yield();
            using var document = JsonDocument.Parse(MinimalResponse);
            yield return new ChatStreamEvent("final", document.RootElement.Clone());
            yield return new ChatStreamEvent(
                "done",
                JsonSerializer.SerializeToElement(new { ok = true }));
        }
    }
}
