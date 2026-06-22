import type { OrderItemStatus, OrderTrackingOrder } from "../../types";

const statusDescriptions: Record<OrderItemStatus, string> = {
  Pending: "Bếp đã nhận món và đang xếp hàng xử lý.",
  Preparing: "Đầu bếp đang chế biến món này.",
  Ready: "Món đã sẵn sàng để phục vụ.",
  Served: "Món đã được phục vụ.",
  Cancelled: "Món đã hủy.",
};

const itemStatusLabels: Record<OrderItemStatus, string> = {
  Pending: "Chờ xử lý",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
  Cancelled: "Đã hủy",
};

const timelineSteps: Array<{ key: string; label: string }> = [
  { key: "Placed", label: "Đã đặt" },
  { key: "Preparing", label: "Đang chế biến" },
  { key: "Ready", label: "Sẵn sàng" },
  { key: "Served", label: "Đã phục vụ" },
];

type OrderTrackingPanelProps = {
  order: OrderTrackingOrder;
};

export function OrderTrackingPanel({ order }: OrderTrackingPanelProps) {
  const readyCount = order.items.filter((item) => item.status === "Ready").length;

  return (
    <section className="order-tracking-panel" aria-label="Theo dõi đơn hàng">
      <div className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Theo dõi đơn</p>
          <h3>{order.orderCode}</h3>
          <span>
            {order.tableCode ? `Bàn ${order.tableCode}` : "Mang về"} –{" "}
            {orderStatusLabel(order.status)}
          </span>
        </div>
        <strong>
          {readyCount}/{order.items.length}
          <small> món sẵn sàng</small>
        </strong>
      </div>

      <div className="tracking-timeline">
        {timelineSteps.map((step, index) => (
          <div className={getTimelineClass(order.status, step.key)} key={step.key}>
            <span>{index + 1}</span>
            <div>
              <h3>{step.label}</h3>
              <p>{getTimelineCopy(step.key)}</p>
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
                x{item.quantity} – {statusDescriptions[item.status]}
              </p>
            </div>
            <span className={`status-pill status-${item.status.toLowerCase()}`}>
              {itemStatusLabels[item.status]}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function orderStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    Placed: "Đã đặt",
    Confirmed: "Đã xác nhận",
    Preparing: "Đang chế biến",
    Ready: "Sẵn sàng",
    Served: "Đã phục vụ",
    Completed: "Hoàn tất",
    Cancelled: "Đã hủy",
  };
  return labels[status] ?? status;
}

function getTimelineCopy(status: string) {
  switch (status) {
    case "Placed":
      return "Đơn đã được ghi nhận.";
    case "Preparing":
      return "Bếp đang xử lý các món.";
    case "Ready":
      return "Món sẵn sàng để mang ra.";
    default:
      return "Nhân viên xác nhận phục vụ.";
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
