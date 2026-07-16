namespace RestaurantQrAiOrdering.Api.Tables;

public sealed record TableInvoiceLineResponse(
    string MenuItemId,
    string Name,
    decimal UnitPrice,
    int Quantity,
    decimal LineTotal);

public sealed record TableInvoiceOrderRoundResponse(
    string OrderCode,
    string Status,
    decimal SubtotalAmount,
    DateTimeOffset CreatedAt);

public sealed record TableInvoiceResponse(
    string TableSessionId,
    string? InvoiceCode,
    string? TableCode,
    string Status,
    decimal SubtotalAmount,
    decimal DiscountAmount,
    decimal TotalAmount,
    string? PromotionCode,
    string? CustomerPhoneNumber,
    string Method,
    IReadOnlyList<TableInvoiceOrderRoundResponse> OrderRounds,
    IReadOnlyList<TableInvoiceLineResponse> Items,
    TableInvoiceVietQrResponse? VietQr);

public sealed record TableInvoicePaymentRequest(
    string? Method,
    string? PromotionCode,
    string? CustomerPhoneNumber);

public sealed record TableInvoiceSettlementActionRequest(string? Note);

public sealed record TableInvoicePaymentStateResponse(
    string PaymentId,
    string Status,
    string Method,
    decimal Amount);

public sealed record TableInvoiceVietQrResponse(
    string InvoiceCode,
    decimal Amount,
    string TransferContent,
    string QuickLink,
    string QrImageDataUri);

public sealed record TableInvoicePaymentRequestResponse(
    TableInvoiceResponse Invoice,
    TableInvoicePaymentStateResponse Payment,
    TableInvoiceVietQrResponse? VietQr);
