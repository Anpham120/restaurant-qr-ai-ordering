using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class CounterShiftAccessTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public CounterShiftAccessTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task CurrentShiftReturnsNullJsonWhenNoneOpen()
    {
        using var client = await CreateStaffClientAsync();
        await CloseAnyOpenShiftAsync(client);

        using var response = await client.GetAsync("/api/counter/shifts/current");
        response.EnsureSuccessStatusCode();
        var raw = (await response.Content.ReadAsStringAsync()).Trim();
        Assert.Equal("null", raw);
    }

    [Fact]
    public async Task StaffCanReadCurrentCounterShift()
    {
        using var client = await CreateStaffClientAsync();
        using var response = await client.GetAsync("/api/counter/shifts/current");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Fact]
    public async Task StaffCanOpenCounterShiftWhenNoneOpen()
    {
        using var client = await CreateStaffClientAsync();
        await CloseAnyOpenShiftAsync(client);

        using var response = await client.PostAsJsonAsync("/api/counter/shifts/open", new { openingCashBalance = 0m });
        response.EnsureSuccessStatusCode();
        using var payload = await ReadJsonAsync(response);
        Assert.Equal("Open", payload.RootElement.GetProperty("status").GetString());
    }

    private async Task<HttpClient> CreateStaffClientAsync()
    {
        using var adminClient = factory.CreateClient();
        var adminToken = await SignInAsAdminAsync(adminClient);
        adminClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);

        var staffEmail = $"staff-{Guid.NewGuid():N}@local.test";
        const string staffPassword = "StaffPass!2026";
        using var createUserResponse = await adminClient.PostAsJsonAsync("/api/users", new
        {
            fullName = "Floor Staff",
            email = staffEmail,
            password = staffPassword,
            role = "CounterStaff",
        });
        createUserResponse.EnsureSuccessStatusCode();

        var staffClient = factory.CreateClient();
        using var loginResponse = await staffClient.PostAsJsonAsync("/api/auth/login", new
        {
            email = staffEmail,
            password = staffPassword,
        });
        loginResponse.EnsureSuccessStatusCode();
        using var loginPayload = await ReadJsonAsync(loginResponse);
        staffClient.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            loginPayload.RootElement.GetProperty("accessToken").GetString());
        return staffClient;
    }

    private static async Task CloseAnyOpenShiftAsync(HttpClient client)
    {
        using var currentResponse = await client.GetAsync("/api/counter/shifts/current");
        currentResponse.EnsureSuccessStatusCode();
        var raw = await currentResponse.Content.ReadAsStringAsync();
        if (string.IsNullOrWhiteSpace(raw) || raw == "null")
        {
            return;
        }

        using var currentPayload = JsonDocument.Parse(raw);
        if (currentPayload.RootElement.ValueKind is JsonValueKind.Null)
        {
            return;
        }

        var shiftId = currentPayload.RootElement.GetProperty("shiftId").GetString();
        if (string.IsNullOrWhiteSpace(shiftId))
        {
            return;
        }

        using var closeResponse = await client.PostAsJsonAsync(
            $"/api/counter/shifts/{Uri.EscapeDataString(shiftId)}/close",
            new { actualCashTotal = 0m });
        closeResponse.EnsureSuccessStatusCode();
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
