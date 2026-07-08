#nullable enable

using System;
using System.Collections.Generic;

namespace RestaurantQrAiOrdering.Entities;

public class ChatSession
{
    public string Id { get; set; } = string.Empty;

    public string? RestaurantTableId { get; set; }

    public RestaurantTable? RestaurantTable { get; set; }

    public string? TableCode { get; set; }

    /// <summary>
    /// Phiên bàn (table session) mà hội thoại này thuộc về. Khi phiên bàn
    /// đóng/hết hạn, mọi chat session gắn với nó sẽ bị xóa để phục vụ khách mới.
    /// </summary>
    public string? TableSessionId { get; set; }

    public string? OrderId { get; set; }

    public Order? Order { get; set; }

    public bool IsClosed { get; set; }

    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;

    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;

    public ICollection<ChatMessage> Messages { get; set; } = new List<ChatMessage>();
}
