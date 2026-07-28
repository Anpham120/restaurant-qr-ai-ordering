import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "@cmc/auth";
import { subscribeOrderRealtime } from "../../services/realtimeOrderService";
import type { OrderRealtimeEvent } from "../../types";
import { useOpsAssistance } from "./OpsAssistanceProvider";
import { useOpsNavBadges } from "./OpsNavBadgesProvider";
import {
  buildAssistanceToastHref,
  buildOrderCreatedToastHref,
  buildPaymentRequestedToastHref,
  resolveOpsToastHref,
} from "./opsToastRouting";
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
  const { user } = useAuth();
  const { refreshBadges } = useOpsNavBadges();
  const { recordAssistance } = useOpsAssistance();
  const role = user?.role;

  const pushToast = useCallback((message: string, href?: string) => {
    const safeHref = resolveOpsToastHref(role, href);
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((current) => [...current.slice(-2), { id, message, href: safeHref }]);
    // #region agent log
    fetch("http://127.0.0.1:7639/ingest/45c610dd-1025-4f92-a068-a057f791be7f", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "613762" },
      body: JSON.stringify({
        sessionId: "613762",
        hypothesisId: "A",
        location: "OpsToastProvider.tsx:pushToast",
        message: "toast queued",
        data: { role, hasHref: Boolean(safeHref), droppedHref: Boolean(href && !safeHref) },
        timestamp: Date.now(),
        runId: "ops-realtime",
      }),
    }).catch(() => {});
    // #endregion
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5000);
  }, [role]);

  useEffect(() => {
    const unsubscribe = subscribeOrderRealtime((event) => {
      try {
        const label = TOAST_LABELS[event.event];
        if (!label) return;
        // #region agent log
        fetch("http://127.0.0.1:7639/ingest/45c610dd-1025-4f92-a068-a057f791be7f", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "613762" },
          body: JSON.stringify({
            sessionId: "613762",
            hypothesisId: "B",
            location: "OpsToastProvider.tsx:subscribe",
            message: "realtime toast event",
            data: { event: event.event, role },
            timestamp: Date.now(),
            runId: "ops-realtime",
          }),
        }).catch(() => {});
        // #endregion
        if (role !== "Kitchen") {
          void refreshBadges();
        }
        if (event.event === "payment.requested") {
          pushToast(label, buildPaymentRequestedToastHref(role, event.payload.tableCode));
          return;
        }
        if (event.event === "order.created") {
          pushToast(label, buildOrderCreatedToastHref(role, event.payload.tableCode));
          return;
        }
        if (event.event === "assistance.requested") {
          const { tableCode, tableSessionId, note, requestedAt } = event.payload;
          recordAssistance({ tableCode, tableSessionId, note, requestedAt });
          pushToast(
            `Bàn ${tableCode} · yêu cầu gọi nhân viên`,
            buildAssistanceToastHref(role),
          );
          return;
        }
        pushToast(label);
      } catch (error) {
        // #region agent log
        fetch("http://127.0.0.1:7639/ingest/45c610dd-1025-4f92-a068-a057f791be7f", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "613762" },
          body: JSON.stringify({
            sessionId: "613762",
            hypothesisId: "C",
            location: "OpsToastProvider.tsx:subscribe catch",
            message: "toast handler error",
            data: { detail: error instanceof Error ? error.message : "unknown" },
            timestamp: Date.now(),
            runId: "ops-realtime",
          }),
        }).catch(() => {});
        // #endregion
      }
    });
    return () => {
      unsubscribe();
    };
  }, [pushToast, recordAssistance, refreshBadges, role]);

  const value = useMemo(() => ({ pushToast }), [pushToast]);

  return (
    <OpsToastContext.Provider value={value}>
      {children}
      <div className="ops-toast-stack" aria-live="polite">
        {toasts.map((toast) => (
          toast.href ? (
            <a key={toast.id} className="ops-toast" href={toast.href}>
              {toast.message}
            </a>
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
