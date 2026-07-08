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
  qrToken?: string;
};

export function loadMenuCart(): MenuCart {
  try {
    const rawCart = window.localStorage.getItem(CART_KEY);
    return rawCart ? (JSON.parse(rawCart) as MenuCart) : {};
  } catch {
    return {};
  }
}

export function saveMenuCart(cart: MenuCart) {
  window.localStorage.setItem(CART_KEY, JSON.stringify(cart));
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
  window.localStorage.setItem(ORDER_CONTEXT_KEY, JSON.stringify(context));
  notifyCartUpdated();
}

