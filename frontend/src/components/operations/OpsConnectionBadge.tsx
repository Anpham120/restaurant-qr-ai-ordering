import type { RealtimeConnectionStatus } from "@cmc/shared-types";

const LABELS: Record<RealtimeConnectionStatus, string> = {
  connected: "Đã kết nối",
  connecting: "Đang kết nối...",
  reconnecting: "Đang kết nối lại...",
  disconnected: "Mất kết nối",
  error: "Mất kết nối",
};

export function OpsConnectionBadge({ status }: { status: RealtimeConnectionStatus }) {
  return (
    <span className={`ops-connection ops-connection--${status}`}>
      <span className="ops-connection-dot" />
      {LABELS[status]}
    </span>
  );
}
