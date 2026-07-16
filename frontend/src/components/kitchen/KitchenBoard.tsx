import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type DragEvent as ReactDragEvent,
  type ReactNode,
} from "react";
import type { Order, OrderItemStatus } from "@cmc/shared-types";
import { CheckCircle2, Circle, Clock3, Flame, GripVertical, X } from "lucide-react";
import { updateOrderItemStatus, updateOrderStatus } from "../../services/orderService";
import {
  canDropKitchenOrder,
  getKitchenBoardAdvancePlan,
  getKitchenBoardColumn,
  type KitchenBoardColumn,
} from "./kitchenOrderPipeline";
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

function FinishCookingButton({
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
      className={`ops-btn ops-btn--primary${compact ? " ops-btn--sm" : ""}`}
      disabled={isPending}
      onClick={() => onMoveNext(order)}
      type="button"
    >
      <CheckCircle2 aria-hidden="true" size={compact ? 14 : 16} />
      {compact ? "Nấu xong" : "Đánh dấu tất cả đã sẵn sàng"}
    </button>
  );
}

function MarkServedButton({
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
      className="ops-btn ops-btn--primary"
      disabled={isPending}
      onClick={() => onMoveNext(order)}
      type="button"
    >
      <CheckCircle2 aria-hidden="true" size={compact ? 14 : 16} />
      {compact ? "Đã phục vụ" : "Xác nhận đã phục vụ"}
    </button>
  );
}

/* ---------- Order Card ---------- */
function OrderCard({
  order,
  column,
  onOpenDetail,
  onMoveNext,
  onDragStart,
  onDragEnd,
  isPending,
  isDragging,
}: {
  order: Order;
  column: KitchenBoardColumn;
  onOpenDetail: (order: Order) => void;
  onMoveNext: (order: Order) => void;
  onDragStart: (order: Order, event: ReactDragEvent<HTMLElement>) => void;
  onDragEnd: () => void;
  isPending: boolean;
  isDragging: boolean;
}) {
  const [elapsed, setElapsed] = useState(timeAgo(order.createdAt));

  useEffect(() => {
    const timer = setInterval(() => setElapsed(timeAgo(order.createdAt)), 10_000);
    return () => clearInterval(timer);
  }, [order.createdAt]);

  const isUrgent = Date.now() - new Date(order.createdAt).getTime() > 15 * 60_000;
  const readyCount = order.items.filter((i) => i.status === "Ready" || i.status === "Served").length;
  const totalCount = order.items.filter((i) => i.status !== "Cancelled").length;
  const isDraggable = column !== "served" && !isPending;

  return (
    <article
      className={`ops-card ops-card--${order.status.toLowerCase()}${isDragging ? " ops-card--dragging" : ""}`}
      draggable={isDraggable}
      onClick={() => onOpenDetail(order)}
      onDragEnd={onDragEnd}
      onDragStart={isDraggable ? (event) => onDragStart(order, event) : undefined}
      role="button"
      tabIndex={0}
      title={isDraggable ? "Kéo sang cột trạng thái tiếp theo" : undefined}
      onKeyDown={(e) => e.key === "Enter" && onOpenDetail(order)}
    >
      <div className="ops-card-header">
        <span className="ops-card-code">
          {isDraggable ? <GripVertical aria-hidden="true" className="ops-card-drag-handle" size={15} /> : null}
          {order.orderCode}
        </span>
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
              item.status === "Ready" || item.status === "Served" || item.status === "Cancelled"
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
      {column === "preparing" ? (
        <div className="ops-card-actions" onClick={(e) => e.stopPropagation()}>
          <FinishCookingButton compact isPending={isPending} onMoveNext={onMoveNext} order={order} />
        </div>
      ) : null}
      {column === "ready" ? (
        <div className="ops-card-actions" onClick={(e) => e.stopPropagation()}>
          <MarkServedButton compact isPending={isPending} onMoveNext={onMoveNext} order={order} />
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
  const column = getKitchenBoardColumn(order.status) ?? "confirmed";

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
                    {item.status === "Pending" || item.status === "Preparing" ? (
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
        {column === "preparing" ? (
          <div className="ops-modal-footer">
            <FinishCookingButton isPending={isPending} onMoveNext={onMoveNext} order={order} />
          </div>
        ) : null}
        {column === "ready" ? (
          <div className="ops-modal-footer">
            <MarkServedButton isPending={isPending} onMoveNext={onMoveNext} order={order} />
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
  onCardDragStart,
  onCardDragEnd,
  onColumnDragOver,
  onColumnDragLeave,
  onColumnDrop,
  pendingCode,
  draggedOrderCode,
  isDropTarget,
}: {
  title: string;
  icon: ReactNode;
  column: KitchenBoardColumn;
  orders: Order[];
  onOpenDetail: (o: Order) => void;
  onMoveNext: (o: Order) => void;
  onCardDragStart: (order: Order, event: ReactDragEvent<HTMLElement>) => void;
  onCardDragEnd: () => void;
  onColumnDragOver: (column: KitchenBoardColumn, event: ReactDragEvent<HTMLDivElement>) => void;
  onColumnDragLeave: (column: KitchenBoardColumn, event: ReactDragEvent<HTMLDivElement>) => void;
  onColumnDrop: (column: KitchenBoardColumn, event: ReactDragEvent<HTMLDivElement>) => void;
  pendingCode: string | null;
  draggedOrderCode: string | null;
  isDropTarget: boolean;
}) {
  return (
    <div
      className={`ops-column ops-column--${column}${isDropTarget ? " ops-column--drop-target" : ""}`}
      onDragLeave={(event) => onColumnDragLeave(column, event)}
      onDragOver={(event) => onColumnDragOver(column, event)}
      onDrop={(event) => onColumnDrop(column, event)}
    >
      <div className="ops-column-header">
        <h3>{icon} {title}</h3>
        <span className="ops-count">{orders.length}</span>
      </div>
      {isDropTarget ? <div className="ops-drop-hint">Thả vào đây để chuyển trạng thái</div> : null}
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
              onDragStart={onCardDragStart}
              onDragEnd={onCardDragEnd}
              isPending={pendingCode === order.orderCode}
              isDragging={draggedOrderCode === order.orderCode}
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
  const [draggedOrderCode, setDraggedOrderCode] = useState<string | null>(null);
  const [dropTargetColumn, setDropTargetColumn] = useState<KitchenBoardColumn | null>(null);

  const confirmed = useMemo(
    () => orders.filter((o) => getKitchenBoardColumn(o.status) === "confirmed"),
    [orders],
  );
  const preparing = useMemo(
    () => orders.filter((o) => getKitchenBoardColumn(o.status) === "preparing"),
    [orders],
  );
  const ready = useMemo(
    () => orders.filter((o) => getKitchenBoardColumn(o.status) === "ready"),
    [orders],
  );
  const served = useMemo(
    () => orders.filter((o) => getKitchenBoardColumn(o.status) === "served"),
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
    setPendingCode(order.orderCode);
    setNotice("");
    try {
      const plan = getKitchenBoardAdvancePlan(order.status);
      if (!plan) {
        return;
      }

      if (plan.kind === "order") {
        await updateOrderStatus(order.orderCode, plan.nextOrderStatus);
        setNotice(`${order.orderCode}: đã phục vụ`);
        return;
      }

      const eligibleItems = order.items.filter((item) =>
        plan.eligibleItemStatuses.some((status) => status === item.status),
      );
      for (const item of eligibleItems) {
        await updateOrderItemStatus(order.orderCode, item.orderItemId, plan.nextItemStatus);
      }

      if (plan.nextItemStatus === "Preparing") {
        setNotice(`${order.orderCode}: đã bắt đầu nấu ${eligibleItems.length} món`);
      } else {
        setNotice(`${order.orderCode}: ${eligibleItems.length} món đã sẵn sàng`);
      }
    } catch {
      setNotice("Cập nhật thất bại. Thử lại.");
    } finally {
      await onRefresh();
      setPendingCode(null);
    }
  }, [onRefresh]);

  const handleCardDragStart = useCallback((order: Order, event: ReactDragEvent<HTMLElement>) => {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", order.orderCode);
    setDraggedOrderCode(order.orderCode);
    setDropTargetColumn(null);
  }, []);

  const handleCardDragEnd = useCallback(() => {
    setDraggedOrderCode(null);
    setDropTargetColumn(null);
  }, []);

  const handleColumnDragOver = useCallback((
    column: KitchenBoardColumn,
    event: ReactDragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();
    const draggedOrder = orders.find((order) => order.orderCode === draggedOrderCode);
    const isAllowed = Boolean(
      draggedOrder
      && draggedOrder.orderCode !== pendingCode
      && canDropKitchenOrder(draggedOrder.status, column),
    );
    event.dataTransfer.dropEffect = isAllowed ? "move" : "none";
    setDropTargetColumn(isAllowed ? column : null);
  }, [draggedOrderCode, orders, pendingCode]);

  const handleColumnDragLeave = useCallback((
    column: KitchenBoardColumn,
    event: ReactDragEvent<HTMLDivElement>,
  ) => {
    const nextTarget = event.relatedTarget as Node | null;
    if (nextTarget && event.currentTarget.contains(nextTarget)) return;
    setDropTargetColumn((current) => current === column ? null : current);
  }, []);

  const handleColumnDrop = useCallback((
    column: KitchenBoardColumn,
    event: ReactDragEvent<HTMLDivElement>,
  ) => {
    event.preventDefault();
    event.stopPropagation();
    const draggedOrder = orders.find((order) => order.orderCode === draggedOrderCode);
    setDraggedOrderCode(null);
    setDropTargetColumn(null);

    if (
      !draggedOrder
      || draggedOrder.orderCode === pendingCode
      || !canDropKitchenOrder(draggedOrder.status, column)
    ) {
      setNotice("Chỉ có thể chuyển thẻ sang cột trạng thái kế tiếp.");
      return;
    }

    void handleMoveNext(draggedOrder);
  }, [draggedOrderCode, handleMoveNext, orders, pendingCode]);

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

  const kitchenDragHandlers = {
    onCardDragStart: handleCardDragStart,
    onCardDragEnd: handleCardDragEnd,
    onColumnDragOver: handleColumnDragOver,
    onColumnDragLeave: handleColumnDragLeave,
    onColumnDrop: handleColumnDrop,
    draggedOrderCode,
  };

  return (
    <>
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-board ops-board--kitchen">
        <KitchenColumn
          title="Đơn mới"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="confirmed"
          orders={confirmed}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          {...kitchenDragHandlers}
          pendingCode={pendingCode}
          isDropTarget={dropTargetColumn === "confirmed"}
        />
        <KitchenColumn
          title="Đang nấu"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="preparing"
          orders={preparing}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          {...kitchenDragHandlers}
          pendingCode={pendingCode}
          isDropTarget={dropTargetColumn === "preparing"}
        />
        <KitchenColumn
          title="Sẵn sàng"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="ready"
          orders={ready}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          {...kitchenDragHandlers}
          pendingCode={pendingCode}
          isDropTarget={dropTargetColumn === "ready"}
        />
        <KitchenColumn
          title="Đã phục vụ"
          icon={<Circle aria-hidden="true" fill="currentColor" size={12} />}
          column="served"
          orders={served}
          onOpenDetail={setSelectedOrder}
          onMoveNext={handleMoveNext}
          {...kitchenDragHandlers}
          pendingCode={pendingCode}
          isDropTarget={dropTargetColumn === "served"}
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
