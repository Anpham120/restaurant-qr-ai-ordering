namespace RestaurantQrAiOrdering.Api.Users;

public interface IUserStore
{
    RegisterUserResult RegisterCustomer(string fullName, string email, string password);

    UserAccount? ValidateCredentials(string email, string password);
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
            CreatedAt = user.CreatedAt
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
