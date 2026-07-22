import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { OpsNavBadges } from "../../services/opsSummaryService";
import { fetchOpsNavBadges } from "../../services/opsSummaryService";
import { subscribeOrderRealtime } from "../../services/realtimeOrderService";

type OpsNavBadgesContextValue = {
  badges: OpsNavBadges;
  refreshBadges: () => Promise<void>;
};

const DEFAULT_BADGES: OpsNavBadges = { orders: 0, counter: 0, tables: 0, kitchen: 0 };

const OpsNavBadgesContext = createContext<OpsNavBadgesContextValue>({
  badges: DEFAULT_BADGES,
  refreshBadges: async () => {},
});

export function OpsNavBadgesProvider({ children }: { children: ReactNode }) {
  const [badges, setBadges] = useState<OpsNavBadges>(DEFAULT_BADGES);

  const refreshBadges = useCallback(async () => {
    if (typeof document !== "undefined" && document.visibilityState !== "visible") {
      return;
    }
    try {
      setBadges(await fetchOpsNavBadges());
    } catch {
      /* keep previous badges */
    }
  }, []);

  useEffect(() => {
    void refreshBadges();
    const interval = window.setInterval(() => void refreshBadges(), 20_000);
    const unsubscribe = subscribeOrderRealtime(() => void refreshBadges());
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        void refreshBadges();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.clearInterval(interval);
      unsubscribe();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refreshBadges]);

  const value = useMemo(() => ({ badges, refreshBadges }), [badges, refreshBadges]);
  return <OpsNavBadgesContext.Provider value={value}>{children}</OpsNavBadgesContext.Provider>;
}

export function useOpsNavBadges() {
  return useContext(OpsNavBadgesContext);
}
