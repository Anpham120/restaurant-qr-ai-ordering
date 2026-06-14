import type {
  ApiErrorBody,
  AuthUser,
  CreateOrderRequest,
  LoginRequest,
  LoginResponse,
  MenuResponse,
  Order,
  OrderItemStatus,
  OrderListResponse,
  OrderStatus,
  Payment,
  Table,
  TableSession,
  VietQrPayment,
} from "@cmc/shared-types";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) { super(message); }
}

export type ApiClientOptions = { baseUrl?: string; getAccessToken?: () => string | null };

export function createApiClient(options: ApiClientOptions = {}) {
  const baseUrl = (options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "https://localhost:7296/api").replace(/\/$/, "");
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (init.body) headers.set("Content-Type", "application/json");
    const token = options.getAccessToken?.();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
    if (!response.ok) {
      let body: ApiErrorBody | undefined;
      try { body = await response.json() as ApiErrorBody; } catch { body = undefined; }
      throw new ApiError(response.status, body?.error.code ?? `HTTP_${response.status}`, body?.error.message ?? response.statusText, body?.error.details);
    }
    return response.status === 204 ? undefined as T : response.json() as Promise<T>;
  }
  return {
    request,
    auth: {
      login: (payload: LoginRequest) => request<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
      me: () => request<AuthUser>("/auth/me"),
    },
    menu: { get: () => request<MenuResponse>("/menu") },
    tables: {
      get: (code: string) => request<Table>(`/tables/${encodeURIComponent(code)}`),
      openSession: (payload: { qrToken?: string | null; tableCode?: string | null; orderType?: "DineIn" | "Pickup" }) =>
        request<TableSession>("/table-sessions", { method: "POST", body: JSON.stringify(payload) }),
      getSession: (sessionId: string) => request<TableSession>(`/table-sessions/${encodeURIComponent(sessionId)}`),
      closeSession: (sessionId: string) =>
        request<TableSession>(`/table-sessions/${encodeURIComponent(sessionId)}/close`, { method: "POST" }),
    },
    orders: {
      create: (payload: CreateOrderRequest) => request<Order>("/orders", { method: "POST", body: JSON.stringify(payload) }),
      get: (code: string) => request<Order>(`/orders/${encodeURIComponent(code)}`),
      list: (filters: { status?: string; tableCode?: string; updatedSince?: string } = {}) => {
        const params = new URLSearchParams();
        if (filters.status) params.set("status", filters.status);
        if (filters.tableCode) params.set("tableCode", filters.tableCode);
        if (filters.updatedSince) params.set("updatedSince", filters.updatedSince);
        const query = params.toString();
        return request<OrderListResponse>(`/orders${query ? `?${query}` : ""}`);
      },
      updateStatus: (code: string, status: OrderStatus) => request<Order>(`/orders/${encodeURIComponent(code)}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
      updateItemStatus: (code: string, itemId: string, status: OrderItemStatus) => request<Order>(`/orders/${encodeURIComponent(code)}/items/${encodeURIComponent(itemId)}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    },
    payments: {
      get: (orderCode: string) => request<Payment>(`/orders/${encodeURIComponent(orderCode)}/payment`),
      generateVietQr: (orderCode: string) =>
        request<VietQrPayment>(`/orders/${encodeURIComponent(orderCode)}/payment/vietqr`, { method: "POST" }),
      confirm: (orderCode: string, payload: { providerTransactionId?: string | null; note?: string | null } = {}) =>
        request<Payment>(`/orders/${encodeURIComponent(orderCode)}/payment/confirm`, { method: "POST", body: JSON.stringify(payload) }),
      fail: (orderCode: string, payload: { note?: string | null } = {}) =>
        request<Payment>(`/orders/${encodeURIComponent(orderCode)}/payment/fail`, { method: "POST", body: JSON.stringify(payload) }),
    },
  };
}
