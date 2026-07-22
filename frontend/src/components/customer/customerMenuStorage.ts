import type { MenuCart } from "../../types";
import {
  browserSessionCapabilityStore,
  type SessionCapability,
} from "../../ordering/sessionCapabilityStore";
import { cartApi, cartResponseToMenuCart } from "../../services/cartService";

const CART_KEY = "cmc-restaurant-menu-cart";
const CART_MIGRATION_KEY = "cmc-cart-server-synced";
/** Bumps on each cart mutation so stale server syncs cannot overwrite in-flight adds. */
let cartSyncGeneration = 0;

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

function readStoredCartRaw(): StoredSessionCart | null {
  try {
    const rawCart = window.localStorage.getItem(CART_KEY);
    if (!rawCart) {
      return null;
    }

    const stored = JSON.parse(rawCart) as Partial<StoredSessionCart>;
    if (!stored.sessionId || !stored.items) {
      return null;
    }

    return stored as StoredSessionCart;
  } catch {
    return null;
  }
}

function writeStoredCart(sessionId: string, items: MenuCart) {
  const stored: StoredSessionCart = { sessionId, items };
  window.localStorage.setItem(CART_KEY, JSON.stringify(stored));
  notifyCartUpdated();
}

export function loadMenuCart(): MenuCart {
  try {
    const context = loadOrderContext();
    if (!context.sessionId || !context.sessionToken) {
      return {};
    }

    const stored = readStoredCartRaw();
    if (stored?.sessionId !== context.sessionId || !stored.items) {
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

  writeStoredCart(context.sessionId, cart);
}

export function clearMenuCart() {
  window.localStorage.removeItem(CART_KEY);
  notifyCartUpdated();

  const context = loadOrderContext();
  if (context.sessionId && context.sessionToken) {
    void cartApi.clearCart(context.sessionId).catch(() => undefined);
  }
}

export async function syncCartFromServer(options?: {
  expectedGeneration?: number;
  force?: boolean;
}): Promise<MenuCart> {
  const context = loadOrderContext();
  if (!context.sessionId || !context.sessionToken) {
    return {};
  }

  const cart = await cartApi.getCart(context.sessionId);
  const menuCart = cartResponseToMenuCart(cart);
  if (
    !options?.force
    && options?.expectedGeneration !== undefined
    && options.expectedGeneration !== cartSyncGeneration
  ) {
    return loadMenuCart();
  }

  writeStoredCart(context.sessionId, menuCart);
  return menuCart;
}

async function migrateLocalCartToServerIfNeeded(): Promise<void> {
  const context = loadOrderContext();
  if (!context.sessionId || !context.sessionToken) {
    return;
  }

  const migratedForSession = typeof window !== "undefined"
    && window.sessionStorage.getItem(CART_MIGRATION_KEY) === context.sessionId;
  if (migratedForSession) {
    return;
  }

  const localCart = loadMenuCart();
  const localHasItems = Object.values(localCart).some((quantity) => quantity > 0);
  if (!localHasItems) {
    window.sessionStorage.setItem(CART_MIGRATION_KEY, context.sessionId);
    return;
  }

  const serverCart = await cartApi.getCart(context.sessionId);
  const serverMenuCart = cartResponseToMenuCart(serverCart);
  const serverEmpty = Object.keys(serverMenuCart).length === 0;

  if (serverEmpty) {
    await Promise.all(
      Object.entries(localCart)
        .filter(([, quantity]) => quantity > 0)
        .map(([menuItemId, quantity]) =>
          cartApi.updateItem(context.sessionId!, { menuItemId, delta: quantity }),
        ),
    );
  }

  window.sessionStorage.setItem(CART_MIGRATION_KEY, context.sessionId);
}

export async function reconcileCartOnLoad(): Promise<MenuCart> {
  const context = loadOrderContext();
  if (!context.sessionId || !context.sessionToken) {
    return {};
  }

  const generationAtStart = cartSyncGeneration;

  try {
    await migrateLocalCartToServerIfNeeded();
    return await syncCartFromServer({ expectedGeneration: generationAtStart });
  } catch {
    return loadMenuCart();
  }
}

export async function applyCartDelta(
  menuItemId: string,
  delta: number,
  note?: string,
): Promise<MenuCart> {
  const mutationGeneration = ++cartSyncGeneration;
  const context = loadOrderContext();
  if (!context.sessionId || !context.sessionToken) {
    throw new Error("Phiên bàn chưa sẵn sàng.");
  }

  const current = loadMenuCart();
  const nextQuantity = Math.max(0, (current[menuItemId] ?? 0) + delta);
  const optimistic = { ...current };
  if (nextQuantity === 0) {
    delete optimistic[menuItemId];
  } else {
    optimistic[menuItemId] = nextQuantity;
  }
  writeStoredCart(context.sessionId, optimistic);

  try {
    const cart = await cartApi.updateItem(context.sessionId, { menuItemId, delta, note });
    const menuCart = cartResponseToMenuCart(cart);
    if (mutationGeneration !== cartSyncGeneration) {
      return loadMenuCart();
    }
    writeStoredCart(context.sessionId, menuCart);
    return menuCart;
  } catch (error) {
    try {
      await syncCartFromServer({ force: true });
    } catch {
      if (mutationGeneration === cartSyncGeneration) {
        writeStoredCart(context.sessionId, current);
      }
    }
    throw error;
  }
}

export function loadOrderContext(): CustomerOrderContext {
  return browserSessionCapabilityStore.read();
}

export function saveOrderContext(context: SessionCapability) {
  const current = loadOrderContext();
  if (current.sessionId !== context.sessionId) {
    window.localStorage.removeItem(CART_KEY);
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(CART_MIGRATION_KEY);
    }
  }
  browserSessionCapabilityStore.write(context);
  notifyCartUpdated();
}

export function clearCustomerSession() {
  window.localStorage.removeItem(CART_KEY);
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(CART_MIGRATION_KEY);
  }
  browserSessionCapabilityStore.clear();
  notifyCartUpdated();
}
