import type { OrderItemStatus, OrderTrackingItem, OrderTrackingOrder } from "../../types";

const kitchenColumns: OrderItemStatus[] = ["Pending", "Preparing", "Ready"];

const columnLabels: Record<OrderItemStatus, string> = {
  Pending: "Chờ bếp nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng phục vụ",
  Served: "Đã phục vụ",
  Cancelled: "Đã hủy",
};

type KitchenBoardProps = {
  orders: OrderTrackingOrder[];
  onUpdateItemStatus: (
    order: OrderTrackingOrder,
    item: OrderTrackingItem,
    status: OrderItemStatus,
  ) => void;
};

export function KitchenBoard({ orders, onUpdateItemStatus }: KitchenBoardProps) {
  const ticketCount = orders.reduce((total, order) => total + order.items.length, 0);

  if (ticketCount === 0) {
    return (
      <div className="admin-state-panel">
        <strong>Chưa có món trong bếp</strong>
        <p>Khi khách đặt món hoặc staff gửi phiếu bếp, ticket sẽ xuất hiện tại đây.</p>
      </div>
    );
  }

  return (
    <div className="realtime-kitchen-board" aria-label="Kitchen realtime board">
      {kitchenColumns.map((status) => {
        const tickets = orders.flatMap((order) =>
          order.items
            .filter((item) => item.status === status)
            .map((item) => ({ order, item })),
        );

        return (
          <section className="realtime-kitchen-lane" key={status}>
            <div className="realtime-lane-heading">
              <div>
                <h3>{columnLabels[status]}</h3>
                <p>{status}</p>
              </div>
              <span>{tickets.length} món</span>
            </div>

            {tickets.length === 0 ? (
              <p className="realtime-empty">Không có món trong cột này.</p>
            ) : (
              tickets.map(({ order, item }) => (
                <article className="realtime-ticket" key={`${order.orderCode}-${item.orderItemId}`}>
                  <div className="realtime-ticket-topline">
                    <strong>{item.name}</strong>
                    <span>x{item.quantity}</span>
                  </div>
                  <p>
                    {order.orderCode}
                    {order.tableCode ? ` - Bàn ${order.tableCode}` : " - Pickup"}
                  </p>
                  <small>Cập nhật: {formatTime(item.updatedAt)}</small>

                  <div className="realtime-ticket-actions">
                    <button
                      disabled={item.status === "Preparing"}
                      onClick={() => onUpdateItemStatus(order, item, "Preparing")}
                      type="button"
                    >
                      Bắt đầu
                    </button>
                    <button
                      disabled={item.status === "Ready"}
                      onClick={() => onUpdateItemStatus(order, item, "Ready")}
                      type="button"
                    >
                      Sẵn sàng
                    </button>
                  </div>
                </article>
              ))
            )}
          </section>
        );
      })}
    </div>
  );
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
