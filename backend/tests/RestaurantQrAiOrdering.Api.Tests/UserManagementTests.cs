using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class UserManagementTests : IClassFixture<RestaurantApiFactory>
{
    private readonly RestaurantApiFactory factory;

    public UserManagementTests(RestaurantApiFactory factory)
    {
        this.factory = factory;
    }

    [Fact]
    public async Task TestV42_AdminCanCreateUpdateAndDeleteUser()
    {
        using var client = factory.CreateClient();
        var session = await SignInAsAdminAsync(client);
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", session.AccessToken);
        var email = $"managed-{Guid.NewGuid():N}@local.test";

        using var createdResponse = await client.PostAsJsonAsync("/api/users", new
        {
            fullName = "Managed Customer",
            email,
            password = "ManagedPass!2026",
            role = "Customer"
        });
        Assert.Equal(HttpStatusCode.Created, createdResponse.StatusCode);
        using var created = await ReadJsonAsync(createdResponse);
        var userId = created.RootElement.GetProperty("userId").GetString()!;

        using var updatedResponse = await client.PutAsJsonAsync($"/api/users/{userId}", new
        {
            fullName = "Managed Staff",
            email = $"updated-{email}",
            role = "Staff"
        });
        Assert.Equal(HttpStatusCode.OK, updatedResponse.StatusCode);
        using var updated = await ReadJsonAsync(updatedResponse);
        Assert.Equal("Managed Staff", updated.RootElement.GetProperty("fullName").GetString());
        Assert.Equal("Staff", updated.RootElement.GetProperty("role").GetString());

        using var duplicateResponse = await client.PutAsJsonAsync($"/api/users/{userId}", new
        {
            fullName = "Managed Staff",
            email = RestaurantApiFactory.AdminEmail,
            role = "Staff"
        });
        Assert.Equal(HttpStatusCode.Conflict, duplicateResponse.StatusCode);
        Assert.Equal("EMAIL_ALREADY_REGISTERED", await ReadErrorCodeAsync(duplicateResponse));

        using var deletedResponse = await client.DeleteAsync($"/api/users/{userId}");
        Assert.Equal(HttpStatusCode.NoContent, deletedResponse.StatusCode);

        using var missingResponse = await client.DeleteAsync($"/api/users/{userId}");
        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
        Assert.Equal("USER_NOT_FOUND", await ReadErrorCodeAsync(missingResponse));
    }

    [Fact]
    public async Task TestV42_CurrentAdminCannotDeleteSelfOrRemoveOwnAdminRole()
    {
        using var client = factory.CreateClient();
        var session = await SignInAsAdminAsync(client);
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", session.AccessToken);

        using var deleteResponse = await client.DeleteAsync($"/api/users/{session.UserId}");
        Assert.Equal(HttpStatusCode.BadRequest, deleteResponse.StatusCode);
        Assert.Equal("CANNOT_DELETE_CURRENT_USER", await ReadErrorCodeAsync(deleteResponse));

        using var updateResponse = await client.PutAsJsonAsync($"/api/users/{session.UserId}", new
        {
            fullName = session.FullName,
            email = session.Email,
            role = "Staff"
        });
        Assert.Equal(HttpStatusCode.BadRequest, updateResponse.StatusCode);
        Assert.Equal("CANNOT_REMOVE_OWN_ADMIN_ROLE", await ReadErrorCodeAsync(updateResponse));
    }

    private static async Task<AdminSession> SignInAsAdminAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email = RestaurantApiFactory.AdminEmail,
            password = RestaurantApiFactory.AdminPassword
        });
        response.EnsureSuccessStatusCode();
        using var body = await ReadJsonAsync(response);
        var user = body.RootElement.GetProperty("user");
        return new AdminSession(
            body.RootElement.GetProperty("accessToken").GetString()!,
            user.GetProperty("userId").GetString()!,
            user.GetProperty("fullName").GetString()!,
            user.GetProperty("email").GetString()!);
    }

    private static async Task<string> ReadErrorCodeAsync(HttpResponseMessage response)
    {
        using var body = await ReadJsonAsync(response);
        return body.RootElement.GetProperty("error").GetProperty("code").GetString()!;
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response)
    {
        await using var stream = await response.Content.ReadAsStreamAsync();
        return await JsonDocument.ParseAsync(stream);
    }

    private sealed record AdminSession(string AccessToken, string UserId, string FullName, string Email);
}
