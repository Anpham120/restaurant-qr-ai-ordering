namespace RestaurantQrAiOrdering.Api.Payments;

public sealed record PaymentResponse(
    string PaymentId,
    string OrderCode,
    string Method,
    string Status,
    decimal Amount,
    string? ProviderTransactionId,
    DateTimeOffset CreatedAt,
    DateTimeOffset? PaidAt,
    DateTimeOffset UpdatedAt,
    IReadOnlyList<PaymentTransactionResponse> Transactions);

public sealed record PaymentTransactionResponse(
    string TransactionId,
    string Method,
    string Status,
    decimal Amount,
    string Provider,
    string? ProviderTransactionId,
    string? Note,
    DateTimeOffset CreatedAt);

public sealed record VietQrResponse(
    string OrderCode,
    decimal Amount,
    string TransferContent,
    string BankId,
    string AccountNumber,
    string AccountName,
    string QuickLink,
    string QrPayload,
    string QrImageDataUri,
    string PaymentStatus);

public sealed record ConfirmPaymentRequest(string? ProviderTransactionId, string? Note);

public sealed record FailPaymentRequest(string? Note);

public sealed record RefundPaymentRequest(string? Note);
