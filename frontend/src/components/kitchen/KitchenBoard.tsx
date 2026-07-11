import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Order, OrderItemStatus } from "@cmc/shared-types";
import { Circle, Clock3, Flame, X } from "lucide-react";
import { updateOrderItemStatus } from "../../services/orderService";
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

function statusBadgeClass(status: string): string {
  return `ops-badge ops-badge--${status.toLowerCase()}`;
}

function itemNextStatus(current: OrderItemStatus): OrderItemStatus | null {
  if (current === "Pending") return "Preparing";
  if (current === "Preparing") return "Ready";
  return null;
}

function itemActionLabel(current: OrderItemStatus): string {
  if (current === "Pending") return "Bắt đầu nấu";
  if (current === "Preparing") return "Xong món";
  return "";
}

/* ---------- types ---------- */
type KitchenColumn = "confirmed" | "preparing" | "ready";

interface KitchenBoardProps {
  orders: Order[];
  onRefresh: () => void | Promise<void>;
}

function StartCookingButton({
  order,
  isPending,
  onMoveNext,
  compact = false,
}: {
  order: Order;
  isPending: boolean;
  onMoveNext: (order: Order) => void;
  compact?: boolean;
}) {
  return (
    <button
      className={`ops-btn ops-btn--warning${compact ? " ops-btn--sm" : ""}`}
      disabled={isPending}
      onClick={() => onMoveNext(order)}
      type="button"
    >
      <Flame aria-hidden="true" size={compact ? 14 : 16} />
      {compact ? "Bắt đầu nấu" : "Bắt đầu nấu đơn"}
    </button>
  );
}

/* ---------- Order Card ---------- */
function OrderCard({
  order,
  column,
  onOpenDetail,
  onMoveNext,
  isPending,
}: {
  order: Order;
  column: KitchenColumn;
  onOpenDetail: (order: Order) => void;
  onMoveNext: (order: Order) => void;
  isPending: boolean;
}) {
  const [elapsed, setElapsed] = useState(timeAgo(order.createdAt));

  useEffect(() => {
    const timer = setInterval(() => setElapsed(timeAgo(order.createdAt)), 10_000);
    return () => clearInterval(timer);
  }, [order.createdAt]);

  const isUrgent = Date.now() - new Date(order.createdAt).getTime() > 15 * 60_000;
  const readyCount = order.items.filter((i) => i.status === "Ready").length;
  const totalCount = order.items.filter((i) => i.status !== "Cancelled").length;

  return (
    <article
      className={`ops-card ops-card--${order.status.toLowerCase()}`}
      onClick={() => onOpenDetail(order)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onOpenDetail(order)}
    >
      <div className="ops-card-header">
        <span className="ops-card-code">{order.orderCode}</span>
        {order.tableCode ? (
          <span className="ops-card-table">Bàn {order.tableCode}</span>
        ) : null}
      </div>

      <div className="ops-card-meta">
        <span className={isUrgent ? "ops-timer ops-timer--urgent" : "ops-timer ops-timer--normal"}>
          <Clock3 aria-hidden="true" size={14} /> {elapsed}
        </span>
        <span>{readyCount}/{totalCount} món xong</span>
        <span>{formatVnd(order.totalAmount)}</span>
      </div>

      <div className="ops-card-items">
        {order.items.map((item) => (
          <span
            key={item.orderItemId}
            className={
              item.status === "Ready" || item.status === "Cancelled"
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

      {column === "confirmed" ? (
        <div className="ops-card-actions" onClick={(e) => e.stopPropagation()}>
          <StartCookingButton compact isPending={isPending} onMoveNext={onMoveNext} order={order} />
        </div>
      ) : null}
    </article>
  );
}

/* ---------- Order Detail Modal ---------- */
function OrderDetailModal({
  order,
  onClose,
  onItemAction,
  onMoveNext,
  isPending,
}: {
  order: Order;
  onClose: () => void;
  onItemAction: (order: Order, itemId: string, nextStatus: OrderItemStatus) => void;
  onMoveNext: (order: Order) => void;
  isPending: boolean;
}) {
  const column: KitchenColumn =
    order.status === "Confirmed" ? "confirmed" : order.status === "Preparing" ? "preparing" : "ready";

  return (
    <div className="ops-modal-overlay" onClick={onClose}>
      <div
        aria-labelledby="kitchen-order-title"
        aria-modal="true"
        className="ops-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <div className="ops-modal-header">
          <div>
            <h2 id="kitchen-order-title">{order.orderCode}</h2>
            <div className="ops-card-meta" style={{ marginTop: 4 }}>
              <span className={statusBadgeClass(order.status)}>{order.status}</span>
              {order.tableCode ? <span>Bàn {order.tableCode}</span> : null}
              <span>{formatVnd(order.totalAmount)}</span>
            </div>
          </div>
          <button aria-label="Đóng" className="ops-modal-close" onClick={onClose} type="button"><X aria-hidden="true" size={18} /></button>
        </div>

        <div className="ops-modal-body">
          <div className="ops-item-list">
            {order.items.map((item) => {
              const next = itemNextStatus(item.status);
              return (
                <div className="ops-item-row" key={item.orderItemId}>
                  <div className="ops-item-info">
                    <div className="ops-item-name">
                      <span>{item.quantity}× {item.name}</span>
                      <span className={statusBadgeClass(item.status)}>{item.status}</span>
                    </div>
                    <span className="ops-item-qty">{formatVnd(item.lineTotal)}</span>
                  </div>
                  <div className="ops-item-actions">
                    {next ? (
                      <button
                        className="ops-btn ops-btn--sm ops-btn--primary"
                        disabled={isPending}
                        onClick={() => onItemAction(order, item.orderItemId, next)}
                        type="button"
                      >
                        {itemActionLabel(item.status)}
                      </button>
                    ) : null}
                    {item.status !== "Cancelled" && item.status !== "Ready" ? (
                      <button
                        className="ops-btn ops-btn--sm ops-btn--ghost"
                        disabled={isPending}
                        onClick={() => onItemAction(order, item.orderItemId, "Cancelled")}
                        type="button"
                      >
                        Hủy
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {column === "confirmed" ? (
          <div className="ops-modal-footer">
            <StartCookingButton isPending={isPending} onMoveNext={onMoveNext} order={order} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

/* ---------- Column ---------- */
function KitchenColumn({
  title,
  icon,
  column,
  orders,
  onOpenDetail,
  onMoveNext,
  pendingCode,
}: {
  title: string;
  icon: ReactNode;
  column: KitchenColumn;
  orders: Order[];
  onOpenDetail: (o: Order) => void;
  onMoveNext: (o: Order) => void;
  pendingCode: string | null;
}) {
  return (
    <div className={`ops-column ops-column--${column}`}>
      <div className="ops-column-header">
        <h3>{icon} {title}</h3>
        <span className="ops-count">{orders.length}</span>
      </div>
      <div className="ops-column-body">
        {orders.length === 0 ? (
          <div className="ops-column-empty">Không có đơn</div>
        ) : (
          orders.map((order) => (
            <OrderCard
              key={order.orderId}
              order={order}
              column={column}
              onOpenDetail={onOpenDetail}
              onMoveNext={onMoveNext}
              isPending={pendingCode === order.orderCode}
            />
          ))
        )}
      </div>
    </div>
  );
}

/* ---------- Main Board ---------- */
export function KitchenBoard({ orders, onRefresh }: KitchenBoardProps) {
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  const confirmed = useMemo(
    () => orders.filter((o) => o.status === "Confirmed"),
    [orders],
  );
  const preparing = useMemo(
    () => orders.filter((o) => o.status === "Preparing"),
    [orders],
  );
  const ready = useMemo(
    () => orders.filter((o) => o.status === "Ready"),
    [orders],
  );

  // Sync selected order with fresh data
  useEffect(() => {
    if (selectedOrder) {
      const fresh = orders.find((o) => o.orderCode === selectedOrder.orderCode);
      if (fresh) {
        setSelectedOrder(fresh);
      } else {
        setSelectedOrder(null);
      }
    }
  }, [orders]);

  const handleMoveNext = useCallback(async (order: Order) => {
    const pendingItems = order.items.filter((item) => item.status === "Pending");

    setPendingCode(order.orderCode);
    setNotice("");
    try {
      for (const item of pendingItems) {
        await updateOrderItemStatus(order.orderCode, item.orderItemId, "Preparing");
      }
      setNotice(`${order.orderCode}: đã bắt đầu nấu ${pendingItems.length} món`);
    } catch {
      setNotice("Cập nhật thất bại. Thử lại.");
    } finally {
      await onRefresh();
      setPendingCode(null);
    }
  }, [onRefresh]);

  const handleItemAction = useCallback(async (order: Order, itemId: string, nextStatus: OrderItemStatus) => {
    setPendingCode(order.orderCode);
    setNotice("");
    try {
      await updateOrderItemStatus(order.orderCode, itemId, nextStatus);
    } catch {
      setNotice("Cập nhật món thất bại.");
    } finally {
      await onRefresh();
      setPendingCode(null);
    }
  }, [onRefresh]);

  return (
    <>
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-board">
        <KitchenColumn
          title="Đơn mới"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="confirmed"
          orders={confirmed}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          pendingCode={pendingCode}
        />
        <KitchenColumn
          title="Đang nấu"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="preparing"
          orders={preparing}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          pendingCode={pendingCode}
        />
        <KitchenColumn
          title="Sẵn sàng"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="ready"
          orders={ready}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          pendingCode={pendingCode}
        />
      </div>

      {selectedOrder ? (
        <OrderDetailModal
          order={selectedOrder}
          onClose={() => setSelectedOrder(null)}
          onItemAction={handleItemAction}
          onMoveNext={handleMoveNext}
          isPending={pendingCode === selectedOrder.orderCode}
        />
      ) : null}
    </>
  );
}
