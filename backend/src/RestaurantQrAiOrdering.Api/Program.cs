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
using RestaurantQrAiOrdering.Entities;

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

if (!string.IsNullOrEmpty(connectionString))
{
    using var scope = app.Services.CreateScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();

    if (builder.Configuration.GetValue<bool>("RUN_DB_MIGRATIONS_ON_STARTUP"))
    {
        await dbContext.Database.MigrateAsync();
    }

    var hasher = scope.ServiceProvider.GetRequiredService<IPasswordHasher>();
    var nowUtc = DateTimeOffset.UtcNow;

    // Bootstrap a single real administrator from environment configuration only.
    // The account is created once when missing and is never reset on later boots,
    // so a rotated password stays rotated.
    var bootstrapEmail = builder.Configuration["BOOTSTRAP_ADMIN_EMAIL"];
    var bootstrapPassword = builder.Configuration["BOOTSTRAP_ADMIN_PASSWORD"];
    if (!string.IsNullOrWhiteSpace(bootstrapEmail) && !string.IsNullOrWhiteSpace(bootstrapPassword))
    {
        var adminExists = await dbContext.Users.AnyAsync(u => u.Email == bootstrapEmail);
        if (!adminExists)
        {
            dbContext.Users.Add(new User
            {
                Id = $"usr_{Guid.NewGuid():N}",
                FullName = "System Admin",
                Email = bootstrapEmail,
                PasswordHash = hasher.HashPassword(bootstrapPassword),
                Role = UserRole.Admin,
                CreatedAt = nowUtc,
                UpdatedAt = nowUtc
            });
            await dbContext.SaveChangesAsync();
        }
    }

    // Demo operational accounts are opt-in via SEED_DEMO_USERS and must stay disabled
    // in production. Each account is created only when missing; existing passwords are
    // never overwritten, so these are not a permanent reset-on-boot backdoor.
    if (builder.Configuration.GetValue<bool>("SEED_DEMO_USERS"))
    {
        var demoUsers = new[]
        {
            (Id: "usr_admin", Email: "admin@restaurant.local", Password: "Admin@1234", Role: UserRole.Admin, FullName: "Demo Admin"),
            (Id: "usr_staff", Email: "staff@restaurant.local", Password: "Staff@1234", Role: UserRole.Staff, FullName: "Demo Staff"),
            (Id: "usr_kitchen", Email: "kitchen@restaurant.local", Password: "Kitchen@1234", Role: UserRole.Kitchen, FullName: "Demo Kitchen"),
            (Id: "usr_customer_seed", Email: "customer@restaurant.local", Password: "Customer@1234", Role: UserRole.Customer, FullName: "Demo Customer"),
        };

        foreach (var demo in demoUsers)
        {
            var exists = await dbContext.Users.AnyAsync(u => u.Email == demo.Email);
            if (!exists)
            {
                dbContext.Users.Add(new User
                {
                    Id = demo.Id,
                    FullName = demo.FullName,
                    Email = demo.Email,
                    PasswordHash = hasher.HashPassword(demo.Password),
                    Role = demo.Role,
                    CreatedAt = nowUtc,
                    UpdatedAt = nowUtc
                });
            }
        }

        await dbContext.SaveChangesAsync();
    }
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
