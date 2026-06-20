using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Tests.Users;

public sealed class UserManagementEndpointTests
{
    private const string AdminEmail = "admin@restaurant.local";
    private const string AdminPassword = "Admin@1234";

    [Fact]
    public async Task ChangePassword_AllowsLoginWithNewPasswordAndRejectsOld()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        await RegisterCustomerAsync(client, email, "Password123!");
        var token = await LoginAsync(client, email, "Password123!");

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        using var changeResponse = await client.PostAsJsonAsync("/api/auth/change-password", new
        {
            currentPassword = "Password123!",
            newPassword = "NewPassword456!"
        });

        Assert.Equal(HttpStatusCode.NoContent, changeResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = null;
        using var oldLogin = await client.PostAsJsonAsync("/api/auth/login", new { email, password = "Password123!" });
        using var newLogin = await client.PostAsJsonAsync("/api/auth/login", new { email, password = "NewPassword456!" });

        Assert.Equal(HttpStatusCode.Unauthorized, oldLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, newLogin.StatusCode);
    }

    [Fact]
    public async Task ChangePassword_RejectsWrongCurrentPassword()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        await RegisterCustomerAsync(client, email, "Password123!");
        var token = await LoginAsync(client, email, "Password123!");

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        using var response = await client.PostAsJsonAsync("/api/auth/change-password", new
        {
            currentPassword = "WrongPassword!",
            newPassword = "NewPassword456!"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("CURRENT_PASSWORD_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task ChangePassword_RequiresAuthentication()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();

        using var response = await client.PostAsJsonAsync("/api/auth/change-password", new
        {
            currentPassword = "Password123!",
            newPassword = "NewPassword456!"
        });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task CreateUser_AsAdmin_CreatesStaffAccountThatCanLogin()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();
        var adminToken = await LoginAsync(client, AdminEmail, AdminPassword);
        var staffEmail = CreateUniqueEmail();

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);
        using var createResponse = await client.PostAsJsonAsync("/api/users", new
        {
            fullName = "Nhan Vien Moi",
            email = staffEmail,
            password = "StaffPass123!",
            role = UserRole.Staff
        });
        using var createBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.Created, createResponse.StatusCode);
        Assert.Equal(UserRole.Staff, createBody.RootElement.GetProperty("role").GetString());
        Assert.Equal(staffEmail, createBody.RootElement.GetProperty("email").GetString());

        client.DefaultRequestHeaders.Authorization = null;
        using var staffLogin = await client.PostAsJsonAsync("/api/auth/login", new { email = staffEmail, password = "StaffPass123!" });
        using var staffBody = await JsonDocument.ParseAsync(await staffLogin.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, staffLogin.StatusCode);
        Assert.Equal(UserRole.Staff, staffBody.RootElement.GetProperty("user").GetProperty("role").GetString());
    }

    [Fact]
    public async Task CreateUser_RejectsCustomerRole()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();
        var adminToken = await LoginAsync(client, AdminEmail, AdminPassword);

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);
        using var response = await client.PostAsJsonAsync("/api/users", new
        {
            fullName = "Khach Hang",
            email = CreateUniqueEmail(),
            password = "Customer123!",
            role = UserRole.Customer
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("ROLE_INVALID", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task CreateUser_RejectsNonAdminCaller()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        await RegisterCustomerAsync(client, email, "Password123!");
        var token = await LoginAsync(client, email, "Password123!");

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        using var response = await client.PostAsJsonAsync("/api/users", new
        {
            fullName = "Nhan Vien",
            email = CreateUniqueEmail(),
            password = "StaffPass123!",
            role = UserRole.Staff
        });

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    [Fact]
    public async Task ResetPassword_AsAdmin_AllowsLoginWithNewPassword()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();
        var adminToken = await LoginAsync(client, AdminEmail, AdminPassword);
        var staffEmail = CreateUniqueEmail();

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);
        using var createResponse = await client.PostAsJsonAsync("/api/users", new
        {
            fullName = "Nhan Vien Reset",
            email = staffEmail,
            password = "StaffPass123!",
            role = UserRole.Kitchen
        });
        using var createBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var userId = createBody.RootElement.GetProperty("userId").GetString();

        using var resetResponse = await client.PostAsJsonAsync($"/api/users/{userId}/reset-password", new
        {
            newPassword = "ResetPass789!"
        });

        Assert.Equal(HttpStatusCode.NoContent, resetResponse.StatusCode);

        client.DefaultRequestHeaders.Authorization = null;
        using var oldLogin = await client.PostAsJsonAsync("/api/auth/login", new { email = staffEmail, password = "StaffPass123!" });
        using var newLogin = await client.PostAsJsonAsync("/api/auth/login", new { email = staffEmail, password = "ResetPass789!" });

        Assert.Equal(HttpStatusCode.Unauthorized, oldLogin.StatusCode);
        Assert.Equal(HttpStatusCode.OK, newLogin.StatusCode);
    }

    [Fact]
    public async Task ResetPassword_RejectsUnknownUser()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();
        var adminToken = await LoginAsync(client, AdminEmail, AdminPassword);

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);
        using var response = await client.PostAsJsonAsync("/api/users/usr_missing/reset-password", new
        {
            newPassword = "ResetPass789!"
        });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        Assert.Equal("USER_NOT_FOUND", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }

    [Fact]
    public async Task ListUsers_AsAdmin_ReturnsSeededAdmin()
    {
        await using var factory = new TestWebApplicationFactory();
        await factory.SeedDatabaseAsync();
        using var client = factory.CreateClient();
        var adminToken = await LoginAsync(client, AdminEmail, AdminPassword);

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", adminToken);
        using var response = await client.GetAsync("/api/users");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var emails = body.RootElement.GetProperty("users")
            .EnumerateArray()
            .Select(user => user.GetProperty("email").GetString())
            .ToList();
        Assert.Contains(AdminEmail, emails);
    }

    [Fact]
    public async Task ListUsers_RejectsNonAdminCaller()
    {
        await using var factory = new TestWebApplicationFactory();
        using var client = factory.CreateClient();
        var email = CreateUniqueEmail();

        await RegisterCustomerAsync(client, email, "Password123!");
        var token = await LoginAsync(client, email, "Password123!");

        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        using var response = await client.GetAsync("/api/users");

        Assert.Equal(HttpStatusCode.Forbidden, response.StatusCode);
    }

    private static async Task RegisterCustomerAsync(HttpClient client, string email, string password)
    {
        using var response = await client.PostAsJsonAsync("/api/auth/register", new
        {
            fullName = "Nguyen Van A",
            email,
            password
        });
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    }

    private static async Task<string> LoginAsync(HttpClient client, string email, string password)
    {
        using var response = await client.PostAsJsonAsync("/api/auth/login", new { email, password });
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        return body.RootElement.GetProperty("accessToken").GetString()!;
    }

    private static string CreateUniqueEmail()
    {
        return $"user-{Guid.NewGuid():N}@example.com";
    }
}
