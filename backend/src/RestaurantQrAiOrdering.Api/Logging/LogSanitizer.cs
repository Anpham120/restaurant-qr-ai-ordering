namespace RestaurantQrAiOrdering.Api.Logging;

/// <summary>
/// Strips CR/LF from values before structured logging to prevent log forging (CWE-117).
/// </summary>
public static class LogSanitizer
{
    public static string ForLog(string? value)
    {
        if (string.IsNullOrEmpty(value))
        {
            return string.Empty;
        }

        return value.Replace('\r', '_').Replace('\n', '_');
    }
}
