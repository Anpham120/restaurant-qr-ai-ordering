import { useContext, useEffect, useRef, useState } from "react";
import type { RealtimeConnectionStatus } from "@cmc/shared-types";
import type { OrderRealtimeEvent } from "../types";
import { OpsRealtimeContext } from "../components/operations/OpsRealtimeProvider";
import {
  connectOrderRealtime,
  disconnectOrderRealtime,
  subscribeOrderRealtime,
  subscribeRealtimeConnection,
} from "../services/realtimeOrderService";

type UseOpsRealtimeOptions = {
  refresh: () => void | Promise<void>;
  onEvent?: (event: OrderRealtimeEvent) => void;
  pollIntervalMs?: number;
  enabled?: boolean;
};

let activeConsumers = 0;

export function useOpsRealtime({
  refresh,
  onEvent,
  pollIntervalMs = 10_000,
  enabled = true,
}: UseOpsRealtimeOptions) {
  const appRealtime = useContext(OpsRealtimeContext);
  const [localStatus, setLocalStatus] = useState<RealtimeConnectionStatus>("disconnected");
  const connectionStatus = appRealtime?.connectionStatus ?? localStatus;
  const refreshRef = useRef(refresh);
  const onEventRef = useRef(onEvent);
  refreshRef.current = refresh;
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!enabled) return;

    const unsubscribeRealtime = subscribeOrderRealtime((event) => {
      onEventRef.current?.(event);
      void refreshRef.current();
    });

    if (appRealtime) {
      return () => {
        unsubscribeRealtime();
      };
    }

    activeConsumers += 1;
    const unsubscribeConnection = subscribeRealtimeConnection(setLocalStatus);
    void connectOrderRealtime().catch(() => setLocalStatus("error"));

    return () => {
      unsubscribeConnection();
      unsubscribeRealtime();
      activeConsumers -= 1;
      if (activeConsumers <= 0) {
        activeConsumers = 0;
        void disconnectOrderRealtime();
      }
    };
  }, [appRealtime, enabled]);

  useEffect(() => {
    if (!enabled || connectionStatus === "connected") return;
    const interval = window.setInterval(() => void refreshRef.current(), pollIntervalMs);
    return () => window.clearInterval(interval);
  }, [connectionStatus, pollIntervalMs, enabled]);

  return { connectionStatus };
}
