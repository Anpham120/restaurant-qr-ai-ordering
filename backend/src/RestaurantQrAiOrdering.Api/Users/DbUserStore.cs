using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Users;

public sealed class DbUserStore : IUserStore
{
    private readonly RestaurantDbContext dbContext;
    private readonly IPasswordHasher passwordHasher;

    public DbUserStore(RestaurantDbContext dbContext, IPasswordHasher passwordHasher)
    {
        this.dbContext = dbContext;
        this.passwordHasher = passwordHasher;
    }

    public RegisterUserResult RegisterCustomer(string fullName, string email, string password)
    {
        var normalizedEmail = NormalizeEmail(email);

        var existingUser = dbContext.Users
            .FirstOrDefault(u => u.Email.ToLower() == normalizedEmail.ToLower());

        if (existingUser is not null)
        {
            return RegisterUserResult.DuplicateEmail();
        }

        var now = DateTimeOffset.UtcNow;
        var user = new User
        {
            Id = $"usr_{Guid.NewGuid():N}",
            FullName = fullName.Trim(),
            Email = normalizedEmail,
            PasswordHash = passwordHasher.HashPassword(password),
            Role = UserRole.Customer,
            CreatedAt = now,
            UpdatedAt = now
        };

        dbContext.Users.Add(user);
        dbContext.SaveChanges();

        return RegisterUserResult.Success(CloneUser(user));
    }

    public UserAccount? ValidateCredentials(string email, string password)
    {
        var normalizedEmail = NormalizeEmail(email);

        var user = dbContext.Users
            .FirstOrDefault(u => u.Email.ToLower() == normalizedEmail.ToLower());

        if (user is null || !passwordHasher.VerifyPassword(password, user.PasswordHash))
        {
            return null;
        }

        return ToUserAccount(user);
    }

    private static string NormalizeEmail(string email)
    {
        return email.Trim().ToLowerInvariant();
    }

    private static UserAccount CloneUser(User user)
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

    private static UserAccount ToUserAccount(User user)
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
