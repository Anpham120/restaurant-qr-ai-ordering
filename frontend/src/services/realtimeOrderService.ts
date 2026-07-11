import { authStorage } from "@cmc/auth";
import { createOrderHubClient } from "@cmc/realtime-client";
import type { OrderItemStatus, OrderRealtimeEvent, OrderTrackingOrder } from "../types";

export type RealtimeConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected" | "error";
type RealtimeListener = (event: OrderRealtimeEvent) => void;
type ConnectionListener = (status: RealtimeConnectionStatus) => void;
const realtimeListeners = new Set<RealtimeListener>();
const connectionListeners = new Set<ConnectionListener>();
let connectionStatus: RealtimeConnectionStatus = "disconnected";

const client = createOrderHubClient({
  accessTokenFactory: authStorage.token,
  handlers: {
    onOrderCreated: payload => notifyRealtimeListeners({ event: "order.created", payload }),
    onOrderStatusChanged: payload => notifyRealtimeListeners({ event: "order.statusChanged", payload }),
    onOrderItemStatusChanged: payload => notifyRealtimeListeners({ event: "order.itemStatusChanged", payload }),
    onPaymentRequested: payload => notifyRealtimeListeners({ event: "payment.requested", payload }),
    onStatusChanged: setConnectionStatus,
  },
});

export async function connectOrderRealtime() { await client.connect(); }
export async function disconnectOrderRealtime() { await client.disconnect(); }
export async function watchOrderRealtime(orderCode: string, orderToken: string) { await client.watchOrder(orderCode, orderToken); }
export async function watchTableRealtime(tableCode: string) { await client.watchTable(tableCode); }
export function subscribeOrderRealtime(listener: RealtimeListener) { realtimeListeners.add(listener); return () => realtimeListeners.delete(listener); }
export function subscribeRealtimeConnection(listener: ConnectionListener) { connectionListeners.add(listener); listener(connectionStatus); return () => connectionListeners.delete(listener); }

// Kept for optimistic local updates and cross-tab compatibility only. Server events remain authoritative.
export function publishOrderRealtimeEvent(event: OrderRealtimeEvent) { notifyRealtimeListeners(event); }
export function createItemStatusChangedEvent(order: OrderTrackingOrder, orderItemId: string, status: OrderItemStatus): OrderRealtimeEvent {
  const item = order.items.find(orderItem => orderItem.orderItemId === orderItemId);
  return { event: "order.itemStatusChanged", payload: { orderId: order.orderId, orderCode: order.orderCode, orderItemId, menuItemName: item?.name ?? orderItemId, status, updatedAt: new Date().toISOString() } };
}
function setConnectionStatus(status: RealtimeConnectionStatus) { connectionStatus = status; connectionListeners.forEach(listener => listener(status)); }
function notifyRealtimeListeners(event: OrderRealtimeEvent) { realtimeListeners.forEach(listener => listener(event)); }
