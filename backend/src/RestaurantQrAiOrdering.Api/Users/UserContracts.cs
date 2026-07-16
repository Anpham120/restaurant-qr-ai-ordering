namespace RestaurantQrAiOrdering.Api.Users;

public sealed record CreateUserRequest(string? FullName, string? Email, string? Password, string? Role);

public sealed record ResetPasswordRequest(string? NewPassword);

public sealed record UserSummaryResponse(string UserId, string FullName, string Email, string Role, DateTimeOffset CreatedAt);

public sealed record UserListResponse(IReadOnlyList<UserSummaryResponse> Users);
