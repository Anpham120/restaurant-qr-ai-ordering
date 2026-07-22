import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { RealtimeConnectionStatus } from "@cmc/shared-types";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeRealtimeConnection,
} from "../../services/realtimeOrderService";

type OpsRealtimeContextValue = {
  connectionStatus: RealtimeConnectionStatus;
};

export const OpsRealtimeContext = createContext<OpsRealtimeContextValue | null>(null);

export function OpsRealtimeProvider({ children }: { children: ReactNode }) {
  const [connectionStatus, setConnectionStatus] = useState<RealtimeConnectionStatus>("disconnected");

  useEffect(() => {
    const unsubscribe = subscribeRealtimeConnection(setConnectionStatus);
    void connectOrderRealtime().catch(() => setConnectionStatus("error"));
    return () => {
      unsubscribe();
      void disconnectOrderRealtime();
    };
  }, []);

  const value = useMemo(() => ({ connectionStatus }), [connectionStatus]);
  return <OpsRealtimeContext.Provider value={value}>{children}</OpsRealtimeContext.Provider>;
}

export function useOpsConnectionStatus() {
  const value = useContext(OpsRealtimeContext);
  return value?.connectionStatus ?? "disconnected";
}
