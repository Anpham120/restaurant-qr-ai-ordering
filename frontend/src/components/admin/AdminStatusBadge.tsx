import type { AdminOrder } from "../../types";

type AdminStatusBadgeProps = {
  status: AdminOrder["status"] | "Available" | "Unavailable" | "Paid" | "Pending";
};

export function AdminStatusBadge({ status }: AdminStatusBadgeProps) {
  return <span className={`admin-status admin-status-${status.toLowerCase()}`}>{status}</span>;
}
