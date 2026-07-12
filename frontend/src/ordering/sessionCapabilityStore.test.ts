import { describe, expect, it } from "vitest";
import {
  LEGACY_ORDER_CONTEXT_KEY,
  SESSION_CAPABILITY_KEY,
  createSessionCapabilityStore,
  matchSessionCapability,
} from "./sessionCapabilityStore";

function createMemoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    removeItem: (key: string) => { values.delete(key); },
    setItem: (key: string, value: string) => { values.set(key, value); },
  };
}

const capability = {
  qrToken: "qr-token",
  sessionId: "session-123",
  sessionToken: "session-token",
  tableCode: "T01",
};

describe("session capability store", () => {
  it("classifies a direct session URL without capability as missing", () => {
    expect(matchSessionCapability({}, "session-123")).toBe("missing");
  });

  it("does not authorize a route for a different session", () => {
    expect(matchSessionCapability(capability, "session-other")).toBe("mismatch");
    expect(matchSessionCapability(capability, "session-123")).toBe("matching");
  });

  it("writes the capability only to tab-scoped storage", () => {
    const sessionStorage = createMemoryStorage();
    const legacyStorage = createMemoryStorage();
    const store = createSessionCapabilityStore(sessionStorage, legacyStorage);

    store.write(capability);

    expect(JSON.parse(sessionStorage.getItem(SESSION_CAPABILITY_KEY)!)).toEqual(capability);
    expect(legacyStorage.getItem(LEGACY_ORDER_CONTEXT_KEY)).toBeNull();
  });

  it("does not authorize a fresh tab from a persistent legacy capability", () => {
    const sessionStorage = createMemoryStorage();
    const legacyStorage = createMemoryStorage();
    legacyStorage.setItem(LEGACY_ORDER_CONTEXT_KEY, JSON.stringify(capability));
    const store = createSessionCapabilityStore(sessionStorage, legacyStorage);

    expect(store.read()).toEqual({});
    expect(sessionStorage.getItem(SESSION_CAPABILITY_KEY)).toBeNull();
    expect(legacyStorage.getItem(LEGACY_ORDER_CONTEXT_KEY)).toBeNull();
  });

  it("clears both current and legacy capability storage", () => {
    const sessionStorage = createMemoryStorage();
    const legacyStorage = createMemoryStorage();
    sessionStorage.setItem(SESSION_CAPABILITY_KEY, JSON.stringify(capability));
    legacyStorage.setItem(LEGACY_ORDER_CONTEXT_KEY, JSON.stringify(capability));
    const store = createSessionCapabilityStore(sessionStorage, legacyStorage);

    store.clear();

    expect(sessionStorage.getItem(SESSION_CAPABILITY_KEY)).toBeNull();
    expect(legacyStorage.getItem(LEGACY_ORDER_CONTEXT_KEY)).toBeNull();
  });
});
