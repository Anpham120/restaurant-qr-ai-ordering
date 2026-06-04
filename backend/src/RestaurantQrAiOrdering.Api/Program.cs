var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenApi();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

app.UseHttpsRedirection();

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
