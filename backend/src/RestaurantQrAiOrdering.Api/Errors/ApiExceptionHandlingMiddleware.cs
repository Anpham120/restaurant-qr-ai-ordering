using System.Text.Json;

namespace RestaurantQrAiOrdering.Api.Errors;

public sealed class ApiExceptionHandlingMiddleware
{
    private readonly RequestDelegate next;
    private readonly ILogger<ApiExceptionHandlingMiddleware> logger;

    public ApiExceptionHandlingMiddleware(
        RequestDelegate next,
        ILogger<ApiExceptionHandlingMiddleware> logger)
    {
        this.next = next;
        this.logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await next(context);
        }
        catch (Exception exception) when (exception is BadHttpRequestException or JsonException)
        {
            logger.LogWarning(
                exception,
                "Rejected invalid request body for {Method} {Path}.",
                context.Request.Method,
                context.Request.Path);

            await WriteErrorAsync(
                context,
                StatusCodes.Status400BadRequest,
                "REQUEST_INVALID",
                "Request body is invalid.");
        }
        catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
        {
            logger.LogDebug(
                "Request was cancelled by the client for {Method} {Path}.",
                context.Request.Method,
                context.Request.Path);
        }
        catch (Exception exception)
        {
            logger.LogError(
                exception,
                "Unhandled API exception for {Method} {Path}.",
                context.Request.Method,
                context.Request.Path);

            await WriteErrorAsync(
                context,
                StatusCodes.Status500InternalServerError,
                "INTERNAL_ERROR",
                "The server could not complete the request.");
        }
    }

    private static async Task WriteErrorAsync(
        HttpContext context,
        int statusCode,
        string code,
        string message)
    {
        if (context.Response.HasStarted)
        {
            throw new InvalidOperationException("The response already started before error handling completed.");
        }

        context.Response.Clear();
        await ApiErrorFactory.WriteAsync(context.Response, statusCode, code, message);
    }
}
