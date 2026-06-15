using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Payments;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Users;

const string CorsPolicyName = "CmcRestaurantCors";

var builder = WebApplication.CreateBuilder(args);
var defaultCorsOrigins = new[]
{
    "https://cmcrestaurant.app",
    "https://admin.cmcrestaurant.app",
    "https://staging.cmcrestaurant.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:5178",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
    "http://127.0.0.1:5177",
    "http://127.0.0.1:5178"
};

var configuredCorsOrigins = builder.Configuration["CORS_ALLOWED_ORIGINS"]?
    .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

builder.Services.AddOpenApi();
builder.Services.AddCors(options =>
{
    options.AddPolicy(CorsPolicyName, policy =>
    {
        policy
            .WithOrigins(configuredCorsOrigins is { Length: > 0 } ? configuredCorsOrigins : defaultCorsOrigins)
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
if (!string.IsNullOrEmpty(connectionString))
{
    builder.Services.AddDbContext<RestaurantDbContext>(options =>
    {
        options.UseNpgsql(connectionString, npgsql =>
        {
            npgsql.EnableRetryOnFailure(
                maxRetryCount: 3,
                maxRetryDelay: TimeSpan.FromSeconds(10),
                errorCodesToAdd: null);
        });
    });
}

if (!string.IsNullOrEmpty(connectionString))
{
    builder.Services.AddHealthChecks()
        .AddNpgSql(connectionString, name: "postgresql", tags: ["db", "ready"]);
}
else
{
    builder.Services.AddHealthChecks();
}
builder.Services.AddRestaurantAuth(builder.Configuration);
builder.Services.AddRestaurantMenuTableApis();
builder.Services.AddRestaurantOrderApis();
builder.Services.AddRestaurantPaymentApis(builder.Configuration);
builder.Services.AddRestaurantRealtimeApis();
builder.Services.AddRestaurantChatApis();

var app = builder.Build();

if (!string.IsNullOrEmpty(connectionString)
    && builder.Configuration.GetValue<bool>("RUN_DB_MIGRATIONS_ON_STARTUP"))
{
    using var scope = app.Services.CreateScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();
    await dbContext.Database.MigrateAsync();

    // Keep demo operation accounts usable after database migrations in deployed environments.
    // Customer self-registration remains separate from these fixed operational accounts.
    var hasher = scope.ServiceProvider.GetRequiredService<IPasswordHasher>();
    var seedPasswords = new Dictionary<string, string>
    {
        ["admin@restaurant.local"] = "Admin@123",
        ["staff@restaurant.local"] = "Staff@123",
        ["kitchen@restaurant.local"] = "Kitchen@123",
        ["customer@restaurant.local"] = "Customer@123",
    };

    foreach (var (email, password) in seedPasswords)
    {
        var user = await dbContext.Users.FirstOrDefaultAsync(u => u.Email == email);
        if (user is not null && !hasher.VerifyPassword(password, user.PasswordHash))
        {
            user.PasswordHash = hasher.HashPassword(password);
        }
    }

    await dbContext.SaveChangesAsync();
}

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (Exception exception) when (exception is BadHttpRequestException or JsonException)
    {
        var logger = context.RequestServices
            .GetRequiredService<ILoggerFactory>()
            .CreateLogger("RestaurantQrAiOrdering.Api.RequestValidation");

        logger.LogWarning(
            exception,
            "Rejected invalid request body for {Method} {Path}.",
            context.Request.Method,
            context.Request.Path);

        if (context.Response.HasStarted)
        {
            throw;
        }

        await ApiErrorFactory.WriteAsync(
            context.Response,
            StatusCodes.Status400BadRequest,
            "REQUEST_INVALID",
            "Request body is invalid.");
    }
});
app.UseCors(CorsPolicyName);
app.UseAuthentication();
app.UseAuthorization();

app.MapAuthEndpoints();
app.MapRestaurantMenuTableApis();
app.MapOrderEndpoints();
app.MapPaymentEndpoints();
app.MapRestaurantRealtimeApis();
app.MapRestaurantChatApis();

app.MapGet("/api/health", () => Results.Ok(new
{
    status = "Healthy",
    service = "RestaurantQrAiOrdering.Api",
    environment = app.Environment.EnvironmentName,
    checkedAtUtc = DateTimeOffset.UtcNow
}))
.WithName("GetHealth")
.WithTags("Health");

app.MapHealthChecks("/health/live");
app.MapHealthChecks("/health/ready");

app.Run();

public partial class Program;
