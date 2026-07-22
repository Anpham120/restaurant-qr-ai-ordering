using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;
using RestaurantQrAiOrdering.Enums;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class AdminTableCrudTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public AdminTableCrudTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task AdminCanCreateUpdateAndRotateTableQr()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        using var createResponse = await client.PostAsJsonAsync("/api/admin/tables", new
        {
            tableCode = "T88",
            displayName = "Ban test 88",
        });
        createResponse.EnsureSuccessStatusCode();
        using var created = await ReadJsonAsync(createResponse);
        var initialToken = created.RootElement.GetProperty("qrToken").GetString();
        Assert.False(string.IsNullOrWhiteSpace(initialToken));

        using var updateResponse = await client.PatchAsJsonAsync("/api/admin/tables/T88", new
        {
            displayName = "Ban cap nhat",
        });
        updateResponse.EnsureSuccessStatusCode();
        using var updated = await ReadJsonAsync(updateResponse);
        Assert.Equal("Ban cap nhat", updated.RootElement.GetProperty("displayName").GetString());

        using var rotateResponse = await client.PostAsync("/api/admin/tables/T88/qr/rotate", null);
        rotateResponse.EnsureSuccessStatusCode();
        using var rotated = await ReadJsonAsync(rotateResponse);
        var rotatedToken = rotated.RootElement.GetProperty("qrToken").GetString();
        Assert.NotEqual(initialToken, rotatedToken);
    }

    [Fact]
    public async Task RotateQrBlockedWhileSessionOpen()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var tableSession = await TableSessionTestHelpers.OpenFreshTableSessionAsync(client);
        using var rotateResponse = await client.PostAsync(
            $"/api/admin/tables/{tableSession.TableCode}/qr/rotate",
            null);

        Assert.Equal(HttpStatusCode.Conflict, rotateResponse.StatusCode);
    }

    [Fact]
    public async Task DeactivateTableBlockedWhileSessionOpen()
    {
        using var client = factory.CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            await SignInAsAdminAsync(client));

        var tableSession = await TableSessionTestHelpers.OpenFreshTableSessionAsync(client);
        using var patchResponse = await client.PatchAsJsonAsync(
            $"/api/admin/tables/{tableSession.TableCode}",
            new { isActive = false });

        Assert.Equal(HttpStatusCode.Conflict, patchResponse.StatusCode);
    }

    [Fact]
    public async Task CounterStaffCanListTablesButCannotMutate()
    {
        using var adminClient = factory.CreateClient();
        var adminToken = await SignInAsAdminAsync(adminClient);
        adminClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);

        var counterEmail = $"counter-{Guid.NewGuid():N}@local.test";
        const string counterPassword = "CounterPass!2026";
        using var createUserResponse = await adminClient.PostAsJsonAsync("/api/users", new
        {
            fullName = "Counter Staff",
            email = counterEmail,
            password = counterPassword,
            role = "CounterStaff",
        });
        createUserResponse.EnsureSuccessStatusCode();

        using var counterClient = factory.CreateClient();
        using var loginResponse = await counterClient.PostAsJsonAsync("/api/auth/login", new
        {
            email = counterEmail,
            password = counterPassword,
        });
        loginResponse.EnsureSuccessStatusCode();
        using var loginPayload = await ReadJsonAsync(loginResponse);
        counterClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            loginPayload.RootElement.GetProperty("accessToken").GetString());

        using var listResponse = await counterClient.GetAsync("/api/admin/tables");
        listResponse.EnsureSuccessStatusCode();

        using var sessionsResponse = await counterClient.GetAsync("/api/admin/table-sessions");
        sessionsResponse.EnsureSuccessStatusCode();

        using var createTableResponse = await counterClient.PostAsJsonAsync("/api/admin/tables", new
        {
            tableCode = "T77",
            displayName = "Counter forbidden",
        });
        Assert.Equal(HttpStatusCode.Forbidden, createTableResponse.StatusCode);
    }

    private static async Task<string> SignInAsAdminAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email = RestaurantApiFactory.AdminEmail,
            password = RestaurantApiFactory.AdminPassword,
        });
        response.EnsureSuccessStatusCode();
        using var payload = await ReadJsonAsync(response);
        return payload.RootElement.GetProperty("accessToken").GetString()!;
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }
}
