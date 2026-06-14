import { getApiBaseUrl } from "./apiClient";
import { getAuthHeaders } from "./authService";
import type {
  CreateOrderRequest,
  CreateOrderResponse,
  OrderItemStatus,
  OrderStatus,
  OrderTrackingOrder,
} from "../types";

type OrderListResponse = {
  orders: OrderTrackingOrder[];
  total: number;
};

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
};

function apiUrl(path: string) {
  return `${getApiBaseUrl()}${path}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => ({}))) as T & ApiErrorPayload;
  if (!response.ok) {
    const code = payload.error?.code ?? "API_ERROR";
    const message = payload.error?.message ?? "Không thể xử lý yêu cầu.";
    throw new Error(`${code}: ${message}`);
  }

  return payload;
}

export async function createOrder(payload: CreateOrderRequest): Promise<CreateOrderResponse> {
  const response = await fetch(apiUrl("/orders"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseJson<CreateOrderResponse>(response);
}

export async function getKitchenOrders(): Promise<OrderTrackingOrder[]> {
  const response = await fetch(apiUrl("/orders"), {
    headers: getAuthHeaders(),
  });
  const body = await parseJson<OrderListResponse>(response);

  return body.orders;
}

export async function getOrderTracking(orderCode: string): Promise<OrderTrackingOrder> {
  const response = await fetch(apiUrl(`/orders/${encodeURIComponent(orderCode)}`));

  return parseJson<OrderTrackingOrder>(response);
}

export async function updateOrderStatus(
  orderCode: string,
  status: OrderStatus,
): Promise<OrderTrackingOrder> {
  const response = await fetch(apiUrl(`/orders/${encodeURIComponent(orderCode)}/status`), {
    method: "PATCH",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status }),
  });

  return parseJson<OrderTrackingOrder>(response);
}

export async function updateOrderItemStatus(
  orderCode: string,
  orderItemId: string,
  status: OrderItemStatus,
): Promise<OrderTrackingOrder> {
  const response = await fetch(
    apiUrl(`/orders/${encodeURIComponent(orderCode)}/items/${encodeURIComponent(orderItemId)}/status`),
    {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    },
  );

  return parseJson<OrderTrackingOrder>(response);
}

export async function confirmOrderPayment(orderCode: string): Promise<unknown> {
  const response = await fetch(apiUrl(`/orders/${encodeURIComponent(orderCode)}/payment/confirm`), {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      note: "Confirmed from staff operations board.",
    }),
  });

  return parseJson<unknown>(response);
}
