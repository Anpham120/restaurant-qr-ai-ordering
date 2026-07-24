import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import type { Order, OrderStatus } from "@cmc/shared-types";
import { Check, CircleCheck, ClipboardList, Clock3, Flame, Inbox, RefreshCw, Utensils } from "lucide-react";
import { getKitchenOrders, updateOrderStatus } from "../../services/orderService";
import { useOpsRealtime } from "../../hooks/useOpsRealtime";
import { matchesTableFilter, normalizeTableCode } from "../operations/opsDeepLinkUtils";
import { OpsConnectionBadge } from "../operations/OpsConnectionBadge";
import { labelOrderStatus, labelPaymentChip } from "../../utils/opsStatusLabels";
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
  highlighted = false,
}: {
  order: Order;
  onAction: (code: string, status: OrderStatus) => void;
  isPending: boolean;
  highlighted?: boolean;
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
    <article className={`ops-card ops-card--${order.status.toLowerCase()}${highlighted ? " ops-card--highlight" : ""}`}>
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
        <span className={`ops-badge ops-badge--${order.status.toLowerCase()}`}>{labelOrderStatus(order.status)}</span>
        <span className={payBadge}>{labelPaymentChip(order.paymentMethod, order.paymentStatus)}</span>
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
  tableFilter,
}: {
  title: string;
  icon: ReactNode;
  variant: string;
  orders: Order[];
  onAction: (code: string, status: OrderStatus) => void;
  pendingCode: string | null;
  tableFilter: string;
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
            <StaffCard
              key={o.orderId}
              order={o}
              onAction={onAction}
              isPending={pendingCode === o.orderCode}
              highlighted={Boolean(tableFilter && matchesTableFilter(o.tableCode, tableFilter))}
            />
          ))
        )}
      </div>
    </div>
  );
}

/* ---------- Main Board ---------- */
export function StaffOrderBoard({ embedded = false }: { embedded?: boolean }) {
  const [searchParams] = useSearchParams();
  const tableFilter = normalizeTableCode(searchParams.get("table"));
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingCode, setPendingCode] = useState<string | null>(null);

  const loadOrders = useCallback(async () => {
    try {
      const list = await getKitchenOrders();
      const nextOrders = Array.isArray(list) ? list : [];
      setOrders(nextOrders);
      setError("");
    } catch {
      setError("Không tải được đơn hàng.");
    }
  }, [tableFilter]);

  useEffect(() => {
    loadOrders().finally(() => setIsLoading(false));
  }, [loadOrders]);

  const { connectionStatus } = useOpsRealtime({ refresh: loadOrders, pollIntervalMs: 5_000 });

  const visibleOrders = useMemo(() => {
    if (!tableFilter) return orders;
    return orders.filter((order) => matchesTableFilter(order.tableCode, tableFilter));
  }, [orders, tableFilter]);

  const placed = useMemo(() => visibleOrders.filter((o) => o.status === "Placed"), [visibleOrders]);
  const preparing = useMemo(
    () => visibleOrders.filter((o) => o.status === "Confirmed" || o.status === "Preparing"),
    [visibleOrders],
  );
  const ready = useMemo(() => visibleOrders.filter((o) => o.status === "Ready"), [visibleOrders]);
  const served = useMemo(() => visibleOrders.filter((o) => o.status === "Served"), [visibleOrders]);

  const stats = useMemo(() => [
    { label: "Đơn mới", value: String(placed.length), detail: "Chờ xác nhận" },
    { label: "Đang bếp", value: String(preparing.length), detail: "Đã xác nhận, chờ món" },
    { label: "Sẵn sàng", value: String(ready.length), detail: "Chờ mang ra bàn" },
    { label: "Đã phục vụ", value: String(served.length), detail: "Chờ thu tiền / hoàn tất" },
  ], [placed, preparing, ready, served]);

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
      {!embedded ? (
        <div className="ops-page-header">
          <div className="ops-page-header-row">
            <div>
              <h1>Đơn cần phục vụ</h1>
              <p>Xác nhận, mang món, hoàn tất đơn tại bàn</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <OpsConnectionBadge status={connectionStatus} />
              <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={loadOrders} type="button"><RefreshCw aria-hidden="true" size={14} /> Làm mới</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="ops-toolbar">
          <OpsConnectionBadge status={connectionStatus} />
          <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={loadOrders} type="button"><RefreshCw aria-hidden="true" size={14} /> Làm mới</button>
        </div>
      )}

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      {tableFilter ? (
        <div className="ops-notice ops-notice--info">
          Đang lọc bàn <strong>{tableFilter}</strong>
        </div>
      ) : null}

      <div className="ops-stats">
        {stats.map((s) => (
          <div className="ops-stat-card" key={s.label}>
            <div className="ops-stat-label">{s.label}</div>
            <div className="ops-stat-value">{s.value}</div>
            <div className="ops-stat-detail">{s.detail}</div>
          </div>
        ))}
      </div>

      <div className="ops-board ops-board--staff">
        <StaffColumn title="Đơn mới" icon={<Inbox aria-hidden="true" size={16} />} variant="placed" orders={placed} onAction={handleAction} pendingCode={pendingCode} tableFilter={tableFilter} />
        <StaffColumn title="Đang bếp" icon={<Flame aria-hidden="true" size={16} />} variant="preparing" orders={preparing} onAction={handleAction} pendingCode={pendingCode} tableFilter={tableFilter} />
        <StaffColumn title="Sẵn sàng" icon={<Utensils aria-hidden="true" size={16} />} variant="ready" orders={ready} onAction={handleAction} pendingCode={pendingCode} tableFilter={tableFilter} />
        <StaffColumn title="Đã phục vụ" icon={<CircleCheck aria-hidden="true" size={16} />} variant="served" orders={served} onAction={handleAction} pendingCode={pendingCode} tableFilter={tableFilter} />
      </div>
    </div>
  );
}
