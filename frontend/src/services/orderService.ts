import { createApiClient } from "@cmc/api-client";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  OrderItemStatus,
  PaymentResponse,
  OrderTrackingOrder,
  VietQrPaymentResponse,
} from "../types";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});

export async function createOrder(
  payload: CreateOrderRequest,
): Promise<CreateOrderResponse> {
  const response = await api.orders.create(payload);
  return response as CreateOrderResponse;
}

export async function getKitchenOrders(): Promise<OrderTrackingOrder[]> {
  const response = await api.orders.list();
  return response.orders as OrderTrackingOrder[];
}

export async function getOrderTracking(orderCode: string): Promise<OrderTrackingOrder> {
  return api.orders.get(orderCode) as Promise<OrderTrackingOrder>;
}

export async function updateOrderItemStatus(
  orderCode: string,
  orderItemId: string,
  status: OrderItemStatus,
): Promise<OrderTrackingOrder> {
  return api.orders.updateItemStatus(orderCode, orderItemId, status) as Promise<OrderTrackingOrder>;
}

export async function updateOrderStatus(
  orderCode: string,
  status: OrderTrackingOrder["status"],
): Promise<OrderTrackingOrder> {
  return api.orders.updateStatus(orderCode, status) as Promise<OrderTrackingOrder>;
}

export async function getOrderPayment(orderCode: string): Promise<PaymentResponse> {
  return api.payments.get(orderCode) as Promise<PaymentResponse>;
}

export async function generateVietQrPayment(orderCode: string): Promise<VietQrPaymentResponse> {
  return api.payments.generateVietQr(orderCode) as Promise<VietQrPaymentResponse>;
}

export async function confirmOrderPayment(orderCode: string, note?: string): Promise<PaymentResponse> {
  return api.payments.confirm(orderCode, { note }) as Promise<PaymentResponse>;
}

// An order needs staff to collect/resolve payment when it is not already paid and
// either a payment attempt is open (Pending/Failed) or the order has reached the
// customer (Served/Delivering/Delivered/Completed) still unpaid.
export function isAwaitingPayment(order: OrderTrackingOrder): boolean {
  if (order.status === "Cancelled") return false;
  if (
    order.paymentStatus === "Paid" ||
    order.paymentStatus === "Confirmed" ||
    order.paymentStatus === "Cancelled"
  ) {
    return false;
  }
  if (order.paymentStatus === "Pending" || order.paymentStatus === "Failed") return true;
  return (
    order.status === "Served" ||
    order.status === "Delivering" ||
    order.status === "Delivered" ||
    order.status === "Completed"
  );
}
