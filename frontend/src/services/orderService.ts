import type {
  CreateOrderRequest,
  CreateOrderResponse,
  OrderItemStatus,
  PaymentMethod,
  PaymentRequestResponse,
  PaymentResponse,
  OrderTrackingOrder,
  ValidatePromotionResponse,
  VietQrPaymentResponse,
} from "../types";
import { api } from "./apiClient";

// Per-order customer access tokens, keyed by order code. Issued by the backend at create
// time and replayed (X-Order-Token) on customer reads so guessable order codes can't be
// enumerated. Operators read via their bearer token instead and don't need this.
const ORDER_TOKENS_KEY = "cmc.orderTokens";
const ORDER_IDEMPOTENCY_KEY = "cmc.orderIdempotency";
const PAYMENT_IDEMPOTENCY_KEY = "cmc.paymentIdempotency";
const VIETQR_CACHE_KEY = "cmc.vietQrPayments";

type PendingIdempotency = { fingerprint: string; key: string };

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

export function getCustomerOrderToken(orderCode: string): string | undefined {
  return readOrderTokens()[orderCode];
}

export function hasCustomerOrderToken(orderCode: string): boolean {
  return Boolean(getCustomerOrderToken(orderCode));
}

function createIdempotencyKey(prefix: "order" | "payment") {
  const suffix = globalThis.crypto?.randomUUID?.() ??
    `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${suffix}`;
}

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    return JSON.parse(window.localStorage.getItem(key) ?? "") as T;
  } catch {
    return fallback;
  }
}

function getOrderIdempotency(payload: CreateOrderRequest): PendingIdempotency {
  const fingerprint = JSON.stringify(payload);
  const pending = readJson<PendingIdempotency | null>(ORDER_IDEMPOTENCY_KEY, null);
  if (pending?.fingerprint === fingerprint) return pending;
  const next = { fingerprint, key: createIdempotencyKey("order") };
  window.localStorage.setItem(ORDER_IDEMPOTENCY_KEY, JSON.stringify(next));
  return next;
}

function clearOrderIdempotency(pending: PendingIdempotency) {
  const current = readJson<PendingIdempotency | null>(ORDER_IDEMPOTENCY_KEY, null);
  if (current?.fingerprint === pending.fingerprint && current.key === pending.key) {
    window.localStorage.removeItem(ORDER_IDEMPOTENCY_KEY);
  }
}

function getPaymentIdempotency(orderCode: string, method: PaymentMethod) {
  const records = readJson<Record<string, string>>(PAYMENT_IDEMPOTENCY_KEY, {});
  const fingerprint = `${orderCode}:${method}`;
  const existing = records[fingerprint];
  if (existing) return existing;
  const key = createIdempotencyKey("payment");
  records[fingerprint] = key;
  window.localStorage.setItem(PAYMENT_IDEMPOTENCY_KEY, JSON.stringify(records));
  return key;
}

function rememberVietQrPayment(data: VietQrPaymentResponse | null) {
  if (!data || typeof window === "undefined") return;
  const records = readJson<Record<string, VietQrPaymentResponse>>(VIETQR_CACHE_KEY, {});
  records[data.orderCode] = data;
  window.localStorage.setItem(VIETQR_CACHE_KEY, JSON.stringify(records));
}

export function getStoredVietQrPayment(orderCode: string): VietQrPaymentResponse | null {
  return readJson<Record<string, VietQrPaymentResponse>>(VIETQR_CACHE_KEY, {})[orderCode] ?? null;
}

export async function createOrder(
  payload: CreateOrderRequest,
): Promise<CreateOrderResponse> {
  const pending = getOrderIdempotency(payload);
  const response = (await api.orders.create(payload, pending.key)) as CreateOrderResponse;
  rememberOrderToken(response.orderCode, response.customerAccessToken);
  clearOrderIdempotency(pending);
  return response;
}

export async function validatePromotion(
  code: string,
  subtotalAmount: number,
): Promise<ValidatePromotionResponse> {
  return api.promotions.validate({ code, subtotalAmount }) as Promise<ValidatePromotionResponse>;
}

export async function getKitchenOrders(): Promise<OrderTrackingOrder[]> {
  const response = await api.orders.list();
  return response.orders as OrderTrackingOrder[];
}

export async function getOrderTracking(orderCode: string): Promise<OrderTrackingOrder> {
  return api.orders.get(orderCode, getCustomerOrderToken(orderCode)) as Promise<OrderTrackingOrder>;
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
  return api.payments.get(orderCode, getCustomerOrderToken(orderCode)) as Promise<PaymentResponse>;
}

export async function requestOrderPayment(
  orderCode: string,
  method: Exclude<PaymentMethod, "Unselected">,
): Promise<PaymentRequestResponse> {
  const orderToken = getCustomerOrderToken(orderCode);
  if (!orderToken) {
    throw new Error("Không còn quyền truy cập đơn này.");
  }
  const idempotencyKey = getPaymentIdempotency(orderCode, method);
  const response = await api.payments.request(
    orderCode,
    { method },
    orderToken,
    idempotencyKey,
  ) as PaymentRequestResponse;
  rememberVietQrPayment(response.vietQr);
  return response;
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
