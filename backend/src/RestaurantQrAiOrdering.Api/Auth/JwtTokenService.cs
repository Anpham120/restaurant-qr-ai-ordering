using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;
using RestaurantQrAiOrdering.Api.Users;

namespace RestaurantQrAiOrdering.Api.Auth;

public interface IJwtTokenService
{
    LoginResponse CreateLoginResponse(UserAccount user);

    ClaimsPrincipal? ValidateAccessToken(string token);
}

public sealed class JwtTokenService : IJwtTokenService
{
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);
    private static readonly TimeSpan ClockSkew = TimeSpan.FromSeconds(30);

    private readonly JwtOptions options;

    public JwtTokenService(IOptions<JwtOptions> options)
    {
        this.options = options.Value;
    }

    public LoginResponse CreateLoginResponse(UserAccount user)
    {
        var now = DateTimeOffset.UtcNow;
        var expiresAt = now.AddMinutes(Math.Max(1, options.AccessTokenMinutes));
        var header = new Dictionary<string, object>
        {
            ["alg"] = "HS256",
            ["typ"] = "JWT"
        };

        var payload = new Dictionary<string, object>
        {
            ["iss"] = options.Issuer,
            ["aud"] = options.Audience,
            ["sub"] = user.Id,
            ["name"] = user.FullName,
            ["email"] = user.Email,
            ["role"] = user.Role,
            ["iat"] = now.ToUnixTimeSeconds(),
            ["nbf"] = now.ToUnixTimeSeconds(),
            ["exp"] = expiresAt.ToUnixTimeSeconds(),
            ["jti"] = Guid.NewGuid().ToString("N")
        };

        var encodedHeader = Base64Url.Encode(JsonSerializer.Serialize(header, SerializerOptions));
        var encodedPayload = Base64Url.Encode(JsonSerializer.Serialize(payload, SerializerOptions));
        var signature = Sign($"{encodedHeader}.{encodedPayload}");
        var accessToken = $"{encodedHeader}.{encodedPayload}.{signature}";

        return new LoginResponse(
            accessToken,
            expiresAt,
            new AuthUserResponse(user.Id, user.FullName, user.Email, user.Role));
    }

    public ClaimsPrincipal? ValidateAccessToken(string token)
    {
        var parts = token.Split('.');
        if (parts.Length != 3)
        {
            return null;
        }

        var signatureInput = $"{parts[0]}.{parts[1]}";
        var expectedSignature = Sign(signatureInput);
        if (!FixedTimeEquals(expectedSignature, parts[2]))
        {
            return null;
        }

        Dictionary<string, JsonElement>? payload;
        try
        {
            payload = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(
                Base64Url.Decode(parts[1]),
                SerializerOptions);
        }
        catch (JsonException)
        {
            return null;
        }
        catch (FormatException)
        {
            return null;
        }

        if (payload is null
            || !TryGetString(payload, "iss", out var issuer)
            || !TryGetString(payload, "aud", out var audience)
            || !TryGetString(payload, "sub", out var userId)
            || !TryGetString(payload, "name", out var fullName)
            || !TryGetString(payload, "email", out var email)
            || !TryGetString(payload, "role", out var role)
            || !TryGetLong(payload, "nbf", out var notBefore)
            || !TryGetLong(payload, "exp", out var expiresAt)
            || !issuer.Equals(options.Issuer, StringComparison.Ordinal)
            || !audience.Equals(options.Audience, StringComparison.Ordinal))
        {
            return null;
        }

        var now = DateTimeOffset.UtcNow;
        if (now < DateTimeOffset.FromUnixTimeSeconds(notBefore).Subtract(ClockSkew)
            || now > DateTimeOffset.FromUnixTimeSeconds(expiresAt).Add(ClockSkew))
        {
            return null;
        }

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, userId),
            new(ClaimTypes.Name, fullName),
            new(ClaimTypes.Email, email),
            new(ClaimTypes.Role, role),
            new("role", role)
        };

        return new ClaimsPrincipal(new ClaimsIdentity(claims, "Bearer"));
    }

    private string Sign(string value)
    {
        var key = Encoding.UTF8.GetBytes(options.SigningKey);
        using var hmac = new HMACSHA256(key);
        return Base64Url.Encode(hmac.ComputeHash(Encoding.UTF8.GetBytes(value)));
    }

    private static bool FixedTimeEquals(string expected, string actual)
    {
        try
        {
            var expectedBytes = Base64Url.Decode(expected);
            var actualBytes = Base64Url.Decode(actual);

            return expectedBytes.Length == actualBytes.Length
                && CryptographicOperations.FixedTimeEquals(expectedBytes, actualBytes);
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static bool TryGetString(
        IReadOnlyDictionary<string, JsonElement> payload,
        string key,
        out string value)
    {
        value = string.Empty;
        if (!payload.TryGetValue(key, out var element) || element.ValueKind != JsonValueKind.String)
        {
            return false;
        }

        value = element.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }

    private static bool TryGetLong(
        IReadOnlyDictionary<string, JsonElement> payload,
        string key,
        out long value)
    {
        value = 0;
        return payload.TryGetValue(key, out var element) && element.TryGetInt64(out value);
    }
}
