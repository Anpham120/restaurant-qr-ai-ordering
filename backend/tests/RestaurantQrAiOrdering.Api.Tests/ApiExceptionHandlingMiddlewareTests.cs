using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using RestaurantQrAiOrdering.Api.Errors;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class ApiExceptionHandlingMiddlewareTests
{
    [Fact]
    public async Task TestV27_UnhandledExceptionReturnsStructuredCorsResponse()
    {
        const string origin = "https://order.cmcrestaurant.app";
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Services.AddCors(options =>
        {
            options.AddPolicy("test", policy => policy
                .WithOrigins(origin)
                .AllowAnyHeader()
                .AllowAnyMethod());
        });

        await using var app = builder.Build();
        app.UseCors("test");
        app.UseMiddleware<ApiExceptionHandlingMiddleware>();
        app.MapPost(
            "/api/fail",
            (HttpContext _) => Task.FromException(new InvalidOperationException("diagnostic")));
        await app.StartAsync();

        using var request = new HttpRequestMessage(HttpMethod.Post, "/api/fail");
        request.Headers.Add("Origin", origin);
        using var response = await app.GetTestClient().SendAsync(request);
        using var body = JsonDocument.Parse(await response.Content.ReadAsStringAsync());

        Assert.Equal(HttpStatusCode.InternalServerError, response.StatusCode);
        Assert.Equal(origin, response.Headers.GetValues("Access-Control-Allow-Origin").Single());
        Assert.Equal("INTERNAL_ERROR", body.RootElement.GetProperty("error").GetProperty("code").GetString());
    }
}
