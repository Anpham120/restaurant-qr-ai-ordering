import { useEffect, useMemo, useState } from "react";
import { KitchenBoard } from "../../components/kitchen/KitchenBoard";
import "../../components/order-tracking/realtime-order.css";
import {
  createItemStatusChangedEvent,
  publishOrderRealtimeEvent,
  simulateRealtimeError,
  simulateReconnectCycle,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
  type RealtimeConnectionStatus,
} from "../../services/realtimeOrderService";
import { getKitchenOrders, updateOrderItemStatus } from "../../services/orderService";
import type {
  OrderItemStatus,
  OrderRealtimeEvent,
  OrderTrackingItem,
  OrderTrackingOrder,
} from "../../types";
import { PageShell } from "../PageShell";

export function KitchenRealtimePage() {
  const [orders, setOrders] = useState<OrderTrackingOrder[]>([]);
  const [connectionStatus, setConnectionStatus] =
    useState<RealtimeConnectionStatus>("connected");
  const [eventLog, setEventLog] = useState<OrderRealtimeEvent[]>([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    getKitchenOrders()
      .then(setOrders)
      .catch(() => setErrorMessage("Khong tai duoc danh sach don bep."));
  }, []);

  useEffect(() => {
    const unsubscribeConnection = subscribeRealtimeConnection(setConnectionStatus);
    const unsubscribeRealtime = subscribeOrderRealtime((event) => {
      setEventLog((current) => [event, ...current].slice(0, 4));
      setOrders((current) => applyRealtimeEvent(current, event));
    });

    return () => {
      unsubscribeConnection();
      unsubscribeRealtime();
    };
  }, []);

  const stats = useMemo(() => {
    const items = orders.flatMap((order) => order.items);

    return [
      {
        label: "Pending",
        value: String(items.filter((item) => item.status === "Pending").length),
        detail: "Mon moi vao hang doi",
      },
      {
        label: "Preparing",
        value: String(items.filter((item) => item.status === "Preparing").length),
        detail: "Bep dang che bien",
      },
      {
        label: "Ready",
        value: String(items.filter((item) => item.status === "Ready").length),
        detail: "Cho phuc vu ra ban",
      },
    ];
  }, [orders]);

  async function handleUpdateItemStatus(
    order: OrderTrackingOrder,
    item: OrderTrackingItem,
    status: OrderItemStatus,
  ) {
    setErrorMessage("");

    try {
      const updatedOrder = await updateOrderItemStatus(
        order.orderCode,
        item.orderItemId,
        status,
      );

      publishOrderRealtimeEvent(
        createItemStatusChangedEvent(updatedOrder, item.orderItemId, status),
      );
    } catch {
      setErrorMessage("Khong cap nhat duoc trang thai mon.");
      simulateRealtimeError();
    }
  }

  return (
    <PageShell
      eyebrow="Kitchen realtime"
      title="Bang bep CMC"
      description="Bep nhan mon theo cot Pending, Preparing, Ready va phat mock realtime event dung contract de man hinh khach cap nhat khong can reload."
      variant="kitchen"
      stats={stats}
    >
      <RealtimeStatusBar
        connectionStatus={connectionStatus}
        onError={simulateRealtimeError}
        onReconnect={simulateReconnectCycle}
      />

      {errorMessage ? <p className="realtime-error">{errorMessage}</p> : null}

      <KitchenBoard orders={orders} onUpdateItemStatus={handleUpdateItemStatus} />

      <EventPreview events={eventLog} />
    </PageShell>
  );
}

function RealtimeStatusBar({
  connectionStatus,
  onError,
  onReconnect,
}: {
  connectionStatus: RealtimeConnectionStatus;
  onError: () => void;
  onReconnect: () => void;
}) {
  return (
    <section className="realtime-status-bar">
      <div>
        <strong>Realtime adapter</strong>
        <p>Mock event source theo contract SignalR `/hubs/orders`.</p>
      </div>
      <span className={`connection-pill connection-${connectionStatus}`}>
        {connectionStatus}
      </span>
      <div className="realtime-status-actions">
        <button onClick={onReconnect} type="button">
          Test reconnect
        </button>
        <button onClick={onError} type="button">
          Test error
        </button>
      </div>
    </section>
  );
}

function EventPreview({ events }: { events: OrderRealtimeEvent[] }) {
  return (
    <section className="tracking-summary-card">
      <div>
        <p className="tracking-kicker">Event payload</p>
        <h3>{events[0]?.event ?? "Chua co event"}</h3>
        <span>Cap nhat item tren bep se tao payload `order.itemStatusChanged`.</span>
      </div>
      <pre>{events[0] ? JSON.stringify(events[0].payload, null, 2) : "{}"}</pre>
    </section>
  );
}

function applyRealtimeEvent(
  orders: OrderTrackingOrder[],
  event: OrderRealtimeEvent,
): OrderTrackingOrder[] {
  if (event.event === "order.itemStatusChanged") {
    return orders.map((order) => {
      if (order.orderCode !== event.payload.orderCode) {
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
    });
  }

  if (event.event === "order.statusChanged") {
    return orders.map((order) =>
      order.orderCode === event.payload.orderCode
        ? { ...order, status: event.payload.status, updatedAt: event.payload.updatedAt }
        : order,
    );
  }

  return orders;
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
