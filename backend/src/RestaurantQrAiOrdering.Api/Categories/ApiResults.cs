namespace RestaurantQrAiOrdering.Api.Categories;

public static class ApiResults
{
    public static IResult BadRequest(string code, string message, object? details = null)
    {
        return Error(StatusCodes.Status400BadRequest, code, message, details);
    }

    public static IResult NotFound(string code, string message, object? details = null)
    {
        return Error(StatusCodes.Status404NotFound, code, message, details);
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
