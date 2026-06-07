namespace RestaurantQrAiOrdering.Api.Errors;

public static class ApiErrorFactory
{
    public static IResult Result(int statusCode, string code, string message, object? details = null)
    {
        return Results.Json(Create(code, message, details), statusCode: statusCode);
    }

    public static async Task WriteAsync(
        HttpResponse response,
        int statusCode,
        string code,
        string message,
        object? details = null)
    {
        response.StatusCode = statusCode;
        await response.WriteAsJsonAsync(Create(code, message, details));
    }

    private static object Create(string code, string message, object? details)
    {
        return new
        {
            error = new
            {
                code,
                message,
                details = details ?? new { }
            }
        };
    }
}
