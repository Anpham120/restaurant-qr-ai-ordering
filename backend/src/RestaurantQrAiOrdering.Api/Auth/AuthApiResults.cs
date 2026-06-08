namespace RestaurantQrAiOrdering.Api.Auth;

using RestaurantQrAiOrdering.Api.Errors;

public static class AuthApiResults
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

    public static IResult Conflict(string code, string message, object? details = null)
    {
        return ApiErrorFactory.Result(StatusCodes.Status409Conflict, code, message, details);
    }
}
