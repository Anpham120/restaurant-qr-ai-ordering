using System.Security.Cryptography;
using System.Text;

namespace RestaurantQrAiOrdering.Api.Auth;

public static class CapabilityTokenSigner
{
    public static string CreateToken(string signingKey, string purpose, string payload) =>
        Base64Url.Encode(CreateSignature(signingKey, purpose, payload));

    public static bool IsValid(
        string suppliedToken,
        string signingKey,
        params (string Purpose, string Payload)[] acceptedMaterials)
    {
        byte[] suppliedSignature;
        try
        {
            suppliedSignature = Base64Url.Decode(suppliedToken);
        }
        catch (FormatException)
        {
            return false;
        }

        var matched = false;
        foreach (var material in acceptedMaterials)
        {
            var expected = CreateSignature(signingKey, material.Purpose, material.Payload);
            matched |= CryptographicOperations.FixedTimeEquals(expected, suppliedSignature);
        }

        return matched;
    }

    private static byte[] CreateSignature(string signingKey, string purpose, string payload)
    {
        if (string.IsNullOrWhiteSpace(signingKey))
        {
            throw new InvalidOperationException("A signing key is required for session capabilities.");
        }

        var purposeKey = HMACSHA256.HashData(
            Encoding.UTF8.GetBytes(signingKey),
            Encoding.UTF8.GetBytes(purpose));
        return HMACSHA256.HashData(purposeKey, Encoding.UTF8.GetBytes(payload));
    }
}
