using System.Security.Claims;
using RestaurantQrAiOrdering.Api.Auth;

namespace RestaurantQrAiOrdering.Api.Users;

public static class UserEndpoints
{
    private static readonly string[] AssignableRoles = UserRole.All;

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
            logger.LogInformation("Admin created user {UserId} with role {Role}.", user.Id, user.Role);

            return Results.Created(
                $"/api/users/{user.Id}",
                new UserSummaryResponse(user.Id, user.FullName, user.Email, user.Role, user.CreatedAt));
        })
        .WithName("CreateUser");

        group.MapPut("/{userId}", (
            string userId,
            UpdateUserRequest? request,
            ClaimsPrincipal principal,
            IUserStore users,
            IRoleCatalog roleCatalog,
            ILoggerFactory loggerFactory) =>
        {
            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Users.UserEndpoints");
            var validationError = ValidateUpdateUserRequest(request, roleCatalog);
            if (validationError is not null)
            {
                logger.LogWarning("Rejected admin user update request during validation for user {UserId}.", userId);
                return validationError;
            }

            var validatedRequest = request!;
            var currentUserId = principal.FindFirstValue(ClaimTypes.NameIdentifier);
            var normalizedRole = NormalizeRole(validatedRequest.Role!);
            if (userId.Equals(currentUserId, StringComparison.Ordinal)
                && !normalizedRole.Equals(UserRole.Admin, StringComparison.Ordinal))
            {
                return AuthApiResults.BadRequest(
                    "CANNOT_REMOVE_OWN_ADMIN_ROLE",
                    "The current administrator cannot remove their own Admin role.");
            }

            var result = users.UpdateUser(
                userId,
                validatedRequest.FullName!,
                validatedRequest.Email!,
                normalizedRole);

            switch (result.Outcome)
            {
                case UpdateUserOutcome.UserNotFound:
                    return AuthApiResults.NotFound("USER_NOT_FOUND", "User account was not found.");
                case UpdateUserOutcome.DuplicateEmail:
                    return AuthApiResults.Conflict("EMAIL_ALREADY_REGISTERED", "Email is already registered.");
            }

            var user = result.User!;
            logger.LogInformation("Admin updated user {UserId} with role {Role}.", user.Id, user.Role);
            return Results.Ok(new UserSummaryResponse(user.Id, user.FullName, user.Email, user.Role, user.CreatedAt));
        })
        .WithName("UpdateUser");

        group.MapDelete("/{userId}", (string userId, ClaimsPrincipal principal, IUserStore users, ILoggerFactory loggerFactory) =>
        {
            var currentUserId = principal.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId.Equals(currentUserId, StringComparison.Ordinal))
            {
                return AuthApiResults.BadRequest(
                    "CANNOT_DELETE_CURRENT_USER",
                    "The current administrator cannot delete their own account.");
            }

            var result = users.DeleteUser(userId);
            if (result.Outcome == DeleteUserOutcome.UserNotFound)
            {
                return AuthApiResults.NotFound("USER_NOT_FOUND", "User account was not found.");
            }

            var logger = loggerFactory.CreateLogger("RestaurantQrAiOrdering.Api.Users.UserEndpoints");
            logger.LogInformation("Admin deleted user {UserId}.", userId);
            return Results.NoContent();
        })
        .WithName("DeleteUser");

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

    private static IResult? ValidateUpdateUserRequest(UpdateUserRequest? request, IRoleCatalog roleCatalog)
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

        if (string.IsNullOrWhiteSpace(request.Role) || !IsAssignableRole(request.Role, roleCatalog))
        {
            return AuthApiResults.BadRequest("ROLE_INVALID", "Role is invalid.");
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
