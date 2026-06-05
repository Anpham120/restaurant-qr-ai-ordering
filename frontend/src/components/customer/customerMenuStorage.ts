import type { MenuCart } from "../../types";

const CART_KEY = "cmc-restaurant-menu-cart";

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
}

