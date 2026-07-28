import type { UserRole } from "@cmc/shared-types";
import { buildCounterPaymentsLink, buildOrdersKanbanLink, buildTableOrdersLink } from "./opsDeepLinkUtils";

/** Kitchen staff must not get SPA links to counter/admin-only routes from realtime toasts. */
export function resolveOpsToastHref(role: UserRole | undefined, href: string | undefined): string | undefined {
  if (!href) return undefined;
  if (role !== "Kitchen") return href;
  if (href.startsWith("/counter") || href.startsWith("/orders") || href.startsWith("/tables/")) {
    return undefined;
  }
  return href;
}

export function buildOrderCreatedToastHref(
  role: UserRole | undefined,
  tableCode: string | null | undefined,
): string | undefined {
  if (role === "Kitchen") return undefined;
  return tableCode ? buildTableOrdersLink(tableCode) : buildOrdersKanbanLink();
}

export function buildPaymentRequestedToastHref(
  role: UserRole | undefined,
  tableCode: string | null | undefined,
): string | undefined {
  if (role === "Kitchen") return undefined;
  return buildCounterPaymentsLink(tableCode);
}

export function buildAssistanceToastHref(role: UserRole | undefined): string | undefined {
  if (role === "Kitchen") return undefined;
  return "/counter?tab=assistance";
}
