#nullable enable

namespace RestaurantQrAiOrdering.Enums;

public enum OrderType
{
    DineIn,

    // Retained so historical pickup orders remain readable after the
    // application moved to QR dine-in ordering only.
    Pickup
}
