using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace RestaurantQrAiOrdering.Api.Orders;

public static partial class RequestIdempotency
{
    public const string HeaderName = "Idempotency-Key";

    private const int MaxKeyLength = 100;

    public static bool TryRead(HttpRequest request, out string key)
    {
        key = string.Empty;
        var values = request.Headers[HeaderName];
        if (values.Count != 1)
        {
            return false;
        }

        var candidate = values[0]?.Trim();
        if (string.IsNullOrEmpty(candidate)
            || candidate.Length > MaxKeyLength
            || !KeyRegex().IsMatch(candidate))
        {
            return false;
        }

        key = candidate;
        return true;
    }

    public static string ComputeFingerprint<T>(T value)
    {
        var json = JsonSerializer.Serialize(value, new JsonSerializerOptions(JsonSerializerDefaults.Web));
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json))).ToLowerInvariant();
    }

    [GeneratedRegex("^[A-Za-z0-9._:-]+$", RegexOptions.CultureInvariant)]
    private static partial Regex KeyRegex();
}
