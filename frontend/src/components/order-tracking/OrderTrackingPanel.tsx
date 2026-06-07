import type { OrderItemStatus, OrderTrackingOrder } from "../../types";

const statusDescriptions: Record<OrderItemStatus, string> = {
  Pending: "Bep da nhan mon va dang xep hang xu ly.",
  Preparing: "Dau bep dang che bien mon nay.",
  Ready: "Mon da san sang de phuc vu.",
  Served: "Mon da duoc phuc vu.",
  Cancelled: "Mon da huy.",
};

type OrderTrackingPanelProps = {
  order: OrderTrackingOrder;
};

export function OrderTrackingPanel({ order }: OrderTrackingPanelProps) {
  const readyCount = order.items.filter((item) => item.status === "Ready").length;

  return (
    <section className="order-tracking-panel" aria-label="Customer order tracking">
      <div className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Order tracking</p>
          <h3>{order.orderCode}</h3>
          <span>
            {order.tableCode ? `Ban ${order.tableCode}` : "Pickup"} - {order.status}
          </span>
        </div>
        <strong>
          {readyCount}/{order.items.length}
          <small> mon Ready</small>
        </strong>
      </div>

      <div className="tracking-timeline">
        {["Placed", "Preparing", "Ready", "Served"].map((status, index) => (
          <div className={getTimelineClass(order.status, status)} key={status}>
            <span>{index + 1}</span>
            <div>
              <h3>{status}</h3>
              <p>{getTimelineCopy(status)}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="tracking-item-list">
        {order.items.map((item) => (
          <article className="tracking-item" key={item.orderItemId}>
            <div>
              <strong>{item.name}</strong>
              <p>
                x{item.quantity} - {statusDescriptions[item.status]}
              </p>
            </div>
            <span className={`status-pill status-${item.status.toLowerCase()}`}>
              {item.status}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function getTimelineCopy(status: string) {
  switch (status) {
    case "Placed":
      return "Don da duoc ghi nhan.";
    case "Preparing":
      return "Bep dang xu ly cac mon.";
    case "Ready":
      return "Mon san sang de mang ra.";
    default:
      return "Nhan vien xac nhan phuc vu.";
  }
}

function getTimelineClass(currentStatus: string, timelineStatus: string) {
  const order = ["Placed", "Preparing", "Ready", "Served"];
  const currentIndex = order.indexOf(currentStatus);
  const timelineIndex = order.indexOf(timelineStatus);

  return timelineIndex <= currentIndex
    ? "tracking-step tracking-step-active"
    : "tracking-step";
}
