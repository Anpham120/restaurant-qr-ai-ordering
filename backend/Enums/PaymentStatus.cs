#nullable enable

namespace RestaurantQrAiOrdering.Enums;

public enum PaymentStatus
{
    NotRequested,
    Unpaid,
    Pending,
    Paid,
    Confirmed,
    Failed,
    Cancelled,
    Refunded
}
