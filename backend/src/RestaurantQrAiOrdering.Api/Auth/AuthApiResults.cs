namespace RestaurantQrAiOrdering.Api.Auth;

public static class AuthApiResults
{
    public static IResult BadRequest(string code, string message, object? details = null)
    {
        return Error(StatusCodes.Status400BadRequest, code, message, details);
    }

    public static IResult Unauthorized(string code, string message, object? details = null)
    {
        return Error(StatusCodes.Status401Unauthorized, code, message, details);
    }

    public static IResult Conflict(string code, string message, object? details = null)
    {
        return Error(StatusCodes.Status409Conflict, code, message, details);
    }

    private static IResult Error(int statusCode, string code, string message, object? details)
    {
        return Results.Json(
            new
            {
                error = new
                {
                    code,
                    message,
                    details = details ?? new { }
                }
            },
            statusCode: statusCode);
    }
}
