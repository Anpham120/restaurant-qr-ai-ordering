#nullable enable

namespace RestaurantQrAiOrdering.Enums;

public enum OrderType
{
    DineIn,
    Pickup,
    DeliveryMock // TODO(issue-64): Rename to Delivery when Payment module is ready
}
