import type {
  Order,
  OrderCreatedEvent,
  OrderItemStatusChangedEvent,
  OrderStatusChangedEvent,
} from "@cmc/shared-types";

export function mergeOrderCreated(orders: Order[], event: OrderCreatedEvent, placeholder?: Order): Order[] {
  const existing = orders.find((order) => order.orderCode === event.orderCode);
  if (existing) {
    return orders;
  }
  if (placeholder) {
    return [placeholder, ...orders];
  }
  return orders;
}

export function mergeOrderStatusChanged(orders: Order[], event: OrderStatusChangedEvent): Order[] {
  return orders.map((order) =>
    order.orderCode === event.orderCode
      ? { ...order, status: event.status, updatedAt: event.updatedAt }
      : order,
  );
}

export function mergeOrderItemStatusChanged(orders: Order[], event: OrderItemStatusChangedEvent): Order[] {
  return orders.map((order) => {
    if (order.orderCode !== event.orderCode) {
      return order;
    }
    return {
      ...order,
      updatedAt: event.updatedAt,
      items: order.items.map((item) =>
        item.orderItemId === event.orderItemId
          ? { ...item, status: event.status, updatedAt: event.updatedAt }
          : item,
      ),
    };
  });
}

export function upsertOrder(orders: Order[], next: Order): Order[] {
  const index = orders.findIndex((order) => order.orderCode === next.orderCode);
  if (index === -1) {
    return [next, ...orders];
  }
  const copy = [...orders];
  copy[index] = next;
  return copy;
}
