import { getApiBaseUrl } from "./apiClient";
import { browserSessionCapabilityStore } from "../ordering/sessionCapabilityStore";
import type { MenuCart } from "../types";

export type CartItemResponse = {
  id: string;
  menuItemId: string;
  name: string;
  description: string;
  price: number;
  categoryId: string;
  categoryName: string;
  imageUrl: string | null;
  isAvailable: boolean;
  quantity: number;
  note: string | null;
  lineTotal: number;
  updatedAt: string;
};

export type CartResponse = {
  tableSessionId: string;
  items: CartItemResponse[];
  itemCount: number;
  subtotal: number;
  updatedAt: string;
};

export type UpdateCartItemRequest = {
  menuItemId: string;
  delta: number;
  note?: string;
};

type CartApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class CartApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

function getSessionAuth(tableSessionId: string) {
  const capability = browserSessionCapabilityStore.read();
  if (capability.sessionId !== tableSessionId || !capability.sessionToken) {
    throw new CartApiError(401, "TABLE_SESSION_TOKEN_MISSING", "Phiên bàn chưa sẵn sàng.");
  }

  return capability.sessionToken;
}

async function requestJson<TResponse>(
  path: string,
  method: "GET" | "POST" | "DELETE",
  body?: unknown,
  tableSessionId?: string,
): Promise<TResponse> {
  const sessionToken = tableSessionId ? getSessionAuth(tableSessionId) : undefined;

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(sessionToken ? { "X-Table-Session-Token": sessionToken } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let errorBody: CartApiErrorBody | null = null;
    try {
      errorBody = await response.json() as CartApiErrorBody;
    } catch {
      errorBody = null;
    }

    throw new CartApiError(
      response.status,
      errorBody?.error?.code ?? `HTTP_${response.status}`,
      errorBody?.error?.message ?? "Không thể cập nhật giỏ hàng.",
    );
  }

  return (await response.json()) as TResponse;
}

export function cartResponseToMenuCart(cart: CartResponse): MenuCart {
  return cart.items.reduce<MenuCart>((result, item) => {
    if (item.quantity > 0) {
      result[item.menuItemId] = item.quantity;
    }
    return result;
  }, {});
}

export const cartApi = {
  async getCart(tableSessionId: string): Promise<CartResponse> {
    return requestJson<CartResponse>(
      `/table-sessions/${encodeURIComponent(tableSessionId)}/cart`,
      "GET",
      undefined,
      tableSessionId,
    );
  },

  async updateItem(
    tableSessionId: string,
    request: UpdateCartItemRequest,
  ): Promise<CartResponse> {
    return requestJson<CartResponse>(
      `/table-sessions/${encodeURIComponent(tableSessionId)}/cart/items`,
      "POST",
      request,
      tableSessionId,
    );
  },

  async clearCart(tableSessionId: string): Promise<CartResponse> {
    return requestJson<CartResponse>(
      `/table-sessions/${encodeURIComponent(tableSessionId)}/cart`,
      "DELETE",
      undefined,
      tableSessionId,
    );
  },
};
