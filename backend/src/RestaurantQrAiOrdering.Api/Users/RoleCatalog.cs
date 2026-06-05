namespace RestaurantQrAiOrdering.Api.Users;

public interface IRoleCatalog
{
    IReadOnlyCollection<string> GetRoles();

    bool RoleExists(string role);
}

public sealed class RoleCatalog : IRoleCatalog
{
    private readonly HashSet<string> roles = new(UserRole.All, StringComparer.OrdinalIgnoreCase);

    public IReadOnlyCollection<string> GetRoles()
    {
        return roles.Order(StringComparer.OrdinalIgnoreCase).ToList();
    }

    public bool RoleExists(string role)
    {
        return roles.Contains(role);
    }
}
