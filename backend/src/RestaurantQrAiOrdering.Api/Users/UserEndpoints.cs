using RestaurantQrAiOrdering.Api.Auth;

namespace RestaurantQrAiOrdering.Api.Users;

public static class UserEndpoints
{
    private static readonly string[] AssignableRoles = [UserRole.Staff, UserRole.Kitchen, UserRole.Admin];

    public static IEndpointRouteBuilder MapUserEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/users")
            .WithTags("Users")
            .RequireAuthorization("AdminOnly");

        group.MapGet("/", (IUserStore users) =>
        {
            var summaries = users.ListUsers()
                .Select(user => new UserSummaryResponse(user.Id, user.FullName, user.Email, user.Role, user.CreatedAt))
                .ToList();

            return Results.Ok(new UserListResponse(summaries));
        })
        .WithName("ListUsers");

        group.MapPost("/", (CreateUserRequest? request, IUserStore users, IRoleCatalog roleCatalog, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Users.UserEndpoints");
            var validationError = ValidateCreateUserRequest(request, roleCatalog);
            if (validationError is not null)
            {
                logger.LogWarning("Rejected admin user creation request during validation.");
                return validationError;
            }

            var validatedRequest = request!;
            var result = users.CreateUser(
                validatedRequest.FullName!,
                validatedRequest.Email!,
                validatedRequest.Password!,
                NormalizeRole(validatedRequest.Role!));

            if (result.IsDuplicateEmail)
            {
                logger.LogWarning("Rejected admin user creation because email {Email} already exists.", validatedRequest.Email);
                return AuthApiResults.Conflict("EMAIL_ALREADY_REGISTERED", "Email is already registered.");
            }

            var user = result.User!;
            logger.LogInformation("Admin created operational user {UserId} with role {Role}.", user.Id, user.Role);

            return Results.Created(
                $"/api/users/{user.Id}",
                new UserSummaryResponse(user.Id, user.FullName, user.Email, user.Role, user.CreatedAt));
        })
        .WithName("CreateUser");

        group.MapPost("/{userId}/reset-password", (string userId, ResetPasswordRequest? request, IUserStore users, ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Users.UserEndpoints");

            if (request is null)
            {
                return AuthApiResults.BadRequest("REQUEST_INVALID", "Request body is required.");
            }

            if (string.IsNullOrWhiteSpace(request.NewPassword) || request.NewPassword.Length < 8)
            {
                return AuthApiResults.BadRequest("PASSWORD_TOO_SHORT", "Password must be at least 8 characters.");
            }

            var result = users.ResetPassword(userId, request.NewPassword);
            if (result.Outcome == ResetPasswordOutcome.UserNotFound)
            {
                logger.LogWarning("Admin password reset failed because user {UserId} was not found.", userId);
                return AuthApiResults.NotFound("USER_NOT_FOUND", "User account was not found.");
            }

            logger.LogInformation("Admin reset password for user {UserId}.", userId);
            return Results.NoContent();
        })
        .WithName("ResetUserPassword");

        return app;
    }

    private static IResult? ValidateCreateUserRequest(CreateUserRequest? request, IRoleCatalog roleCatalog)
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

        if (string.IsNullOrWhiteSpace(request.Role) || !IsAssignableRole(request.Role, roleCatalog))
        {
            return AuthApiResults.BadRequest("ROLE_INVALID", "Role must be Staff, Kitchen, or Admin.");
        }

        return null;
    }

    private static bool IsAssignableRole(string role, IRoleCatalog roleCatalog)
    {
        return roleCatalog.RoleExists(role)
            && AssignableRoles.Any(assignable => assignable.Equals(role, StringComparison.OrdinalIgnoreCase));
    }

    private static string NormalizeRole(string role)
    {
        return AssignableRoles.First(assignable => assignable.Equals(role, StringComparison.OrdinalIgnoreCase));
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
}
