import type { MenuCart } from "../../types";
import {
  browserSessionCapabilityStore,
  type SessionCapability,
} from "../../ordering/sessionCapabilityStore";

const CART_KEY = "cmc-restaurant-menu-cart";

/** Custom event bắn ra mỗi khi giỏ hàng/phiên bàn đổi trong cùng tab,
 * để widget giỏ hàng nổi (mounted ở layout) đồng bộ ngay lập tức. */
export const CART_UPDATED_EVENT = "cmc:cart-updated";

function notifyCartUpdated() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(CART_UPDATED_EVENT));
  }
}

export type CustomerOrderContext = Partial<SessionCapability>;

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
  return browserSessionCapabilityStore.read();
}

export function saveOrderContext(context: SessionCapability) {
  const current = loadOrderContext();
  if (current.sessionId !== context.sessionId) {
    window.localStorage.removeItem(CART_KEY);
  }
  browserSessionCapabilityStore.write(context);
  notifyCartUpdated();
}

export function clearCustomerSession() {
  window.localStorage.removeItem(CART_KEY);
  browserSessionCapabilityStore.clear();
  notifyCartUpdated();
}
