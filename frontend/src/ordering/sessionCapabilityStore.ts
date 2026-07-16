import type { TableCode } from "../types";

export const SESSION_CAPABILITY_KEY = "cmc-ordering-session-capability-v1";
export const LEGACY_ORDER_CONTEXT_KEY = "cmc-restaurant-order-context";

export type SessionCapability = {
  qrToken: string;
  sessionId: string;
  sessionToken: string;
  tableCode: TableCode;
};

type StorageLike = Pick<Storage, "getItem" | "removeItem" | "setItem">;

export type SessionCapabilityStore = {
  clear: () => void;
  read: () => Partial<SessionCapability>;
  write: (capability: SessionCapability) => void;
};

export type SessionCapabilityMatch = "matching" | "missing" | "mismatch";

export function matchSessionCapability(
  capability: Partial<SessionCapability>,
  routeSessionId: string,
): SessionCapabilityMatch {
  if (!capability.sessionId || !capability.sessionToken || !capability.tableCode || !capability.qrToken) {
    return "missing";
  }
  return capability.sessionId === routeSessionId ? "matching" : "mismatch";
}

function parseCapability(raw: string | null): SessionCapability | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as Partial<SessionCapability>;
    if (
      typeof value.qrToken !== "string" ||
      typeof value.sessionId !== "string" ||
      typeof value.sessionToken !== "string" ||
      typeof value.tableCode !== "string"
    ) {
      return null;
    }
    return value as SessionCapability;
  } catch {
    return null;
  }
}

export function createSessionCapabilityStore(
  tabStorage: StorageLike,
  legacyStorage?: StorageLike,
): SessionCapabilityStore {
  return {
    clear() {
      tabStorage.removeItem(SESSION_CAPABILITY_KEY);
      legacyStorage?.removeItem(LEGACY_ORDER_CONTEXT_KEY);
    },
    read() {
      const current = parseCapability(tabStorage.getItem(SESSION_CAPABILITY_KEY));
      if (current) return current;
      // A persistent legacy capability must never authorize a fresh tab.
      legacyStorage?.removeItem(LEGACY_ORDER_CONTEXT_KEY);
      return {};
    },
    write(capability) {
      tabStorage.setItem(SESSION_CAPABILITY_KEY, JSON.stringify(capability));
      legacyStorage?.removeItem(LEGACY_ORDER_CONTEXT_KEY);
    },
  };
}

export const browserSessionCapabilityStore: SessionCapabilityStore = {
  clear() {
    if (typeof window === "undefined") return;
    createSessionCapabilityStore(window.sessionStorage, window.localStorage).clear();
  },
  read() {
    if (typeof window === "undefined") return {};
    return createSessionCapabilityStore(window.sessionStorage, window.localStorage).read();
  },
  write(capability) {
    if (typeof window === "undefined") return;
    createSessionCapabilityStore(window.sessionStorage, window.localStorage).write(capability);
  },
};
