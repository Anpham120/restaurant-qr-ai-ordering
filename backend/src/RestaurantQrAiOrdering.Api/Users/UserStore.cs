namespace RestaurantQrAiOrdering.Api.Users;

public interface IUserStore
{
    RegisterUserResult RegisterCustomer(string fullName, string email, string password);

    UserAccount? ValidateCredentials(string email, string password);

    IReadOnlyList<UserAccount> ListUsers();

    CreateUserResult CreateUser(string fullName, string email, string password, string role);

    ChangePasswordResult ChangePassword(string userId, string currentPassword, string newPassword);

    ResetPasswordResult ResetPassword(string userId, string newPassword);

    long? GetSecurityStampTicks(string userId);

}

public sealed class UserStore : IUserStore
{
    private readonly object syncRoot = new();
    private readonly IPasswordHasher passwordHasher;
    private readonly IRoleCatalog roleCatalog;
    private readonly List<UserAccount> users = [];
    private int nextUserNumber = 1;

    public UserStore(IPasswordHasher passwordHasher, IRoleCatalog roleCatalog)
    {
        this.passwordHasher = passwordHasher;
        this.roleCatalog = roleCatalog;

        if (!roleCatalog.RoleExists(UserRole.Customer))
        {
            throw new InvalidOperationException("Customer role must be seeded.");
        }
    }

    public RegisterUserResult RegisterCustomer(string fullName, string email, string password)
    {
        var normalizedEmail = NormalizeEmail(email);
        lock (syncRoot)
        {
            if (users.Any(user => user.Email.Equals(normalizedEmail, StringComparison.OrdinalIgnoreCase)))
            {
                return RegisterUserResult.DuplicateEmail();
            }

            var now = DateTimeOffset.UtcNow;
            var user = new UserAccount
            {
                Id = $"usr_{nextUserNumber++:000}",
                FullName = fullName.Trim(),
                Email = normalizedEmail,
                PasswordHash = passwordHasher.HashPassword(password),
                Role = UserRole.Customer,
                CreatedAt = now
            };

            users.Add(user);

            return RegisterUserResult.Success(CloneUser(user));
        }
    }

    public UserAccount? ValidateCredentials(string email, string password)
    {
        var normalizedEmail = NormalizeEmail(email);
        lock (syncRoot)
        {
            var user = users.FirstOrDefault(user =>
                user.Email.Equals(normalizedEmail, StringComparison.OrdinalIgnoreCase));

            if (user is null || !passwordHasher.VerifyPassword(password, user.PasswordHash))
            {
                return null;
            }

            return CloneUser(user);
        }
    }

    public IReadOnlyList<UserAccount> ListUsers()
    {
        lock (syncRoot)
        {
            return users.Select(CloneUser).ToList();
        }
    }

    public CreateUserResult CreateUser(string fullName, string email, string password, string role)
    {
        var normalizedEmail = NormalizeEmail(email);
        lock (syncRoot)
        {
            if (users.Any(user => user.Email.Equals(normalizedEmail, StringComparison.OrdinalIgnoreCase)))
            {
                return CreateUserResult.DuplicateEmail();
            }

            var now = DateTimeOffset.UtcNow;
            var user = new UserAccount
            {
                Id = $"usr_{nextUserNumber++:000}",
                FullName = fullName.Trim(),
                Email = normalizedEmail,
                PasswordHash = passwordHasher.HashPassword(password),
                Role = role,
                CreatedAt = now
            };

            users.Add(user);

            return CreateUserResult.Success(CloneUser(user));
        }
    }

    public ChangePasswordResult ChangePassword(string userId, string currentPassword, string newPassword)
    {
        lock (syncRoot)
        {
            var index = users.FindIndex(user => user.Id == userId);
            if (index < 0)
            {
                return ChangePasswordResult.UserNotFound();
            }

            if (!passwordHasher.VerifyPassword(currentPassword, users[index].PasswordHash))
            {
                return ChangePasswordResult.InvalidCurrentPassword();
            }

            users[index] = WithPasswordHash(users[index], passwordHasher.HashPassword(newPassword));

            return ChangePasswordResult.Success();
        }
    }

    public ResetPasswordResult ResetPassword(string userId, string newPassword)
    {
        lock (syncRoot)
        {
            var index = users.FindIndex(user => user.Id == userId);
            if (index < 0)
            {
                return ResetPasswordResult.UserNotFound();
            }

            users[index] = WithPasswordHash(users[index], passwordHasher.HashPassword(newPassword));

            return ResetPasswordResult.Success();
        }
    }

    public long? GetSecurityStampTicks(string userId)
    {
        lock (syncRoot)
        {
            return users.FirstOrDefault(user => user.Id == userId)?.SecurityStampTicks;
        }
    }


    private static string NormalizeEmail(string email)
    {
        return email.Trim().ToLowerInvariant();
    }

    private static UserAccount CloneUser(UserAccount user)
    {
        return new UserAccount
        {
            Id = user.Id,
            FullName = user.FullName,
            Email = user.Email,
            PasswordHash = user.PasswordHash,
            Role = user.Role,
            CreatedAt = user.CreatedAt,
            SecurityStampTicks = user.SecurityStampTicks
        };
    }

    private static UserAccount WithPasswordHash(UserAccount user, string passwordHash)
    {
        return new UserAccount
        {
            Id = user.Id,
            FullName = user.FullName,
            Email = user.Email,
            PasswordHash = passwordHash,
            Role = user.Role,
            CreatedAt = user.CreatedAt,
            SecurityStampTicks = DateTimeOffset.UtcNow.UtcTicks
        };
    }
}

public sealed record RegisterUserResult(bool IsSuccess, bool IsDuplicateEmail, UserAccount? User)
{
    public static RegisterUserResult Success(UserAccount user)
    {
        return new RegisterUserResult(true, false, user);
    }

    public static RegisterUserResult DuplicateEmail()
    {
        return new RegisterUserResult(false, true, null);
    }
}

public sealed record CreateUserResult(bool IsSuccess, bool IsDuplicateEmail, UserAccount? User)
{
    public static CreateUserResult Success(UserAccount user)
    {
        return new CreateUserResult(true, false, user);
    }

    public static CreateUserResult DuplicateEmail()
    {
        return new CreateUserResult(false, true, null);
    }
}

public enum ChangePasswordOutcome
{
    Success,
    UserNotFound,
    InvalidCurrentPassword
}

public sealed record ChangePasswordResult(ChangePasswordOutcome Outcome)
{
    public static ChangePasswordResult Success()
    {
        return new ChangePasswordResult(ChangePasswordOutcome.Success);
    }

    public static ChangePasswordResult UserNotFound()
    {
        return new ChangePasswordResult(ChangePasswordOutcome.UserNotFound);
    }

    public static ChangePasswordResult InvalidCurrentPassword()
    {
        return new ChangePasswordResult(ChangePasswordOutcome.InvalidCurrentPassword);
    }
}

public enum ResetPasswordOutcome
{
    Success,
    UserNotFound
}

public sealed record ResetPasswordResult(ResetPasswordOutcome Outcome)
{
    public static ResetPasswordResult Success()
    {
        return new ResetPasswordResult(ResetPasswordOutcome.Success);
    }

    public static ResetPasswordResult UserNotFound()
    {
        return new ResetPasswordResult(ResetPasswordOutcome.UserNotFound);
    }
}
