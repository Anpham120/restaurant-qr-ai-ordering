import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  clearCustomerSession,
  loadOrderContext,
  type CustomerOrderContext,
} from "../components/customer/customerMenuStorage";
import { validateDineInSession } from "../services/tableSessionService";

export type OrderingSessionState = "loading" | "ready" | "invalid" | "expired" | "error";

type OrderingSessionValue = {
  context: Required<CustomerOrderContext> | null;
  refresh: () => Promise<void>;
  state: OrderingSessionState;
};

type ActiveOrderingSessionValue = Omit<OrderingSessionValue, "context"> & {
  context: Required<CustomerOrderContext>;
};

const OrderingSessionContext = createContext<OrderingSessionValue | null>(null);

function hasMatchingCapability(context: CustomerOrderContext, sessionId: string): context is Required<CustomerOrderContext> {
  return Boolean(
    context.sessionId === sessionId &&
      context.sessionToken &&
      context.tableCode &&
      context.qrToken,
  );
}

export function OrderingSessionProvider({ children, sessionId }: { children: ReactNode; sessionId: string }) {
  const [context, setContext] = useState<Required<CustomerOrderContext> | null>(null);
  const [state, setState] = useState<OrderingSessionState>("loading");

  const refresh = useCallback(async () => {
    const stored = loadOrderContext();
    if (!hasMatchingCapability(stored, sessionId)) {
      setContext(null);
      setState("invalid");
      return;
    }

    setState("loading");
    const validation = await validateDineInSession(
      stored.sessionId,
      stored.sessionToken,
      stored.tableCode,
    );

    if (validation.status === "open") {
      setContext(stored);
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
