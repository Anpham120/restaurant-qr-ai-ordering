using System.Security.Claims;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Auth;

public static class AuthEndpoints
{
    public static IEndpointRouteBuilder MapAuthEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/auth").WithTags("Auth");

        group.MapPost("/register", (RegisterRequest? request, IUserStore users, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Auth.AuthEndpoints");
            var validationError = ValidateRegisterRequest(request);
            if (validationError is not null)
            {
                logger.LogWarning("Rejected customer registration request during validation.");
                return validationError;
            }

            var validatedRequest = request!;
            var result = users.RegisterCustomer(validatedRequest.FullName!, validatedRequest.Email!, validatedRequest.Password!);
            if (result.IsDuplicateEmail)
            {
                logger.LogWarning("Rejected customer registration because email {Email} already exists.", validatedRequest.Email);
                return AuthApiResults.Conflict("EMAIL_ALREADY_REGISTERED", "Email is already registered.");
            }

            var user = result.User!;
            logger.LogInformation("Registered customer {UserId} with role {Role}.", user.Id, user.Role);

            return Results.Created(
                $"/api/users/{user.Id}",
                new RegisterResponse(user.Id, user.FullName, user.Email, user.Role));
        })
        .AllowAnonymous()
        .WithName("RegisterCustomer");

        group.MapPost("/login", (LoginRequest? request, IUserStore users, IJwtTokenService jwtTokenService, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Auth.AuthEndpoints");
            var validationError = ValidateLoginRequest(request);
            if (validationError is not null)
            {
                logger.LogWarning("Rejected login request during validation.");
                return validationError;
            }

            var validatedRequest = request!;
            var user = users.ValidateCredentials(validatedRequest.Email!, validatedRequest.Password!);
            if (user is null)
            {
                logger.LogWarning("Rejected login for email {Email} because credentials were invalid.", validatedRequest.Email);
                return AuthApiResults.Unauthorized("INVALID_CREDENTIALS", "Email or password is incorrect.");
            }

            logger.LogInformation("User {UserId} logged in with role {Role}.", user.Id, user.Role);

            return Results.Ok(jwtTokenService.CreateLoginResponse(user));
        })
        .AllowAnonymous()
        .WithName("Login");

        group.MapGet("/me", (ClaimsPrincipal principal) =>
        {
            return Results.Ok(ToAuthUserResponse(principal));
        })
        .RequireAuthorization()
        .WithName("GetCurrentUser");

        group.MapGet("/admin-check", (ClaimsPrincipal principal) =>
        {
            return Results.Ok(ToAuthUserResponse(principal));
        })
        .RequireAuthorization("AdminOnly")
        .WithName("AdminCheck");

        group.MapPost("/change-password", (ChangePasswordRequest? request, ClaimsPrincipal principal, IUserStore users, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Auth.AuthEndpoints");

            if (request is null)
            {
                return AuthApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            if (string.IsNullOrWhiteSpace(request.CurrentPassword))
            {
                return AuthApiResults.BadRequest("CURRENT_PASSWORD_REQUIRED", "Current password is required.");
            }

            if (string.IsNullOrWhiteSpace(request.NewPassword) || request.NewPassword.Length < 8)
            {
                return AuthApiResults.BadRequest("PASSWORD_TOO_SHORT", "Password must be at least 8 characters.");
            }

            var userId = principal.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrWhiteSpace(userId))
            {
                return AuthApiResults.Unauthorized("AUTHENTICATION_REQUIRED", "Authentication is required.");
            }

            var result = users.ChangePassword(userId, request.CurrentPassword, request.NewPassword);
            switch (result.Outcome)
            {
                case ChangePasswordOutcome.UserNotFound:
                    logger.LogWarning("Change-password failed because user {UserId} was not found.", userId);
                    return AuthApiResults.NotFound("USER_NOT_FOUND", "User account was not found.");
                case ChangePasswordOutcome.InvalidCurrentPassword:
                    logger.LogWarning("Change-password rejected for user {UserId} due to invalid current password.", userId);
                    return AuthApiResults.BadRequest("CURRENT_PASSWORD_INVALID", "Current password is incorrect.");
                default:
                    logger.LogInformation("User {UserId} changed their password.", userId);
                    return Results.NoContent();
            }
        })
        .RequireAuthorization()
        .WithName("ChangePassword");

        return app;
    }

    private static IResult? ValidateRegisterRequest(RegisterRequest? request)
    {
        if (request is null)
        {
            return AuthApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

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

    private static IResult? ValidateLoginRequest(LoginRequest? request)
    {
        if (request is null)
        {
            return AuthApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
        }

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
