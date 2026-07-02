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

// Per-order customer access tokens, keyed by order code. Issued by the backend at create
// time and replayed (X-Order-Token) on customer reads so guessable order codes can't be
// enumerated. Operators read via their bearer token instead and don't need this.
const ORDER_TOKENS_KEY = "cmc.orderTokens";

function readOrderTokens(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(window.localStorage.getItem(ORDER_TOKENS_KEY) ?? "{}") as Record<string, string>;
  } catch {
    return {};
  }
}

function rememberOrderToken(orderCode: string, token: string | null | undefined): void {
  if (typeof window === "undefined" || !token) return;
  const tokens = readOrderTokens();
  tokens[orderCode] = token;
  window.localStorage.setItem(ORDER_TOKENS_KEY, JSON.stringify(tokens));
}

function getOrderToken(orderCode: string): string | undefined {
  return readOrderTokens()[orderCode];
}

export async function createOrder(
  payload: CreateOrderRequest,
): Promise<CreateOrderResponse> {
  const response = (await api.orders.create(payload)) as CreateOrderResponse;
  rememberOrderToken(response.orderCode, response.customerAccessToken);
  return response;
}

export async function getKitchenOrders(): Promise<OrderTrackingOrder[]> {
  const response = await api.orders.list();
  return response.orders as OrderTrackingOrder[];
}

export async function getOrderTracking(orderCode: string): Promise<OrderTrackingOrder> {
  return api.orders.get(orderCode, getOrderToken(orderCode)) as Promise<OrderTrackingOrder>;
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
  return api.payments.get(orderCode, getOrderToken(orderCode)) as Promise<PaymentResponse>;
}

export async function generateVietQrPayment(orderCode: string): Promise<VietQrPaymentResponse> {
  return api.payments.generateVietQr(orderCode, getOrderToken(orderCode)) as Promise<VietQrPaymentResponse>;
}

export async function confirmOrderPayment(orderCode: string, note?: string): Promise<PaymentResponse> {
  return api.payments.confirm(orderCode, { note }) as Promise<PaymentResponse>;
}

export async function refundOrderPayment(orderCode: string, note?: string): Promise<PaymentResponse> {
  return api.payments.refund(orderCode, { note }) as Promise<PaymentResponse>;
}

// A collected payment (Confirmed/Paid) can be reversed by staff/admin; once Refunded it is terminal.
export function isRefundable(order: OrderTrackingOrder): boolean {
  return order.paymentStatus === "Confirmed" || order.paymentStatus === "Paid";
}

// An order needs staff to collect/resolve payment when it is not already paid and
// either a payment attempt is open (Pending/Failed) or the order has reached the
// table (Served/Completed) still unpaid.
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
    order.status === "Completed"
  );
}
