import type { OrderStatus, PaymentStatus, TableSessionResumeState } from "@cmc/shared-types";
import { orderingPath } from "./orderingRoutes";

const IN_PROGRESS_ORDER_STATUSES = new Set<OrderStatus>([
  "Draft",
  "Placed",
  "Confirmed",
  "Preparing",
  "Ready",
]);

export function getSessionResumeDestination(
  sessionId: string,
  resumeState: TableSessionResumeState,
): string {
  if (resumeState === "New") return orderingPath(sessionId, "menu");
  if (resumeState === "CartPending") return orderingPath(sessionId, "cart");
  if (resumeState === "OrderInProgress") return orderingPath(sessionId, "orders");
  return `${orderingPath(sessionId, "orders")}?focus=invoice`;
}

export function deriveSessionHubState(
  orderStatuses: readonly OrderStatus[],
  invoiceStatus: PaymentStatus | null,
): Exclude<TableSessionResumeState, "CartPending"> {
  if (invoiceStatus === "Paid" || invoiceStatus === "Confirmed") return "Paid";
  if (invoiceStatus === "Pending") return "PaymentPending";

  const activeOrderStatuses = orderStatuses.filter(status => status !== "Cancelled");
  if (activeOrderStatuses.length === 0) return "New";
  if (activeOrderStatuses.some(status => IN_PROGRESS_ORDER_STATUSES.has(status))) {
    return "OrderInProgress";
  }
  return "ReadyForPayment";
}
