import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type OpsAssistanceAlert = {
  id: string;
  tableCode: string;
  tableSessionId: string | null;
  note: string | null;
  requestedAt: string;
};

type OpsAssistanceContextValue = {
  recentAssistance: OpsAssistanceAlert[];
  recordAssistance: (alert: Omit<OpsAssistanceAlert, "id">) => void;
};

const OpsAssistanceContext = createContext<OpsAssistanceContextValue>({
  recentAssistance: [],
  recordAssistance: () => {},
});

const MAX_ASSISTANCE_ITEMS = 5;

export function OpsAssistanceProvider({ children }: { children: ReactNode }) {
  const [recentAssistance, setRecentAssistance] = useState<OpsAssistanceAlert[]>([]);

  const recordAssistance = useCallback((alert: Omit<OpsAssistanceAlert, "id">) => {
    const id = `${alert.tableCode}-${alert.requestedAt}`;
    setRecentAssistance((current) => [
      { ...alert, id },
      ...current.filter((item) => item.id !== id),
    ].slice(0, MAX_ASSISTANCE_ITEMS));
  }, []);

  const value = useMemo(
    () => ({ recentAssistance, recordAssistance }),
    [recentAssistance, recordAssistance],
  );

  return (
    <OpsAssistanceContext.Provider value={value}>
      {children}
    </OpsAssistanceContext.Provider>
  );
}

export function useOpsAssistance() {
  return useContext(OpsAssistanceContext);
}
