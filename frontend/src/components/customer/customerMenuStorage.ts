import type { MenuCart, TableCode } from "../../types";

const CART_KEY = "cmc-restaurant-menu-cart";
const ORDER_CONTEXT_KEY = "cmc-restaurant-order-context";

/** Custom event bắn ra mỗi khi giỏ hàng/phiên bàn đổi trong cùng tab,
 * để widget giỏ hàng nổi (mounted ở layout) đồng bộ ngay lập tức. */
export const CART_UPDATED_EVENT = "cmc:cart-updated";

function notifyCartUpdated() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(CART_UPDATED_EVENT));
  }
}

export type CustomerOrderContext = {
  tableCode?: TableCode;
  sessionId?: string;
  sessionToken?: string;
  qrToken?: string;
};

type StoredSessionCart = {
  sessionId: string;
  items: MenuCart;
};

export function loadMenuCart(): MenuCart {
  try {
    const context = loadOrderContext();
    if (!context.sessionId || !context.sessionToken) {
      return {};
    }

    const rawCart = window.localStorage.getItem(CART_KEY);
    if (!rawCart) {
      return {};
    }

    const stored = JSON.parse(rawCart) as Partial<StoredSessionCart>;
    if (stored.sessionId !== context.sessionId || !stored.items) {
      return {};
    }

    return stored.items;
  } catch {
    return {};
  }
}

export function saveMenuCart(cart: MenuCart) {
  const context = loadOrderContext();
  if (!context.sessionId || !context.sessionToken) {
    window.localStorage.removeItem(CART_KEY);
    notifyCartUpdated();
    return;
  }

  const stored: StoredSessionCart = { sessionId: context.sessionId, items: cart };
  window.localStorage.setItem(CART_KEY, JSON.stringify(stored));
  notifyCartUpdated();
}

export function clearMenuCart() {
  window.localStorage.removeItem(CART_KEY);
  notifyCartUpdated();
}

export function loadOrderContext(): CustomerOrderContext {
  try {
    const rawContext = window.localStorage.getItem(ORDER_CONTEXT_KEY);
    return rawContext ? (JSON.parse(rawContext) as CustomerOrderContext) : {};
  } catch {
    return {};
  }
}

export function saveOrderContext(context: CustomerOrderContext) {
  const current = loadOrderContext();
  if (current.sessionId !== context.sessionId) {
    window.localStorage.removeItem(CART_KEY);
  }
  window.localStorage.setItem(ORDER_CONTEXT_KEY, JSON.stringify(context));
  notifyCartUpdated();
}

export function clearCustomerSession() {
  window.localStorage.removeItem(CART_KEY);
  window.localStorage.removeItem(ORDER_CONTEXT_KEY);
  notifyCartUpdated();
}
