#nullable enable

using System;
using System.Collections.Generic;

namespace RestaurantQrAiOrdering.Entities;

public class User
{
    public string Id { get; set; } = string.Empty;

    public string FullName { get; set; } = string.Empty;

    public string Email { get; set; } = string.Empty;

    public string PasswordHash { get; set; } = string.Empty;

    public string Role { get; set; } = string.Empty;

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    // Consecutive failed login attempts since the last success or lockout reset.
    public int FailedLoginCount { get; set; }

    // When set and in the future, the account is locked and logins are rejected
    // without checking the password. Cleared on a successful login.
    public DateTimeOffset? LockoutEndAt { get; set; }
}
