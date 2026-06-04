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
    Delivering,
    Delivered,
    Completed,
    Cancelled
}
