import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import "../../../components/order-tracking/realtime-order.css";
import {
  publishOrderRealtimeEvent,
  simulateRealtimeError,
  simulateReconnectCycle,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
  type RealtimeConnectionStatus,
} from "../../../services/realtimeOrderService";
import { getOrderTracking } from "../../../services/orderService";
import type {
  OrderItemStatus,
  OrderRealtimeEvent,
  OrderTrackingItem,
  OrderTrackingOrder,
} from "../../../types";
import { PageShell } from "../../PageShell";

export function OrderTrackingPage() {
  const { orderCode = "ORD-1001" } = useParams();
  const [order, setOrder] = useState<OrderTrackingOrder | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<RealtimeConnectionStatus>("connected");
  const [eventLog, setEventLog] = useState<OrderRealtimeEvent[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    getOrderTracking(orderCode)
      .then(setOrder)
      .catch(() => setErrorMessage("Không tải được trạng thái đơn hàng."));
  }, [orderCode]);

  useEffect(() => {
    const unsubscribeConnection = subscribeRealtimeConnection(setConnectionStatus);
    const unsubscribeRealtime = subscribeOrderRealtime((event) => {
      if (event.payload.orderCode !== orderCode) {
        return;
      }

      setEventLog((current) => [event, ...current].slice(0, 4));
      setOrder((current) => (current ? applyRealtimeEvent(current, event) : current));
    });

    return () => {
      unsubscribeConnection();
      unsubscribeRealtime();
    };
  }, [orderCode]);

  const stats = useMemo(() => {
    const items = order?.items ?? [];

    return [
      {
        label: "Trạng thái đơn",
        value: order?.status ?? "Loading",
        detail: "Dùng enum OrderStatus trong contract",
      },
      {
        label: "Món đang bếp",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Cập nhật bằng sự kiện demo realtime",
      },
      {
        label: "Món Ready",
        value: String(items.filter((item) => item.status === "Ready").length),
        detail: "Không cần reload trang",
      },
    ];
  }, [order]);

  function publishNextMockEvent() {
    if (!order) {
      return;
    }

    const nextItem =
      order.items.find((item) => item.status === "Pending") ??
      order.items.find((item) => item.status === "Preparing");

    if (!nextItem) {
      simulateRealtimeError();
      return;
    }

    const nextStatus: OrderItemStatus =
      nextItem.status === "Pending" ? "Preparing" : "Ready";

    publishOrderRealtimeEvent({
      event: "order.itemStatusChanged",
      payload: {
        orderId: order.orderId,
        orderCode: order.orderCode,
        orderItemId: nextItem.orderItemId,
        menuItemName: nextItem.name,
        status: nextStatus,
        updatedAt: new Date().toISOString(),
      },
    });
  }

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title={`Đơn ${orderCode}`}
      description="Khách theo dõi trạng thái từng món qua sự kiện realtime theo contract SignalR, không cần tải lại trang."
      stats={stats}
    >
      <section className="realtime-status-bar">
        <div>
          <strong>Theo dõi món theo thời gian thực</strong>
          <p>Đang nghe sự kiện `order.itemStatusChanged` cho {orderCode}.</p>
        </div>
        <span className={`connection-pill connection-${connectionStatus}`}>
          {connectionStatus}
        </span>
        <div className="tracking-action-row">
          <button onClick={publishNextMockEvent} type="button">
            Cập nhật món tiếp theo
          </button>
          <button onClick={simulateReconnectCycle} type="button">
            Giả lập reconnect
          </button>
          <button onClick={simulateRealtimeError} type="button">
            Giả lập lỗi
          </button>
        </div>
      </section>

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}
      {order ? <CustomerOrderTrackingPanel order={order} /> : <p>Đang tải đơn hàng...</p>}

      <section className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Payload realtime gần nhất</p>
          <h3>{eventLog[0]?.event ?? "Chưa có sự kiện"}</h3>
          <span>Phần này dùng làm evidence khi review E2E customer flow.</span>
        </div>
        <pre>{eventLog[0] ? JSON.stringify(eventLog[0].payload, null, 2) : "{}"}</pre>
      </section>
    </PageShell>
  );
}

const itemStatusDescriptions: Record<OrderItemStatus, string> = {
  Pending: "Bếp đã nhận món và đang xếp hàng xử lý.",
  Preparing: "Đầu bếp đang chế biến món này.",
  Ready: "Món đã sẵn sàng để phục vụ.",
  Served: "Món đã được phục vụ.",
  Cancelled: "Món đã hủy.",
};

const timelineLabels: Record<string, string> = {
  Placed: "Đã ghi nhận",
  Preparing: "Đang chế biến",
  Ready: "Sẵn sàng",
  Served: "Đã phục vụ",
};

function CustomerOrderTrackingPanel({ order }: { order: OrderTrackingOrder }) {
  const readyCount = order.items.filter((item) => item.status === "Ready").length;

  return (
    <section className="order-tracking-panel" aria-label="Customer order tracking">
      <div className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Order tracking</p>
          <h3>{order.orderCode}</h3>
          <span>
            {order.tableCode ? `Bàn ${order.tableCode}` : "Mang về"} - {order.status}
          </span>
        </div>
        <strong>
          {readyCount}/{order.items.length}
          <small> món sẵn sàng</small>
        </strong>
      </div>

      <div className="tracking-timeline">
        {["Placed", "Preparing", "Ready", "Served"].map((status, index) => (
          <div className={getTimelineClass(order.status, status)} key={status}>
            <span>{index + 1}</span>
            <div>
              <h3>{timelineLabels[status]}</h3>
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
                x{item.quantity} - {itemStatusDescriptions[item.status]}
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

function applyRealtimeEvent(
  order: OrderTrackingOrder,
  event: OrderRealtimeEvent,
): OrderTrackingOrder {
  if (event.event === "order.statusChanged") {
    return {
      ...order,
      status: event.payload.status,
      updatedAt: event.payload.updatedAt,
    };
  }

  if (event.event !== "order.itemStatusChanged") {
    return order;
  }

  const items = order.items.map((item) =>
    item.orderItemId === event.payload.orderItemId
      ? {
          ...item,
          status: event.payload.status,
          updatedAt: event.payload.updatedAt,
        }
      : item,
  );

  return {
    ...order,
    status: calculateOrderStatus(items),
    updatedAt: event.payload.updatedAt,
    items,
  };
}

function calculateOrderStatus(items: OrderTrackingItem[]) {
  if (items.every((item) => item.status === "Ready" || item.status === "Served")) {
    return "Ready" as const;
  }

  if (items.some((item) => item.status === "Preparing" || item.status === "Ready")) {
    return "Preparing" as const;
  }

  return "Placed" as const;
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
