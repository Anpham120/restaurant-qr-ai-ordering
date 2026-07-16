import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Order, OrderStatus, RealtimeConnectionStatus } from "@cmc/shared-types";
import { Check, CircleCheck, ClipboardList, Clock3, Inbox, RefreshCw, Utensils } from "lucide-react";
import { getKitchenOrders, updateOrderStatus } from "../../services/orderService";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
} from "../../services/realtimeOrderService";
import "../operations/operations.css";

/* ---------- helpers ---------- */
function timeAgo(iso: string): string {
  const diff = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  return `${Math.floor(diff / 3600)}h${Math.floor((diff % 3600) / 60)}m`;
}

function formatVnd(v: number) {
  return v.toLocaleString("vi-VN") + "đ";
}

/* ---------- Order Card ---------- */
function StaffCard({
  order,
  onAction,
  isPending,
}: {
  order: Order;
  onAction: (code: string, status: OrderStatus) => void;
  isPending: boolean;
}) {
  const [elapsed, setElapsed] = useState(timeAgo(order.createdAt));

  useEffect(() => {
    const t = setInterval(() => setElapsed(timeAgo(order.createdAt)), 10_000);
    return () => clearInterval(t);
  }, [order.createdAt]);

  const payBadge =
    order.paymentStatus === "Confirmed" || order.paymentStatus === "Paid"
      ? "ops-badge ops-badge--paid"
      : order.paymentStatus === "Failed"
        ? "ops-badge ops-badge--failed"
        : "ops-badge ops-badge--unpaid";

  return (
    <article className={`ops-card ops-card--${order.status.toLowerCase()}`}>
      <div className="ops-card-header">
        <span className="ops-card-code">{order.orderCode}</span>
        {order.tableCode ? <span className="ops-card-table">Bàn {order.tableCode}</span> : null}
      </div>
      <div className="ops-card-meta">
        <span className="ops-timer ops-timer--normal"><Clock3 aria-hidden="true" size={14} /> {elapsed}</span>
        <span>{order.items.length} món</span>
        <span>{formatVnd(order.totalAmount)}</span>
      </div>
      <div className="ops-card-meta" style={{ marginTop: 6 }}>
        <span className={`ops-badge ops-badge--${order.status.toLowerCase()}`}>{order.status}</span>
        <span className={payBadge}>{order.paymentMethod} · {order.paymentStatus}</span>
      </div>

      <div className="ops-card-items">
        {order.items.map((item) => (
          <span
            key={item.orderItemId}
            className={
              item.status === "Ready" || item.status === "Served"
                ? "ops-card-item-chip ops-card-item-chip--done"
                : item.status === "Preparing"
                  ? "ops-card-item-chip ops-card-item-chip--active"
                  : "ops-card-item-chip"
            }
          >
            {item.quantity}× {item.name}
          </span>
        ))}
      </div>

      <div className="ops-card-actions">
        {order.status === "Placed" ? (
          <button className="ops-btn ops-btn--primary ops-btn--sm" disabled={isPending} onClick={() => onAction(order.orderCode, "Confirmed")} type="button">
            <Check aria-hidden="true" size={14} /> Xác nhận đơn
          </button>
        ) : null}
        {order.status === "Ready" ? (
          <button className="ops-btn ops-btn--success ops-btn--sm" disabled={isPending} onClick={() => onAction(order.orderCode, "Served")} type="button">
            <Utensils aria-hidden="true" size={14} /> Đã phục vụ
          </button>
        ) : null}
        {order.status === "Served" ? (
          <button
            className="ops-btn ops-btn--success ops-btn--sm"
            disabled={isPending || !(order.paymentStatus === "Confirmed" || order.paymentStatus === "Paid")}
            onClick={() => onAction(order.orderCode, "Completed")}
            type="button"
            title={order.paymentStatus !== "Confirmed" && order.paymentStatus !== "Paid" ? "Cần thu tiền trước" : ""}
          >
            <CircleCheck aria-hidden="true" size={14} /> Hoàn tất
          </button>
        ) : null}
        {(order.status === "Placed" || order.status === "Confirmed") ? (
          <button className="ops-btn ops-btn--ghost ops-btn--sm" disabled={isPending} onClick={() => onAction(order.orderCode, "Cancelled")} type="button">
            Hủy
          </button>
        ) : null}
      </div>
    </article>
  );
}

/* ---------- Column ---------- */
function StaffColumn({
  title,
  icon,
  variant,
  orders,
  onAction,
  pendingCode,
}: {
  title: string;
  icon: ReactNode;
  variant: string;
  orders: Order[];
  onAction: (code: string, status: OrderStatus) => void;
  pendingCode: string | null;
}) {
  return (
    <div className={`ops-column ops-column--${variant}`}>
      <div className="ops-column-header">
        <h3>{icon} {title}</h3>
        <span className="ops-count">{orders.length}</span>
      </div>
      <div className="ops-column-body">
        {orders.length === 0 ? (
          <div className="ops-column-empty">Không có đơn</div>
        ) : (
          orders.map((o) => (
            <StaffCard key={o.orderId} order={o} onAction={onAction} isPending={pendingCode === o.orderCode} />
          ))
        )}
      </div>
    </div>
  );
}

/* ---------- Main Board ---------- */
export function StaffOrderBoard() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<RealtimeConnectionStatus>("disconnected");

  const loadOrders = useCallback(async () => {
    try {
      const data = await getKitchenOrders();
      const list = (data as { orders?: Order[] }).orders ?? (data as unknown as Order[]);
      setOrders(Array.isArray(list) ? list : []);
    } catch {
      setError("Không tải được đơn hàng.");
    }
  }, []);

  useEffect(() => {
    loadOrders().finally(() => setIsLoading(false));
  }, [loadOrders]);

  // Realtime
  useEffect(() => {
    const unC = subscribeRealtimeConnection(setConnectionStatus);
    const unR = subscribeOrderRealtime(() => loadOrders());
    void connectOrderRealtime().catch(() => setConnectionStatus("error"));
    return () => { unC(); unR(); void disconnectOrderRealtime(); };
  }, [loadOrders]);

  useEffect(() => {
    if (connectionStatus === "connected") return;
    const interval = window.setInterval(() => void loadOrders(), 5_000);
    return () => window.clearInterval(interval);
  }, [connectionStatus, loadOrders]);

  const placed = useMemo(() => orders.filter((o) => o.status === "Placed"), [orders]);
  const ready = useMemo(() => orders.filter((o) => o.status === "Ready"), [orders]);
  const served = useMemo(() => orders.filter((o) => o.status === "Served"), [orders]);
  const active = useMemo(
    () => orders.filter((o) => ["Confirmed", "Preparing"].includes(o.status)),
    [orders],
  );

  const stats = useMemo(() => [
    { label: "Đơn mới", value: String(placed.length), detail: "Chờ xác nhận" },
    { label: "Đang bếp", value: String(active.length), detail: "Confirmed + Preparing" },
    { label: "Sẵn sàng", value: String(ready.length), detail: "Chờ mang ra bàn" },
    { label: "Đã phục vụ", value: String(served.length), detail: "Chờ thu tiền / hoàn tất" },
  ], [placed, active, ready, served]);

  const handleAction = useCallback(async (orderCode: string, status: OrderStatus) => {
    setPendingCode(orderCode);
    setNotice("");
    try {
      await updateOrderStatus(orderCode, status);
      setNotice(`${orderCode} -> ${status}`);
      await loadOrders();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Thao tác thất bại.");
    } finally {
      setPendingCode(null);
    }
  }, [loadOrders]);

  if (isLoading) {
    return <div className="ops-empty"><div className="ops-empty-icon"><ClipboardList aria-hidden="true" /></div>Đang tải...</div>;
  }

  return (
    <div>
      <div className="ops-page-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1>Đơn cần phục vụ</h1>
            <p>Xác nhận, mang món, hoàn tất đơn tại bàn</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className={`ops-connection ops-connection--${connectionStatus}`}>
              <span className="ops-connection-dot" />
              {connectionStatus === "connected" ? "Đã kết nối" : connectionStatus === "connecting" ? "Đang kết nối..." : "Mất kết nối"}
            </span>
            <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={loadOrders} type="button"><RefreshCw aria-hidden="true" size={14} /> Làm mới</button>
          </div>
        </div>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-stats">
        {stats.map((s) => (
          <div className="ops-stat-card" key={s.label}>
            <div className="ops-stat-label">{s.label}</div>
            <div className="ops-stat-value">{s.value}</div>
            <div className="ops-stat-detail">{s.detail}</div>
          </div>
        ))}
      </div>

      <div className="ops-board">
        <StaffColumn title="Đơn mới" icon={<Inbox aria-hidden="true" size={16} />} variant="placed" orders={placed} onAction={handleAction} pendingCode={pendingCode} />
        <StaffColumn title="Sẵn sàng" icon={<Utensils aria-hidden="true" size={16} />} variant="ready" orders={ready} onAction={handleAction} pendingCode={pendingCode} />
        <StaffColumn title="Đã phục vụ" icon={<CircleCheck aria-hidden="true" size={16} />} variant="served" orders={served} onAction={handleAction} pendingCode={pendingCode} />
      </div>
    </div>
  );
}
