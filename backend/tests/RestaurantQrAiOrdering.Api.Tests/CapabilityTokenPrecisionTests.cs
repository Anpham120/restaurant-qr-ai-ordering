using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Tables;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class CapabilityTokenPrecisionTests
{
    private const string SigningKey = "test-signing-key-with-enough-entropy";

    [Fact]
    public void TestV28_TableCapabilitySurvivesPostgresTimestampPrecision()
    {
        var issued = CreateTableSession(DateTimeOffset.UtcNow.AddTicks(7));
        var token = TableSessionCapability.CreateToken(issued, SigningKey);
        var reloaded = CreateTableSession(TruncateToMicroseconds(issued.OpenedAt));
        reloaded.ExpiresAt = TruncateToMicroseconds(issued.ExpiresAt);

        Assert.True(TableSessionCapability.IsValid(reloaded, token, SigningKey));
    }

    [Fact]
    public void TestV28_ChatCapabilitySurvivesPostgresTimestampPrecision()
    {
        var createdAt = DateTimeOffset.UtcNow.AddTicks(7);
        var issued = new ChatSessionSnapshot(
            "chat_precision",
            "T01",
            createdAt,
            createdAt,
            [],
            "ts_precision");
        var token = ChatSessionCapability.CreateToken(issued, SigningKey);
        var reloaded = issued with
        {
            CreatedAt = TruncateToMicroseconds(issued.CreatedAt),
            UpdatedAt = TruncateToMicroseconds(issued.UpdatedAt)
        };

        Assert.True(ChatSessionCapability.IsValid(reloaded, token, SigningKey));
    }

    [Fact]
    public void TestV28_LegacyCapabilitiesRemainValidDuringDeployment()
    {
        var tableSession = CreateTableSession(DateTimeOffset.UtcNow);
        var legacyTableToken = CapabilityTokenSigner.CreateToken(
            SigningKey,
            "restaurant-qr-ai-ordering:table-session-capability:v1",
            $"{tableSession.Id}\n{tableSession.OpenedAt.UtcDateTime.Ticks}\n{tableSession.ExpiresAt.UtcDateTime.Ticks}");
        var chatSession = new ChatSessionSnapshot(
            "chat_legacy",
            "T01",
            DateTimeOffset.UtcNow,
            DateTimeOffset.UtcNow,
            [],
            tableSession.Id);
        var legacyChatToken = CapabilityTokenSigner.CreateToken(
            SigningKey,
            "restaurant-qr-ai-ordering:chat-session-capability:v1",
            $"{chatSession.Id}\n{chatSession.CreatedAt.UtcDateTime.Ticks}");

        Assert.True(TableSessionCapability.IsValid(tableSession, legacyTableToken, SigningKey));
        Assert.True(ChatSessionCapability.IsValid(chatSession, legacyChatToken, SigningKey));
    }

    private static TableSession CreateTableSession(DateTimeOffset openedAt) => new()
    {
        Id = "ts_precision",
        TableCode = "T01",
        QrToken = "qr_precision",
        OrderType = OrderType.DineIn,
        Status = TableSessionStatus.Open,
        OpenedAt = openedAt,
        ExpiresAt = openedAt.AddHours(1),
        CreatedAt = openedAt,
        UpdatedAt = openedAt
    };

    private static DateTimeOffset TruncateToMicroseconds(DateTimeOffset value) =>
        value.AddTicks(-(value.Ticks % 10));
}
