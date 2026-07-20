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
  qrToken?: string,
): string {
  let path: string;
  if (resumeState === "New") path = orderingPath(sessionId, "menu");
  else if (resumeState === "CartPending") path = orderingPath(sessionId, "cart");
  else if (resumeState === "OrderInProgress") path = orderingPath(sessionId, "orders");
  else path = `${orderingPath(sessionId, "orders")}?focus=invoice`;

  if (!qrToken) {
    return path;
  }

  const url = new URL(path, "http://local");
  url.searchParams.set("qr", qrToken);
  return `${url.pathname}${url.search}`;
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
