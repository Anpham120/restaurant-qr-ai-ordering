import type { AdminTable } from "@cmc/shared-types";

const LOCAL_ORDERING_PORT = "5177";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

export function getOrderingBaseUrl(locationLike?: Pick<Location, "origin" | "hostname" | "protocol" | "port">) {
  const configured = import.meta.env.VITE_ORDERING_BASE_URL;
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (typeof window === "undefined" && !locationLike) {
    return "https://order.cmcrestaurant.app";
  }

  const { origin, hostname, protocol, port } = locationLike ?? window.location;
  if (LOCAL_HOSTS.has(hostname)) {
    return `${protocol}//${hostname}:${LOCAL_ORDERING_PORT}`;
  }
  if (hostname.startsWith("admin.") || hostname.startsWith("ops.")) {
    return `${protocol}//${hostname.replace(/^(admin|ops)\./, "order.")}${port ? `:${port}` : ""}`;
  }

  return origin;
}

export function buildOrderingLink(
  table: Pick<AdminTable, "tableCode" | "customerPath">,
  locationLike?: Pick<Location, "origin" | "hostname" | "protocol" | "port">,
) {
  const baseUrl = getOrderingBaseUrl(locationLike);
  const customerPath = table.customerPath || `/table/${encodeURIComponent(table.tableCode)}`;
  return new URL(customerPath, baseUrl).toString();
}
