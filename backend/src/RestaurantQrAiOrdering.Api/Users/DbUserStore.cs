using Microsoft.EntityFrameworkCore;
using RestaurantQrAiOrdering.Api.Data;
using RestaurantQrAiOrdering.Entities;

namespace RestaurantQrAiOrdering.Api.Users;

public sealed class DbUserStore : IUserStore
{
    // After this many consecutive failed logins the account is locked.
    private const int MaxFailedLoginAttempts = 5;

    // How long the account stays locked once the threshold is reached.
    private static readonly TimeSpan LockoutDuration = TimeSpan.FromMinutes(15);

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

        if (user is null)
        {
            return null;
        }

        var now = DateTimeOffset.UtcNow;

        // Locked and still within the lockout window: reject without checking the
        // password so the caller cannot probe credentials while locked.
        if (user.LockoutEndAt is not null && user.LockoutEndAt > now)
        {
            return null;
        }

        if (passwordHasher.VerifyPassword(password, user.PasswordHash))
        {
            // Successful login clears any accumulated failure state.
            if (user.FailedLoginCount != 0 || user.LockoutEndAt is not null)
            {
                user.FailedLoginCount = 0;
                user.LockoutEndAt = null;
                user.UpdatedAt = now;
                dbContext.SaveChanges();
            }

            return ToUserAccount(user);
        }

        // Failed attempt. If a previous lockout has expired, start a fresh window.
        if (user.LockoutEndAt is not null)
        {
            user.FailedLoginCount = 0;
            user.LockoutEndAt = null;
        }

        user.FailedLoginCount++;
        if (user.FailedLoginCount >= MaxFailedLoginAttempts)
        {
            user.LockoutEndAt = now.Add(LockoutDuration);
        }

        user.UpdatedAt = now;
        dbContext.SaveChanges();

        return null;
    }

    public IReadOnlyList<UserAccount> ListUsers()
    {
        return dbContext.Users
            .OrderBy(u => u.CreatedAt)
            .ThenBy(u => u.FullName)
            .AsEnumerable()
            .Select(ToUserAccount)
            .ToList();
    }

    public CreateUserResult CreateUser(string fullName, string email, string password, string role)
    {
        var normalizedEmail = NormalizeEmail(email);

        var existingUser = dbContext.Users
            .FirstOrDefault(u => u.Email.ToLower() == normalizedEmail.ToLower());

        if (existingUser is not null)
        {
            return CreateUserResult.DuplicateEmail();
        }

        var now = DateTimeOffset.UtcNow;
        var user = new User
        {
            Id = $"usr_{Guid.NewGuid():N}",
            FullName = fullName.Trim(),
            Email = normalizedEmail,
            PasswordHash = passwordHasher.HashPassword(password),
            Role = role,
            CreatedAt = now,
            UpdatedAt = now
        };

        dbContext.Users.Add(user);
        dbContext.SaveChanges();

        return CreateUserResult.Success(ToUserAccount(user));
    }

    public ChangePasswordResult ChangePassword(string userId, string currentPassword, string newPassword)
    {
        var user = dbContext.Users.FirstOrDefault(u => u.Id == userId);
        if (user is null)
        {
            return ChangePasswordResult.UserNotFound();
        }

        if (!passwordHasher.VerifyPassword(currentPassword, user.PasswordHash))
        {
            return ChangePasswordResult.InvalidCurrentPassword();
        }

        user.PasswordHash = passwordHasher.HashPassword(newPassword);
        user.UpdatedAt = DateTimeOffset.UtcNow;
        dbContext.SaveChanges();

        return ChangePasswordResult.Success();
    }

    public ResetPasswordResult ResetPassword(string userId, string newPassword)
    {
        var user = dbContext.Users.FirstOrDefault(u => u.Id == userId);
        if (user is null)
        {
            return ResetPasswordResult.UserNotFound();
        }

        user.PasswordHash = passwordHasher.HashPassword(newPassword);
        user.UpdatedAt = DateTimeOffset.UtcNow;
        dbContext.SaveChanges();

        return ResetPasswordResult.Success();
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
