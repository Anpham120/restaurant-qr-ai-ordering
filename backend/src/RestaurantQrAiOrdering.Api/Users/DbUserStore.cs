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

    public UpdateUserResult UpdateUser(string userId, string fullName, string email, string role)
    {
        var user = dbContext.Users.FirstOrDefault(u => u.Id == userId);
        if (user is null)
        {
            return UpdateUserResult.UserNotFound();
        }

        var normalizedEmail = NormalizeEmail(email);
        var duplicateEmail = dbContext.Users.Any(u => u.Id != userId && u.Email.ToLower() == normalizedEmail.ToLower());
        if (duplicateEmail)
        {
            return UpdateUserResult.DuplicateEmail();
        }

        user.FullName = fullName.Trim();
        user.Email = normalizedEmail;
        user.Role = role;
        user.UpdatedAt = DateTimeOffset.UtcNow;
        dbContext.SaveChanges();

        return UpdateUserResult.Success(ToUserAccount(user));
    }

    public DeleteUserResult DeleteUser(string userId)
    {
        var user = dbContext.Users.FirstOrDefault(u => u.Id == userId);
        if (user is null)
        {
            return DeleteUserResult.UserNotFound();
        }

        var fallbackAdminId = dbContext.Users
            .AsNoTracking()
            .Where(u => u.Id != userId && u.Role == UserRole.Admin)
            .OrderBy(u => u.CreatedAt)
            .Select(u => u.Id)
            .FirstOrDefault();

        var hasCounterRefs = dbContext.CounterShifts.Any(s => s.OpenedByUserId == userId || s.ClosedByUserId == userId)
            || dbContext.CounterShiftTransactions.Any(t => t.CreatedByUserId == userId);

        if (hasCounterRefs && string.IsNullOrEmpty(fallbackAdminId))
        {
            return DeleteUserResult.HasDependencies();
        }

        if (!string.IsNullOrEmpty(fallbackAdminId))
        {
            foreach (var shift in dbContext.CounterShifts.Where(s => s.OpenedByUserId == userId))
            {
                shift.OpenedByUserId = fallbackAdminId;
            }

            foreach (var shift in dbContext.CounterShifts.Where(s => s.ClosedByUserId == userId))
            {
                shift.ClosedByUserId = null;
            }

            foreach (var transaction in dbContext.CounterShiftTransactions.Where(t => t.CreatedByUserId == userId))
            {
                transaction.CreatedByUserId = fallbackAdminId;
            }
        }

        dbContext.Users.Remove(user);
        try
        {
            dbContext.SaveChanges();
        }
        catch (DbUpdateException)
        {
            return DeleteUserResult.HasDependencies();
        }

        return DeleteUserResult.Success();
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

    public long? GetSecurityStampTicks(string userId)
    {
        var updatedAt = dbContext.Users
            .AsNoTracking()
            .Where(user => user.Id == userId)
            .Select(user => (DateTimeOffset?)user.UpdatedAt)
            .FirstOrDefault();
        return updatedAt?.UtcTicks;
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
            CreatedAt = user.CreatedAt,
            SecurityStampTicks = user.UpdatedAt.UtcTicks
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
            CreatedAt = user.CreatedAt,
            SecurityStampTicks = user.UpdatedAt.UtcTicks
        };
    }
}
