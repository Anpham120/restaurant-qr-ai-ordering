import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import "../../../components/order-tracking/realtime-order.css";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
  watchOrderRealtime,
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

      setOrder((current) => (current ? applyRealtimeEvent(current, event) : current));
    });

    void connectOrderRealtime()
      .then(() => watchOrderRealtime(orderCode, order?.tableCode))
      .catch(() => setConnectionStatus("error"));

    return () => {
      unsubscribeConnection();
      unsubscribeRealtime();
      void disconnectOrderRealtime();
    };
  }, [orderCode, order?.tableCode]);

  const stats = useMemo(() => {
    const items = order?.items ?? [];

    return [
      {
        label: "Trạng thái đơn",
        value: order?.status ?? "Loading",
        detail: "Cập nhật theo trạng thái hiện tại",
      },
      {
        label: "Món đang bếp",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Theo dõi trạng thái chế biến",
      },
      {
        label: "Món Ready",
        value: String(items.filter((item) => item.status === "Ready").length),
        detail: "Không cần reload trang",
      },
    ];
  }, [order]);

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title={`Đơn ${orderCode}`}
      description="Khách theo dõi trạng thái từng món theo thời gian thực, không cần tải lại trang."
      stats={stats}
    >
      <section className="realtime-status-bar">
        <div>
          <strong>Theo dõi món theo thời gian thực</strong>
          <p>Đang cập nhật trạng thái cho {orderCode}.</p>
        </div>
        <span className={`connection-pill connection-${connectionStatus}`}>
          {connectionStatus}
        </span>
      </section>

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}
      {order ? <CustomerOrderTrackingPanel order={order} /> : <p>Đang tải đơn hàng...</p>}
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
