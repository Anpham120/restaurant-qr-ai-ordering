import type {
  OrderItemStatus,
  OrderRealtimeEvent,
  OrderTrackingOrder,
} from "../types";

export type RealtimeConnectionStatus = "connected" | "reconnecting" | "error";

type RealtimeListener = (event: OrderRealtimeEvent) => void;
type ConnectionListener = (status: RealtimeConnectionStatus) => void;

const realtimeListeners = new Set<RealtimeListener>();
const connectionListeners = new Set<ConnectionListener>();
const channel =
  typeof window !== "undefined" && "BroadcastChannel" in window
    ? new BroadcastChannel("cmc-order-realtime")
    : null;

let connectionStatus: RealtimeConnectionStatus = "connected";

channel?.addEventListener("message", (message: MessageEvent<OrderRealtimeEvent>) => {
  notifyRealtimeListeners(message.data);
});

export function subscribeOrderRealtime(listener: RealtimeListener) {
  realtimeListeners.add(listener);

  return () => {
    realtimeListeners.delete(listener);
  };
}

export function subscribeRealtimeConnection(listener: ConnectionListener) {
  connectionListeners.add(listener);
  listener(connectionStatus);

  return () => {
    connectionListeners.delete(listener);
  };
}

export function publishOrderRealtimeEvent(event: OrderRealtimeEvent) {
  notifyRealtimeListeners(event);
  channel?.postMessage(event);
}

export function simulateReconnectCycle() {
  setConnectionStatus("reconnecting");

  window.setTimeout(() => {
    setConnectionStatus("connected");
  }, 900);
}

export function simulateRealtimeError() {
  setConnectionStatus("error");

  window.setTimeout(() => {
    setConnectionStatus("connected");
  }, 1500);
}

export function createItemStatusChangedEvent(
  order: OrderTrackingOrder,
  orderItemId: string,
  status: OrderItemStatus,
): OrderRealtimeEvent {
  const item = order.items.find((orderItem) => orderItem.orderItemId === orderItemId);

  return {
    event: "order.itemStatusChanged",
    payload: {
      orderId: order.orderId,
      orderCode: order.orderCode,
      orderItemId,
      menuItemName: item?.name ?? orderItemId,
      status,
      updatedAt: new Date().toISOString(),
    },
  };
}

function setConnectionStatus(status: RealtimeConnectionStatus) {
  connectionStatus = status;
  connectionListeners.forEach((listener) => listener(status));
}

function notifyRealtimeListeners(event: OrderRealtimeEvent) {
  realtimeListeners.forEach((listener) => listener(event));
}
