import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { loadOrderContext } from "../components/customer/customerMenuStorage";
import { openDineInSession } from "../services/tableSessionService";
import { getSessionResumeDestination } from "./sessionResumeState";

export function SessionSmartIndexRedirect() {
  const { sessionId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [resolving, setResolving] = useState(true);
  const [fallbackPath, setFallbackPath] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setResolving(false);
      return;
    }

    const stored = loadOrderContext();
    const qrToken = searchParams.get("qr") ?? stored.qrToken;
    if (!qrToken || stored.sessionId !== sessionId || !stored.tableCode) {
      setFallbackPath(`menu${searchParams.toString() ? `?${searchParams.toString()}` : ""}`);
      setResolving(false);
      return;
    }

    let active = true;
    void openDineInSession(qrToken, stored.tableCode)
      .then((result) => {
        if (!active) return;
        if (result.status === "open") {
          navigate(getSessionResumeDestination(sessionId, result.session.resumeState, qrToken), { replace: true });
          return;
        }
        setFallbackPath(`menu${searchParams.toString() ? `?${searchParams.toString()}` : ""}`);
        setResolving(false);
      })
      .catch(() => {
        if (!active) return;
        setFallbackPath(`menu${searchParams.toString() ? `?${searchParams.toString()}` : ""}`);
        setResolving(false);
      });

    return () => {
      active = false;
    };
  }, [navigate, searchParams, sessionId]);

  if (!sessionId) {
    return <Navigate replace to="/" />;
  }

  if (resolving) {
    return (
      <main className="cmc-redirect-page" role="status">
        <h1>Đang mở phiên bàn...</h1>
      </main>
    );
  }

  if (fallbackPath) {
    return <Navigate replace to={fallbackPath} relative="path" />;
  }

  return (
    <main className="cmc-redirect-page" role="status">
      <h1>Đang chuyển hướng...</h1>
    </main>
  );
}
