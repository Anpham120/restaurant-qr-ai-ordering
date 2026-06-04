using System.Text.RegularExpressions;
using RestaurantQrAiOrdering.Api.Categories;
using RestaurantQrAiOrdering.Api.Data;

namespace RestaurantQrAiOrdering.Api.Tables;

public static partial class TableEndpoints
{
    public static IEndpointRouteBuilder MapTableEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapGet("/api/tables/{tableCode}", (string tableCode, RestaurantDataStore store) =>
        {
            if (string.IsNullOrWhiteSpace(tableCode) || !TableCodeRegex().IsMatch(tableCode))
            {
                return ApiResults.BadRequest("TABLE_CODE_INVALID", "Table code must match format T01.");
            }

            var table = store.GetActiveTable(tableCode);

            return table is null
                ? ApiResults.NotFound("TABLE_NOT_FOUND", "Active table was not found.")
                : Results.Ok(new TableResponse(table.TableCode, table.DisplayName, table.IsActive));
        })
        .WithName("GetTable")
        .WithTags("Tables");

        return app;
    }

    [GeneratedRegex("^T\\d{2}$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex TableCodeRegex();
}
