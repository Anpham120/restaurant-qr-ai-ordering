#nullable enable

namespace RestaurantQrAiOrdering.Enums;

public enum PaymentMethod
{
    COD,
    MockOnline // TODO(issue-64): Replace with VietQR, PayOS, etc. when Payment module is ready
}
