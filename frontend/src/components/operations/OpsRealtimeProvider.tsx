import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "@cmc/auth";
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
  const { user, loading } = useAuth();
  const [connectionStatus, setConnectionStatus] = useState<RealtimeConnectionStatus>("disconnected");

  useEffect(() => {
    if (loading) return;

    const unsubscribe = subscribeRealtimeConnection(setConnectionStatus);

    const syncHub = async () => {
      await disconnectOrderRealtime();
      if (!user) {
        setConnectionStatus("disconnected");
        return;
      }
      try {
        await connectOrderRealtime();
      } catch {
        setConnectionStatus("error");
      }
    };

    void syncHub();

    return () => {
      unsubscribe();
      void disconnectOrderRealtime();
    };
  }, [loading, user?.userId]);

  const value = useMemo(() => ({ connectionStatus }), [connectionStatus]);
  return <OpsRealtimeContext.Provider value={value}>{children}</OpsRealtimeContext.Provider>;
}

export function useOpsConnectionStatus() {
  const value = useContext(OpsRealtimeContext);
  return value?.connectionStatus ?? "disconnected";
}
