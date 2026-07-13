using System.Globalization;
using System.Text;

namespace RestaurantQrAiOrdering.Api.Chat;

/// <summary>
/// Selects the small, live-menu candidate set that an AI provider is allowed to
/// mention or make actionable. This is deterministic by design: an LLM must not
/// be responsible for enforcing a customer category or tag constraint.
/// </summary>
public sealed record ChatMenuItemContext(
    string Id,
    string Name,
    string Description,
    decimal Price,
    string CategoryId,
    string CategoryName,
    IReadOnlyList<string> Tags,
    bool IsAvailable);

public sealed record ChatMenuGroundingResult(
    IReadOnlyList<ChatMenuItemContext> Candidates,
    IReadOnlyList<string> MatchedCategoryNames,
    IReadOnlyList<string> MatchedTags)
{
    public bool HasExplicitConstraint => MatchedCategoryNames.Count > 0 || MatchedTags.Count > 0;
}

public static class ChatMenuGrounding
{
    private const int MaxCandidates = 8;

    public static IReadOnlyList<ChatMenuItemContext> Select(
        string message,
        IEnumerable<ChatMenuItemContext> menuItems) => SelectWithConstraints(message, menuItems).Candidates;

    public static ChatMenuGroundingResult SelectWithConstraints(
        string message,
        IEnumerable<ChatMenuItemContext> menuItems,
        int? maxCandidates = null)
    {
        var query = Normalize(message);
        var available = menuItems.Where(item => item.IsAvailable).ToList();
        if (available.Count == 0)
        {
            return new ChatMenuGroundingResult([], [], []);
        }

        var categoryMatches = available
            .Select(item => item.CategoryName)
            .Where(name => IsMeaningfulPhrase(name) && ContainsPhrase(query, Normalize(name)))
            .ToHashSet(StringComparer.Ordinal);

        var tagMatches = available
            .SelectMany(item => item.Tags)
            .Where(tag => IsMeaningfulPhrase(tag) && ContainsPhrase(query, Normalize(tag)))
            .ToHashSet(StringComparer.Ordinal);

        var constrained = categoryMatches.Count > 0
            ? available.Where(item => categoryMatches.Contains(item.CategoryName))
            : tagMatches.Count > 0
                ? available.Where(item => item.Tags.Any(tag => tagMatches.Contains(tag)))
                : available;

        var candidates = constrained
            .OrderByDescending(item => Relevance(query, item))
            .ThenBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
            .Take(maxCandidates ?? MaxCandidates)
            .ToList();

        return new ChatMenuGroundingResult(
            candidates,
            categoryMatches.OrderBy(name => name, StringComparer.OrdinalIgnoreCase).ToList(),
            tagMatches.OrderBy(tag => tag, StringComparer.OrdinalIgnoreCase).ToList());
    }

    private static int Relevance(string query, ChatMenuItemContext item)
    {
        var document = Normalize($"{item.Name} {item.Description} {item.CategoryName} {string.Join(' ', item.Tags)}");
        return query.Split(' ', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(token => token.Length > 1)
            .Sum(token => document.Contains(token, StringComparison.Ordinal) ? 1 : 0);
    }

    private static bool IsMeaningfulPhrase(string value) => Normalize(value).Length >= 3;

    private static bool ContainsPhrase(string query, string phrase) =>
        !string.IsNullOrWhiteSpace(phrase)
        && ($" {query} ").Contains($" {phrase} ", StringComparison.Ordinal);

    private static string Normalize(string? value)
    {
        var decomposed = (value ?? string.Empty).Normalize(NormalizationForm.FormD);
        var builder = new StringBuilder(decomposed.Length);
        foreach (var character in decomposed)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(character) == UnicodeCategory.NonSpacingMark)
            {
                continue;
            }

            builder.Append(char.IsLetterOrDigit(character) ? char.ToLowerInvariant(character) : ' ');
        }

        return string.Join(' ', builder.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries));
    }
}
