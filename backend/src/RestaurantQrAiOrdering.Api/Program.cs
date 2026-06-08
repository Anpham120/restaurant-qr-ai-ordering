using System.Text.Json;
using RestaurantQrAiOrdering.Api.Auth;
using RestaurantQrAiOrdering.Api.Chat;
using RestaurantQrAiOrdering.Api.Errors;
using RestaurantQrAiOrdering.Api.Orders;
using RestaurantQrAiOrdering.Api.Realtime;

const string CorsPolicyName = "CmcRestaurantCors";

var builder = WebApplication.CreateBuilder(args);
var defaultCorsOrigins = new[]
{
    "https://cmcrestaurant.app",
    "https://customer.cmcrestaurant.app",
    "https://admin.cmcrestaurant.app",
    "https://staging.cmcrestaurant.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173"
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
builder.Services.AddRestaurantAuth(builder.Configuration);
builder.Services.AddRestaurantMenuTableApis();
builder.Services.AddRestaurantOrderApis();
builder.Services.AddRestaurantRealtimeApis();
builder.Services.AddRestaurantChatApis();

var app = builder.Build();

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

app.Run();

public partial class Program;
