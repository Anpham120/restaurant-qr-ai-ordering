import type { OrderStatus } from "@cmc/shared-types";

export type KitchenBoardColumn = "confirmed" | "preparing" | "ready" | "served";

export function getKitchenBoardColumn(status: OrderStatus): KitchenBoardColumn | null {
  if (status === "Placed" || status === "Confirmed") return "confirmed";
  if (status === "Preparing") return "preparing";
  if (status === "Ready") return "ready";
  if (status === "Served") return "served";
  return null;
}

export function isKitchenActiveOrderStatus(status: OrderStatus): boolean {
  return getKitchenBoardColumn(status) !== null;
}
