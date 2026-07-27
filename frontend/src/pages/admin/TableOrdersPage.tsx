import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "@cmc/auth";
import { Armchair, ArrowLeft, ClipboardList } from "lucide-react";
import { AdminOrderManager } from "../../components/admin/AdminOrderManager";
import { OpsConnectionBadge } from "../../components/operations/OpsConnectionBadge";
import { buildCounterPaymentsLink, normalizeTableCode } from "../../components/operations/opsDeepLinkUtils";
import { useOpsConnectionStatus } from "../../components/operations/OpsRealtimeProvider";
import "../../components/operations/operations.css";

export function TableOrdersPage() {
  const { tableCode: rawTableCode } = useParams<{ tableCode: string }>();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const connectionStatus = useOpsConnectionStatus();
  const tableCode = normalizeTableCode(rawTableCode);

  if (!tableCode) {
    return <Navigate replace to="/tables?tab=sessions" />;
  }

  const displayName = searchParams.get("name")?.trim() || `Bàn ${tableCode}`;
  const backHref = `/tables?tab=sessions&table=${encodeURIComponent(tableCode)}`;
  const isCounter = user?.role === "CounterStaff" || user?.role === "Staff";

  return (
    <div className="ops-page">
      <header className="ops-page-header table-orders-header">
        <div className="table-orders-header-main">
          <Link className="table-orders-back" to={backHref}>
            <ArrowLeft aria-hidden="true" size={18} />
            Sơ đồ bàn
          </Link>
          <div className="table-orders-title-block">
            <p className="table-orders-kicker">
              <Armchair aria-hidden="true" size={16} />
              Bàn {tableCode}
            </p>
            <h1>{displayName}</h1>
            <p>
              Đơn gọi món và trạng thái xử lý chỉ của bàn này — tách khỏi màn đơn hàng tổng.
            </p>
          </div>
        </div>
        <div className="table-orders-header-actions">
          <OpsConnectionBadge status={connectionStatus} />
          {isCounter ? (
            <Link className="ops-btn ops-btn--primary ops-btn--sm" to={buildCounterPaymentsLink(tableCode)}>
              Quầy thu ngân
            </Link>
          ) : null}
          <Link className="ops-btn ops-btn--ghost ops-btn--sm" to="/orders?tab=table">
            <ClipboardList aria-hidden="true" size={15} />
            Đơn hàng tổng
          </Link>
        </div>
      </header>

      <AdminOrderManager embedded scopedTableCode={tableCode} />
    </div>
  );
}
