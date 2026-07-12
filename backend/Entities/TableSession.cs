#nullable enable

using System;
using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Entities;

public class TableSession
{
    public string Id { get; set; } = string.Empty;

    public string? RestaurantTableId { get; set; }

    public RestaurantTable? RestaurantTable { get; set; }

    public string? TableCode { get; set; }

    public string? QrToken { get; set; }

    public OrderType OrderType { get; set; }

    public TableSessionStatus Status { get; set; } = TableSessionStatus.Open;

    public DateTimeOffset OpenedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset ExpiresAt { get; set; } = DateTimeOffset.UtcNow.AddHours(4);

    public DateTimeOffset? ClosedAt { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    public TableInvoice? Invoice { get; set; }

    public bool IsActiveAt(DateTimeOffset now) =>
        Status == TableSessionStatus.Open &&
        ClosedAt is null &&
        ExpiresAt > now;

    public bool ExpireIfPast(DateTimeOffset now)
    {
        if (Status != TableSessionStatus.Open || ClosedAt is not null || ExpiresAt > now)
        {
            return false;
        }

        Status = TableSessionStatus.Expired;
        ClosedAt = now;
        UpdatedAt = now;
        return true;
    }
}
