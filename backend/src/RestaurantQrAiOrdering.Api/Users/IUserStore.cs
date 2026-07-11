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
