import { useEffect } from "react";
import { Navigate, useParams, useSearchParams } from "react-router-dom";
import { useI18n } from "@cmc/i18n";
import { loadOrderContext } from "../components/customer/customerMenuStorage";
import { openDineInSession } from "../services/tableSessionService";
import { getSessionResumeDestination } from "./sessionResumeState";

export function SessionSmartIndexRedirect() {
  const { t } = useI18n();
  const { sessionId } = useParams();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    if (!sessionId) return;
    const stored = loadOrderContext();
    const qrToken = searchParams.get("qr") ?? stored.qrToken;
    if (!qrToken || stored.sessionId !== sessionId || !stored.tableCode) {
      return;
    }

    let active = true;
    void openDineInSession(qrToken, stored.tableCode).then((result) => {
      if (!active || result.status !== "open") return;
      const destination = getSessionResumeDestination(sessionId, result.session.resumeState, qrToken);
      if (destination !== `/table-session/${sessionId}/menu`) {
        window.location.replace(destination);
      }
    });
    return () => {
      active = false;
    };
  }, [searchParams, sessionId]);

  if (!sessionId) {
    return <Navigate replace to="/" />;
  }

  const stored = loadOrderContext();
  const qrToken = searchParams.get("qr") ?? stored.qrToken;
  if (qrToken && stored.sessionId === sessionId && stored.sessionToken) {
    return (
      <main className="ordering-state" aria-live="polite">
        <p>{t("Đang mở đúng bước theo trạng thái bàn…")}</p>
      </main>
    );
  }

  return <Navigate replace to={`menu${searchParams.toString() ? `?${searchParams.toString()}` : ""}`} relative="path" />;
}
