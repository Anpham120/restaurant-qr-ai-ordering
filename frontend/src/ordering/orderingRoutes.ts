export type OrderingDestination = "ai" | "menu" | "cart" | "checkout" | "orders";

export function orderingPath(sessionId: string, destination: OrderingDestination | string = "menu"): string {
  return `/table-session/${encodeURIComponent(sessionId)}/${destination}`;
}

export function orderTrackingPath(sessionId: string, orderCode: string): string {
  return `${orderingPath(sessionId, "orders")}/${encodeURIComponent(orderCode)}`;
}
