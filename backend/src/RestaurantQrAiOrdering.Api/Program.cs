using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.HttpOverrides;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Loyalty;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Payments;
using RestaurantQrAiOrdering.Api.Promotions;
using RestaurantQrAiOrdering.Api.Realtime;
using RestaurantQrAiOrdering.Api.Reports;
using RestaurantQrAiOrdering.Api.Users;
using RestaurantQrAiOrdering.Entities;

const string CorsPolicyName = "CmcRestaurantCors";

var builder = WebApplication.CreateBuilder(args);
var migrateOnly = args.Contains("--migrate-only", StringComparer.OrdinalIgnoreCase);
builder.WebHost.ConfigureKestrel(options => options.AddServerHeader = false);
var defaultCorsOrigins = new[]
{
    "https://cmcrestaurant.app",
    "https://order.cmcrestaurant.app",
    "https://customer.cmcrestaurant.app",
    "https://admin.cmcrestaurant.app",
    "https://staging.cmcrestaurant.app",
    "https://order-staging.cmcrestaurant.app",
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

if (!builder.Environment.IsDevelopment() && configuredCorsOrigins is not { Length: > 0 })
{
    throw new InvalidOperationException("CORS_ALLOWED_ORIGINS is required outside Development.");
}

builder.Services.AddOpenApi();
builder.Services.Configure<ForwardedHeadersOptions>(options =>
{
    options.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
    // Keep ASP.NET Core's loopback-only trusted proxy defaults. Clearing these
    // lists would let a direct client spoof X-Forwarded-For/X-Forwarded-Proto.
});
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
var useInMemory = string.IsNullOrEmpty(connectionString);

if (useInMemory && !builder.Environment.IsDevelopment())
{
    throw new InvalidOperationException("ConnectionStrings:DefaultConnection is required outside Development.");
}

if (!useInMemory)
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
else
{
    // Fallback: InMemory database for development without PostgreSQL
    builder.Services.AddDbContext<RestaurantDbContext>(options =>
    {
        options.UseInMemoryDatabase("RestaurantDev");
    });
}

if (!useInMemory)
{
    builder.Services.AddHealthChecks()
        .AddNpgSql(connectionString!, name: "postgresql", tags: ["db", "ready"]);
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

{
    using var scope = app.Services.CreateScope();
    var dbContext = scope.ServiceProvider.GetRequiredService<RestaurantDbContext>();

    if (migrateOnly)
    {
        if (useInMemory)
        {
            throw new InvalidOperationException("--migrate-only requires a PostgreSQL connection.");
        }

        await dbContext.Database.MigrateAsync();
        return;
    }

    if (!useInMemory && builder.Configuration.GetValue<bool>("RUN_DB_MIGRATIONS_ON_STARTUP"))
    {
        await dbContext.Database.MigrateAsync();
    }

    if (useInMemory)
    {
        await dbContext.Database.EnsureCreatedAsync();
    }

    // Predictable historical seed values are never allowed to reach a running API.
    await TableQrTokenRotator.RotateLegacyTokensAsync(dbContext);

    var hasher = scope.ServiceProvider.GetRequiredService<IPasswordHasher>();
    var nowUtc = DateTimeOffset.UtcNow;

    // Bootstrap a single real administrator from environment configuration only.
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

    // Demo accounts are allowed only in Development and all credentials must come
    // from local environment configuration. Tests seed their own isolated users.
    if (app.Environment.IsDevelopment() && builder.Configuration.GetValue<bool>("SEED_DEMO_USERS"))
    {
        var demoUsers = new[]
        {
            (Id: "usr_admin", Email: builder.Configuration["DEMO_ADMIN_EMAIL"], Password: builder.Configuration["DEMO_ADMIN_PASSWORD"], Role: UserRole.Admin, FullName: "Demo Admin"),
            (Id: "usr_staff", Email: builder.Configuration["DEMO_STAFF_EMAIL"], Password: builder.Configuration["DEMO_STAFF_PASSWORD"], Role: UserRole.Staff, FullName: "Demo Staff"),
            (Id: "usr_kitchen", Email: builder.Configuration["DEMO_KITCHEN_EMAIL"], Password: builder.Configuration["DEMO_KITCHEN_PASSWORD"], Role: UserRole.Kitchen, FullName: "Demo Kitchen"),
        };

        foreach (var demo in demoUsers)
        {
            if (string.IsNullOrWhiteSpace(demo.Email) || string.IsNullOrWhiteSpace(demo.Password))
            {
                throw new InvalidOperationException($"Development demo credentials are incomplete for role {demo.Role}.");
            }

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

app.UseForwardedHeaders();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}
else
{
    app.UseHsts();
}

app.UseHttpsRedirection();
app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["X-Frame-Options"] = "DENY";
    context.Response.Headers["Referrer-Policy"] = "no-referrer";
    context.Response.Headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()";
    if (context.Request.Path.StartsWithSegments("/api/auth"))
    {
        context.Response.Headers.CacheControl = "no-store";
    }

    await next();
});
app.UseCors(CorsPolicyName);
app.UseMiddleware<ApiExceptionHandlingMiddleware>();
app.UseAuthentication();
app.UseAuthorization();

app.MapAuthEndpoints();
app.MapUserEndpoints();
app.MapRestaurantMenuTableApis();
app.MapOrderEndpoints();
app.MapPaymentEndpoints();
app.MapPromotionEndpoints();
app.MapReportEndpoints();
app.MapLoyaltyEndpoints();
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

public partial class Program
{
}

public partial class Program;
