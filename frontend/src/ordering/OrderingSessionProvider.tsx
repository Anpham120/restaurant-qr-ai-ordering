import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  clearCustomerSession,
  loadOrderContext,
  type CustomerOrderContext,
} from "../components/customer/customerMenuStorage";
import { validateDineInSession } from "../services/tableSessionService";
import { matchSessionCapability } from "./sessionCapabilityStore";

export type OrderingSessionState = "loading" | "ready" | "missing" | "invalid" | "expired" | "error";

type OrderingSessionValue = {
  context: Required<CustomerOrderContext> | null;
  refresh: () => Promise<void>;
  state: OrderingSessionState;
};

type ActiveOrderingSessionValue = Omit<OrderingSessionValue, "context"> & {
  context: Required<CustomerOrderContext>;
};

const OrderingSessionContext = createContext<OrderingSessionValue | null>(null);

export function OrderingSessionProvider({ children, sessionId }: { children: ReactNode; sessionId: string }) {
  const [context, setContext] = useState<Required<CustomerOrderContext> | null>(null);
  const [state, setState] = useState<OrderingSessionState>("loading");

  const refresh = useCallback(async () => {
    const stored = loadOrderContext();
    const capabilityMatch = matchSessionCapability(stored, sessionId);
    if (capabilityMatch === "missing") {
      setContext(null);
      setState("missing");
      return;
    }
    if (capabilityMatch === "mismatch") {
      setContext(null);
      setState("invalid");
      return;
    }

    const activeCapability = stored as Required<CustomerOrderContext>;

    setState("loading");
    const validation = await validateDineInSession(
      activeCapability.sessionId,
      activeCapability.sessionToken,
      activeCapability.tableCode,
    );

    if (validation.status === "open") {
      setContext(activeCapability);
      setState("ready");
      return;
    }

    if (validation.status === "expired") {
      clearCustomerSession();
      setContext(null);
      setState("expired");
      return;
    }

    setContext(null);
    setState(validation.status === "error" ? "error" : "invalid");
  }, [sessionId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<OrderingSessionValue>(() => ({ context, refresh, state }), [context, refresh, state]);

  return (
    <OrderingSessionContext.Provider value={value}>
      {children}
    </OrderingSessionContext.Provider>
  );
}

export function useOrderingSession(): ActiveOrderingSessionValue {
  const value = useContext(OrderingSessionContext);
  if (!value || value.state !== "ready" || !value.context) {
    throw new Error("Ordering session is not ready.");
  }
  return value as ActiveOrderingSessionValue;
}

export function useOrderingSessionBoundary(): OrderingSessionValue {
  const value = useContext(OrderingSessionContext);
  if (!value) {
    throw new Error("Ordering session provider is missing.");
  }
  return value;
}
