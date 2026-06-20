#nullable enable

namespace RestaurantQrAiOrdering.Enums;

public enum OrderStatus
{
    Draft,
    Placed,
    Confirmed,
    Preparing,
    Ready,
    Served,
    Completed,
    Cancelled
}
