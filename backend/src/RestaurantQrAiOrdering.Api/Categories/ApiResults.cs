namespace RestaurantQrAiOrdering.Api.Categories;

using RestaurantQrAiOrdering.Api.Errors;

public static class ApiResults
{
    public static IResult BadRequest(string code, string message, object? details = null)
    {
        return ApiErrorFactory.Result(StatusCodes.Status400BadRequest, code, message, details);
    }

    public static IResult Unauthorized(string code, string message, object? details = null)
    {
        return ApiErrorFactory.Result(StatusCodes.Status401Unauthorized, code, message, details);
    }

    public static IResult Forbidden(string code, string message, object? details = null)
    {
        return ApiErrorFactory.Result(StatusCodes.Status403Forbidden, code, message, details);
    }

    public static IResult NotFound(string code, string message, object? details = null)
    {
        return ApiErrorFactory.Result(StatusCodes.Status404NotFound, code, message, details);
    }

    public static IResult Conflict(string code, string message, object? details = null)
    {
        return ApiErrorFactory.Result(StatusCodes.Status409Conflict, code, message, details);
    }
}
