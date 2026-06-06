import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { OrderTrackingPanel } from "../../../components/order-tracking/OrderTrackingPanel";
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
      .catch(() => setErrorMessage("Khong tai duoc trang thai don hang."));
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
        label: "Trang thai don",
        value: order?.status ?? "Loading",
        detail: "Dung enum OrderStatus trong contract",
      },
      {
        label: "Mon dang bep",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Cap nhat bang realtime/mock event",
      },
      {
        label: "Mon Ready",
        value: String(items.filter((item) => item.status === "Ready").length),
        detail: "Khong can reload trang",
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
      title={`Don ${orderCode}`}
      description="Khach theo doi trang thai tung mon qua mock realtime event dung contract SignalR, khong can reload trang."
      stats={stats}
    >
      <section className="realtime-status-bar">
        <div>
          <strong>Customer realtime tracking</strong>
          <p>Dang nghe event `order.itemStatusChanged` cho {orderCode}.</p>
        </div>
        <span className={`connection-pill connection-${connectionStatus}`}>
          {connectionStatus}
        </span>
        <div className="tracking-action-row">
          <button onClick={publishNextMockEvent} type="button">
            Phat mock event
          </button>
          <button onClick={simulateReconnectCycle} type="button">
            Test reconnect
          </button>
          <button onClick={simulateRealtimeError} type="button">
            Test error
          </button>
        </div>
      </section>

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}
      {order ? <OrderTrackingPanel order={order} /> : <p>Dang tai don hang...</p>}

      <section className="tracking-summary-card">
        <div>
          <p className="tracking-kicker">Last event payload</p>
          <h3>{eventLog[0]?.event ?? "Chua co event"}</h3>
          <span>Payload hien thi de lam evidence khi review issue.</span>
        </div>
        <pre>{eventLog[0] ? JSON.stringify(eventLog[0].payload, null, 2) : "{}"}</pre>
      </section>
    </PageShell>
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
