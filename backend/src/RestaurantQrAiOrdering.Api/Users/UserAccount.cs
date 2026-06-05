namespace RestaurantQrAiOrdering.Api.Users;

public sealed class UserAccount
{
    public required string Id { get; init; }

    public required string FullName { get; set; }

    public required string Email { get; init; }

    public required string PasswordHash { get; init; }

    public required string Role { get; init; }

    public required DateTimeOffset CreatedAt { get; init; }
}
