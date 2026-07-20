using System.Net.Http.Json;
using System.Text.Json;

namespace RestaurantQrAiOrdering.Api.Tests;

internal static class TableSessionTestHelpers
{
    internal sealed record OpenTableSession(
        string Id,
        string TableCode,
        string QrToken,
        string Token);

    internal static async Task<OpenTableSession> OpenFreshTableSessionAsync(
        HttpClient client,
        int tableIndex = 0)
    {
        var (tableCode, _) = await ReadAdminTableAsync(client, tableIndex);
        await CloseOpenSessionsForTableAsync(client, tableCode);

        var (_, qrToken) = await ReadAdminTableAsync(client, tableIndex);
        using var sessionResponse = await client.PostAsJsonAsync("/api/table-sessions", new
        {
            qrToken,
            tableCode
        });
        sessionResponse.EnsureSuccessStatusCode();
        using var session = await ReadJsonAsync(sessionResponse);
        return new OpenTableSession(
            session.RootElement.GetProperty("sessionId").GetString()!,
            session.RootElement.GetProperty("tableCode").GetString()!,
            qrToken,
            session.RootElement.GetProperty("tableSessionToken").GetString()!);
    }

    private static async Task CloseOpenSessionsForTableAsync(HttpClient client, string tableCode)
    {
        using var sessionsResponse = await client.GetAsync("/api/admin/table-sessions?status=Open");
        sessionsResponse.EnsureSuccessStatusCode();
        using var sessions = await ReadJsonAsync(sessionsResponse);
        foreach (var item in sessions.RootElement.GetProperty("items").EnumerateArray())
        {
            if (!string.Equals(item.GetProperty("tableCode").GetString(), tableCode, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (item.TryGetProperty("isExpired", out var isExpiredElement) &&
                isExpiredElement.ValueKind == JsonValueKind.True)
            {
                continue;
            }

            var sessionId = item.GetProperty("sessionId").GetString()!;
            using var closeResponse = await client.PostAsync($"/api/table-sessions/{sessionId}/close", null);
            closeResponse.EnsureSuccessStatusCode();
        }
    }

    private static async Task<(string TableCode, string QrToken)> ReadAdminTableAsync(HttpClient client, int tableIndex)
    {
        using var tablesResponse = await client.GetAsync("/api/admin/tables");
        tablesResponse.EnsureSuccessStatusCode();
        using var tables = await ReadJsonAsync(tablesResponse);
        var table = tables.RootElement.GetProperty("items")[tableIndex];
        return (
            table.GetProperty("tableCode").GetString()!,
            table.GetProperty("qrToken").GetString()!);
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }
}
