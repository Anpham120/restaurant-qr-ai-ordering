using RestaurantQrAiOrdering.Api.Logging;
using Xunit;

namespace RestaurantQrAiOrdering.Api.Tests;

public sealed class LogSanitizerTests
{
    [Fact]
    public void ForLog_ReplacesCrLfWithUnderscores()
    {
        Assert.Equal("line_one_line_two", LogSanitizer.ForLog("line\rone\nline\rtwo"));
    }

    [Fact]
    public void ForLog_ReturnsEmptyForNullOrEmpty()
    {
        Assert.Equal(string.Empty, LogSanitizer.ForLog(null));
        Assert.Equal(string.Empty, LogSanitizer.ForLog(string.Empty));
    }
}
