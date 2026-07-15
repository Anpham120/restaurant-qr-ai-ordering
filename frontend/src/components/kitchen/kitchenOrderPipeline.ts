import type { OrderItemStatus, OrderStatus } from "@cmc/shared-types";

export type KitchenBoardColumn = "confirmed" | "preparing" | "ready" | "served";

const kitchenBoardColumns: readonly KitchenBoardColumn[] = [
  "confirmed",
  "preparing",
  "ready",
  "served",
];

export type KitchenBoardAdvancePlan =
  | {
      kind: "items";
      eligibleItemStatuses: readonly OrderItemStatus[];
      nextItemStatus: OrderItemStatus;
    }
  | {
      kind: "order";
      nextOrderStatus: OrderStatus;
    };

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

export function getKitchenBoardAdvancePlan(status: OrderStatus): KitchenBoardAdvancePlan | null {
  const column = getKitchenBoardColumn(status);
  if (column === "confirmed") {
    return {
      kind: "items",
      eligibleItemStatuses: ["Pending"],
      nextItemStatus: "Preparing",
    };
  }
  if (column === "preparing") {
    return {
      kind: "items",
      eligibleItemStatuses: ["Pending", "Preparing"],
      nextItemStatus: "Ready",
    };
  }
  if (column === "ready") {
    return { kind: "order", nextOrderStatus: "Served" };
  }
  return null;
}

export function getNextKitchenBoardColumn(status: OrderStatus): KitchenBoardColumn | null {
  const currentColumn = getKitchenBoardColumn(status);
  if (!currentColumn) return null;

  const currentIndex = kitchenBoardColumns.indexOf(currentColumn);
  return kitchenBoardColumns[currentIndex + 1] ?? null;
}

export function canDropKitchenOrder(
  status: OrderStatus,
  targetColumn: KitchenBoardColumn,
): boolean {
  return getNextKitchenBoardColumn(status) === targetColumn;
}
