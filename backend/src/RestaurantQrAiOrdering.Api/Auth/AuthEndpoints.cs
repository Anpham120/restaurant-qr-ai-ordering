using System.Security.Claims;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Auth;

public static class AuthEndpoints
{
    public static IEndpointRouteBuilder MapAuthEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/auth").WithTags("Auth");

        group.MapPost("/register", (RegisterRequest request, IUserStore users) =>
        {
            var validationError = ValidateRegisterRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var result = users.RegisterCustomer(request.FullName!, request.Email!, request.Password!);
            if (result.IsDuplicateEmail)
            {
                return AuthApiResults.Conflict("EMAIL_ALREADY_REGISTERED", "Email is already registered.");
            }

            var user = result.User!;
            return Results.Created(
                $"/api/users/{user.Id}",
                new RegisterResponse(user.Id, user.FullName, user.Email, user.Role));
        })
        .AllowAnonymous()
        .WithName("RegisterCustomer");

        group.MapPost("/login", (LoginRequest request, IUserStore users, IJwtTokenService jwtTokenService) =>
        {
            var validationError = ValidateLoginRequest(request);
            if (validationError is not null)
            {
                return validationError;
            }

            var user = users.ValidateCredentials(request.Email!, request.Password!);
            return user is null
                ? AuthApiResults.Unauthorized("INVALID_CREDENTIALS", "Email or password is incorrect.")
                : Results.Ok(jwtTokenService.CreateLoginResponse(user));
        })
        .AllowAnonymous()
        .WithName("Login");

        group.MapGet("/me", (ClaimsPrincipal principal) =>
        {
            return Results.Ok(ToAuthUserResponse(principal));
        })
        .RequireAuthorization()
        .WithName("GetCurrentUser");

        group.MapGet("/admin-check", () => Results.Ok(new
        {
            status = "Authorized",
            requiredRole = UserRole.Admin
        }))
        .RequireAuthorization("AdminOnly")
        .WithName("AdminAuthorizationCheck");

        return app;
    }

    private static IResult? ValidateRegisterRequest(RegisterRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.FullName))
        {
            return AuthApiResults.BadRequest("FULL_NAME_REQUIRED", "Full name is required.");
        }

        if (!IsValidEmail(request.Email))
        {
            return AuthApiResults.BadRequest("EMAIL_INVALID", "Email is invalid.");
        }

        if (string.IsNullOrWhiteSpace(request.Password) || request.Password.Length < 8)
        {
            return AuthApiResults.BadRequest("PASSWORD_TOO_SHORT", "Password must be at least 8 characters.");
        }

        return null;
    }

    private static IResult? ValidateLoginRequest(LoginRequest request)
    {
        if (!IsValidEmail(request.Email))
        {
            return AuthApiResults.BadRequest("EMAIL_INVALID", "Email is invalid.");
        }

        if (string.IsNullOrWhiteSpace(request.Password))
        {
            return AuthApiResults.BadRequest("PASSWORD_REQUIRED", "Password is required.");
        }

        return null;
    }

    private static bool IsValidEmail(string? email)
    {
        if (string.IsNullOrWhiteSpace(email))
        {
            return false;
        }

        try
        {
            var address = new System.Net.Mail.MailAddress(email);
            return address.Address.Equals(email.Trim(), StringComparison.OrdinalIgnoreCase);
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static AuthUserResponse ToAuthUserResponse(ClaimsPrincipal principal)
    {
        return new AuthUserResponse(
            principal.FindFirstValue(ClaimTypes.NameIdentifier) ?? string.Empty,
            principal.FindFirstValue(ClaimTypes.Name) ?? string.Empty,
            principal.FindFirstValue(ClaimTypes.Email) ?? string.Empty,
            principal.FindFirstValue(ClaimTypes.Role) ?? string.Empty);
    }
}
