import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  applyCartDelta,
  loadMenuCart,
  reconcileCartOnLoad,
  saveOrderContext,
} from "./customerMenuStorage";
import { cartApi } from "../../services/cartService";

function createMemoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    removeItem: (key: string) => { values.delete(key); },
    setItem: (key: string, value: string) => { values.set(key, value); },
  };
}

vi.mock("../../services/cartService", () => ({
  cartApi: {
    getCart: vi.fn(),
    updateItem: vi.fn(),
    clearCart: vi.fn(),
  },
  cartResponseToMenuCart: (cart: { items: Array<{ menuItemId: string; quantity: number }> }) =>
    cart.items.reduce<Record<string, number>>((result, item) => {
      if (item.quantity > 0) {
        result[item.menuItemId] = item.quantity;
      }
      return result;
    }, {}),
}));

const emptyCartResponse = {
  tableSessionId: "session-1",
  items: [],
  itemCount: 0,
  subtotal: 0,
  updatedAt: new Date().toISOString(),
};

const oneItemCartResponse = {
  tableSessionId: "session-1",
  items: [
    {
      id: "cart-1",
      menuItemId: "m_004",
      name: "Test dish",
      description: "",
      price: 55000,
      categoryId: "cat_appetizer",
      categoryName: "Khai vị",
      imageUrl: null,
      isAvailable: true,
      quantity: 1,
      note: null,
      lineTotal: 55000,
      updatedAt: new Date().toISOString(),
    },
  ],
  itemCount: 1,
  subtotal: 55000,
  updatedAt: new Date().toISOString(),
};

describe("customerMenuStorage cart sync generation", () => {
  beforeEach(() => {
    vi.stubGlobal("window", {
      sessionStorage: createMemoryStorage(),
      localStorage: createMemoryStorage(),
      dispatchEvent: vi.fn(),
    });
    saveOrderContext({
      qrToken: "cmc-table-t01-qr",
      sessionId: "session-1",
      sessionToken: "token-1",
      tableCode: "T01",
    });
    vi.mocked(cartApi.getCart).mockReset();
    vi.mocked(cartApi.updateItem).mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("does not let a stale reconcile sync wipe an in-flight add", async () => {
    let resolveGetCart: ((value: typeof emptyCartResponse) => void) | undefined;
    const delayedGetCart = new Promise<typeof emptyCartResponse>((resolve) => {
      resolveGetCart = resolve;
    });

    vi.mocked(cartApi.getCart).mockReturnValue(delayedGetCart);
    vi.mocked(cartApi.updateItem).mockResolvedValue(oneItemCartResponse);

    const reconcilePromise = reconcileCartOnLoad();
    await Promise.resolve();

    await applyCartDelta("m_004", 1);
    expect(loadMenuCart()).toEqual({ m_004: 1 });

    resolveGetCart?.(emptyCartResponse);
    const reconciledCart = await reconcilePromise;

    expect(reconciledCart).toEqual({ m_004: 1 });
    expect(loadMenuCart()).toEqual({ m_004: 1 });
  });
});
