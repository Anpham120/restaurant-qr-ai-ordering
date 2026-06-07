using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Auth;

public sealed class AuthEndpointTests
{
    [Fact]
    public async Task RegisterAndLogin_ReturnsJwtAccessToken()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        using var registerResponse = await RegisterCustomerAsync(client, email);
        using var registerBody = await JsonDocument.ParseAsync(await registerResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, registerResponse.StatusCode);
        Assert.Equal(email, registerBody.RootElement.GetProperty("email").GetString());
        Assert.Equal(UserRole.Customer, registerBody.RootElement.GetProperty("role").GetString());

        using var loginResponse = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email,
            password = "Password123!"
        });
        using var loginBody = await JsonDocument.ParseAsync(await loginResponse.Content.ReadAsStreamAsync());

        var accessToken = loginBody.RootElement.GetProperty("accessToken").GetString();
        var user = loginBody.RootElement.GetProperty("user");

        Assert.Equal(HttpStatusCode.OK, loginResponse.StatusCode);
        Assert.False(string.IsNullOrWhiteSpace(accessToken));
        Assert.Equal(3, accessToken!.Split('.').Length);
        Assert.Equal(email, user.GetProperty("email").GetString());
        Assert.Equal(UserRole.Customer, user.GetProperty("role").GetString());
    }

    [Fact]
    public async Task Login_RejectsInvalidCredentials()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        using var registerResponse = await RegisterCustomerAsync(client, email);
        Assert.Equal(HttpStatusCode.Created, registerResponse.StatusCode);

        using var response = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email,
            password = "WrongPassword123!"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        Assert.Equal("INVALID_CREDENTIALS", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task Register_RejectsEmptyFullName()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/auth/register", new
        {
            fullName = "",
            email = CreateUniqueEmail(),
            password = "Password123!"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("FULL_NAME_REQUIRED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task Register_RejectsInvalidEmail()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/auth/register", new
        {
            fullName = "Nguyen Van A",
            email = "invalid-email",
            password = "Password123!"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("EMAIL_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task Register_RejectsShortPassword()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/auth/register", new
        {
            fullName = "Nguyen Van A",
            email = CreateUniqueEmail(),
            password = "Short1"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("PASSWORD_TOO_SHORT", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task Register_RejectsDuplicateEmail()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        using var firstResponse = await RegisterCustomerAsync(client, email);
        using var duplicateResponse = await RegisterCustomerAsync(client, email);
        using var body = await JsonDocument.ParseAsync(await duplicateResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, firstResponse.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, duplicateResponse.StatusCode);
        Assert.Equal("EMAIL_ALREADY_REGISTERED", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task ProtectedEndpoint_RejectsUnauthenticatedRequest()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        using var response = await client.GetAsync("/api/auth/me");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task ProtectedEndpoint_ReturnsCurrentUserWithValidToken()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        using var registerResponse = await RegisterCustomerAsync(client, email);
        using var registerBody = await JsonDocument.ParseAsync(await registerResponse.Content.ReadAsStreamAsync());
        var userId = registerBody.RootElement.GetProperty("userId").GetString();
        var fullName = registerBody.RootElement.GetProperty("fullName").GetString();
        var role = registerBody.RootElement.GetProperty("role").GetString();
        var accessToken = await LoginAsync(client, email);

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        using var response = await client.GetAsync("/api/auth/me");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(userId, body.RootElement.GetProperty("userId").GetString());
        Assert.Equal(fullName, body.RootElement.GetProperty("fullName").GetString());
        Assert.Equal(email, body.RootElement.GetProperty("email").GetString());
        Assert.Equal(role, body.RootElement.GetProperty("role").GetString());
    }

    [Fact]
    public async Task ProtectedEndpoint_RejectsForgedToken()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", "invalid.token.here");
        using var response = await client.GetAsync("/api/auth/me");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task RoleRestrictedEndpoint_RejectsWrongRole()
    {
        await using var factory = new WebApplicationFactory<Program>();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();
        var accessToken = await RegisterAndLoginAsync(client, email);

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", accessToken);
        using var response = await client.GetAsync("/api/auth/admin-check");

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public void RoleCatalog_SeedsRequiredRoles()
    {
        using var factory = new WebApplicationFactory<Program>();

        var roles = factory.Services.GetRequiredService<IRoleCatalog>().GetRoles();

        Assert.Contains(UserRole.Customer, roles);
        Assert.Contains(UserRole.Staff, roles);
        Assert.Contains(UserRole.Kitchen, roles);
        Assert.Contains(UserRole.Admin, roles);
    }

    private static async Task<HttpResponseMessage> RegisterCustomerAsync(HttpClient client, string email)
    {
        return await client.PostAsJsonAsync("/api/auth/register", new
        {
            fullName = "Nguyen Van A",
            email,
            password = "Password123!"
        });
    }

    private static async Task<string> RegisterAndLoginAsync(HttpClient client, string email)
    {
        using var registerResponse = await RegisterCustomerAsync(client, email);
        Assert.Equal(HttpStatusCode.Created, registerResponse.StatusCode);

        using var loginResponse = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email,
            password = "Password123!"
        });
        using var loginBody = await JsonDocument.ParseAsync(await loginResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, loginResponse.StatusCode);

        return loginBody.RootElement.GetProperty("accessToken").GetString()!;
    }

    private static async Task<string> LoginAsync(HttpClient client, string email)
    {
        using var loginResponse = await client.PostAsJsonAsync("/api/auth/login", new
        {
            email,
            password = "Password123!"
        });
        using var loginBody = await JsonDocument.ParseAsync(await loginResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, loginResponse.StatusCode);

        return loginBody.RootElement.GetProperty("accessToken").GetString()!;
    }

    private static string CreateUniqueEmail()
    {
        return $"customer-{Guid.NewGuid():N}@example.com";
    }
}
