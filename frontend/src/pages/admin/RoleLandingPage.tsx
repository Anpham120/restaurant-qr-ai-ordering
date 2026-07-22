import { useAuth } from "@cmc/auth";
import { Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { AdminCommandCenter } from "../../components/admin/AdminCommandCenter";
import { hasPendingCounterPayments } from "../../services/opsSummaryService";

export function RoleLandingPage() {
  const { user, loading } = useAuth();
  const [counterTarget, setCounterTarget] = useState<string | null>(null);
  const [checkingCounter, setCheckingCounter] = useState(false);

  useEffect(() => {
    if (!user || (user.role !== "CounterStaff" && user.role !== "Staff")) return;
    setCheckingCounter(true);
    void hasPendingCounterPayments()
      .then((hasPending) => setCounterTarget(hasPending ? "/counter?tab=payments" : "/counter?tab=shift"))
      .catch(() => setCounterTarget("/counter"))
      .finally(() => setCheckingCounter(false));
  }, [user]);

  if (loading || checkingCounter) {
    return <div className="cmc-state" role="status">Đang xác minh phiên đăng nhập...</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "Kitchen") return <Navigate to="/kitchen/board" replace />;
  if (user.role === "CounterStaff" || user.role === "Staff") {
    return <Navigate to={counterTarget ?? "/counter"} replace />;
  }
  if (user.role === "Admin") return <AdminCommandCenter />;
  return <Navigate to="/login" replace />;
}
