using Microsoft.Extensions.Options;
using QRCoder;

namespace RestaurantQrAiOrdering.Api.Payments;

public interface IVietQrProvider
{
    VietQrPayload CreatePayload(string orderCode, decimal amount);
}

public sealed record VietQrPayload(
    decimal Amount,
    string TransferContent,
    string BankId,
    string AccountNumber,
    string AccountName,
    string QuickLink,
    string QrPayload,
    string QrImageDataUri);

public sealed class QrCoderVietQrProvider : IVietQrProvider
{
    private readonly VietQrOptions options;

    public QrCoderVietQrProvider(IOptions<VietQrOptions> options)
    {
        this.options = options.Value;
    }

    public VietQrPayload CreatePayload(string orderCode, decimal amount)
    {
        EnsureConfigured();

        var transferContent = $"CMC {orderCode}".ToUpperInvariant();
        var amountText = decimal.Truncate(amount).ToString("0", System.Globalization.CultureInfo.InvariantCulture);
        var quickLink =
            $"https://img.vietqr.io/image/{Uri.EscapeDataString(options.BankId)}-{Uri.EscapeDataString(options.AccountNumber)}-{Uri.EscapeDataString(options.Template)}.png" +
            $"?amount={Uri.EscapeDataString(amountText)}" +
            $"&addInfo={Uri.EscapeDataString(transferContent)}" +
            $"&accountName={Uri.EscapeDataString(options.AccountName)}";

        return new VietQrPayload(
            amount,
            transferContent,
            options.BankId,
            options.AccountNumber,
            options.AccountName,
            quickLink,
            quickLink,
            CreateQrDataUri(quickLink));
    }

    private void EnsureConfigured()
    {
        if (string.IsNullOrWhiteSpace(options.BankId) ||
            string.IsNullOrWhiteSpace(options.AccountNumber) ||
            string.IsNullOrWhiteSpace(options.AccountName))
        {
            throw new InvalidOperationException("VietQR bank configuration is missing.");
        }
    }

    private static string CreateQrDataUri(string payload)
    {
        using var generator = new QRCodeGenerator();
        using var data = generator.CreateQrCode(payload, QRCodeGenerator.ECCLevel.Q);
        var qr = new PngByteQRCode(data);
        var bytes = qr.GetGraphic(8);

        return $"data:image/png;base64,{Convert.ToBase64String(bytes)}";
    }
}
