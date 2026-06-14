namespace RestaurantQrAiOrdering.Api.Payments;

public sealed class VietQrOptions
{
    public const string SectionName = "Payments:VietQr";

    public string BankId { get; set; } = string.Empty;

    public string AccountNumber { get; set; } = string.Empty;

    public string AccountName { get; set; } = string.Empty;

    public string Template { get; set; } = "compact2";
}
