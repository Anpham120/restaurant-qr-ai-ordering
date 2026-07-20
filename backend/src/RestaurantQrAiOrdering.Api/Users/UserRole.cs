namespace RestaurantQrAiOrdering.Api.Users;

public static class UserRole
{
    public const string Customer = "Customer";
    public const string Staff = "Staff";
    public const string CounterStaff = "CounterStaff";
    public const string Kitchen = "Kitchen";
    public const string Admin = "Admin";

    public static readonly string[] All =
    [
        Customer,
        Staff,
        CounterStaff,
        Kitchen,
        Admin
    ];
}
