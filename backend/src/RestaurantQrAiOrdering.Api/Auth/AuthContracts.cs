namespace RestaurantQrAiOrdering.Api.Auth;

public sealed record RegisterRequest(string? FullName, string? Email, string? Password);

public sealed record LoginRequest(string? Email, string? Password);

public sealed record AuthUserResponse(string UserId, string FullName, string Email, string Role);

public sealed record RegisterResponse(string UserId, string FullName, string Email, string Role);

public sealed record LoginResponse(string AccessToken, DateTimeOffset ExpiresAt, AuthUserResponse User);
