import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { subscribeOrderRealtime } from "../../services/realtimeOrderService";
import type { OrderRealtimeEvent } from "../../types";
import { useOpsAssistance } from "./OpsAssistanceProvider";
import { useOpsNavBadges } from "./OpsNavBadgesProvider";
import { buildCounterPaymentsLink, buildOrdersKanbanLink } from "./opsDeepLinkUtils";
import "./operations.css";

type OpsToast = {
  id: string;
  message: string;
  href?: string;
};

type OpsToastContextValue = {
  pushToast: (message: string, href?: string) => void;
};

const OpsToastContext = createContext<OpsToastContextValue>({
  pushToast: () => {},
});

const TOAST_LABELS: Partial<Record<OrderRealtimeEvent["event"], string>> = {
  "order.created": "Có đơn mới",
  "payment.requested": "Yêu cầu thanh toán mới",
  "assistance.requested": "Khách cần hỗ trợ",
  "order.statusChanged": "Trạng thái đơn thay đổi",
};

export function OpsToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<OpsToast[]>([]);
  const { refreshBadges } = useOpsNavBadges();
  const { recordAssistance } = useOpsAssistance();

  const pushToast = useCallback((message: string, href?: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((current) => [...current.slice(-2), { id, message, href }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeOrderRealtime((event) => {
      const label = TOAST_LABELS[event.event];
      if (!label) return;
      void refreshBadges();
      if (event.event === "payment.requested") {
        pushToast(label, buildCounterPaymentsLink(event.payload.tableCode));
        return;
      }
      if (event.event === "order.created") {
        pushToast(label, buildOrdersKanbanLink(event.payload.tableCode));
        return;
      }
      if (event.event === "assistance.requested") {
        const { tableCode, tableSessionId, note, requestedAt } = event.payload;
        recordAssistance({ tableCode, tableSessionId, note, requestedAt });
        pushToast(
          `Khách bàn ${tableCode} cần hỗ trợ`,
          `/tables?tab=sessions&table=${encodeURIComponent(tableCode)}`,
        );
        return;
      }
      pushToast(label);
    });
    return () => {
      unsubscribe();
    };
  }, [pushToast, recordAssistance, refreshBadges]);

  const value = useMemo(() => ({ pushToast }), [pushToast]);

  return (
    <OpsToastContext.Provider value={value}>
      {children}
      <div className="ops-toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          toast.href ? (
            <Link key={toast.id} className="ops-toast" to={toast.href}>
              {toast.message}
            </Link>
          ) : (
            <div key={toast.id} className="ops-toast">{toast.message}</div>
          )
        ))}
      </div>
    </OpsToastContext.Provider>
  );
}

export function useOpsToast() {
  return useContext(OpsToastContext);
}
