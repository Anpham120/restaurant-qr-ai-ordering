import type { OrderItemStatus, OrderTrackingItem, OrderTrackingOrder } from "../../types";

const kitchenColumns: OrderItemStatus[] = ["Pending", "Preparing", "Ready"];

type KitchenBoardProps = {
  orders: OrderTrackingOrder[];
  onUpdateItemStatus: (
    order: OrderTrackingOrder,
    item: OrderTrackingItem,
    status: OrderItemStatus,
  ) => void;
};

export function KitchenBoard({ orders, onUpdateItemStatus }: KitchenBoardProps) {
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
              <h3>{status}</h3>
              <span>{tickets.length} mon</span>
            </div>

            {tickets.length === 0 ? (
              <p className="realtime-empty">Khong co mon trong cot nay.</p>
            ) : (
              tickets.map(({ order, item }) => (
                <article className="realtime-ticket" key={`${order.orderCode}-${item.orderItemId}`}>
                  <div className="realtime-ticket-topline">
                    <strong>{item.name}</strong>
                    <span>x{item.quantity}</span>
                  </div>
                  <p>
                    {order.orderCode}
                    {order.tableCode ? ` - Ban ${order.tableCode}` : " - Pickup"}
                  </p>
                  <small>Cap nhat: {formatTime(item.updatedAt)}</small>

                  <div className="realtime-ticket-actions">
                    <button
                      disabled={item.status === "Preparing"}
                      onClick={() => onUpdateItemStatus(order, item, "Preparing")}
                      type="button"
                    >
                      Preparing
                    </button>
                    <button
                      disabled={item.status === "Ready"}
                      onClick={() => onUpdateItemStatus(order, item, "Ready")}
                      type="button"
                    >
                      Ready
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
