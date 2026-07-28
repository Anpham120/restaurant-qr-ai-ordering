import { Navigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@cmc/auth";
import { AdminOrderManager } from "../../components/admin/AdminOrderManager";
import { StaffOrderBoard } from "../../components/staff/StaffOrderBoard";
import { OpsHubShell } from "../../components/operations/OpsHubShell";
import { useOpsHubTab } from "../../components/operations/OpsHubTabs";
import { useOpsConnectionStatus } from "../../components/operations/OpsRealtimeProvider";
import { buildTableOrdersLink, normalizeTableCode } from "../../components/operations/opsDeepLinkUtils";
import "../../components/operations/operations.css";

const ORDER_TABS = [
  { id: "table", label: "Quản lý đơn", adminOnly: true },
  { id: "kanban", label: "Kanban vận hành", counterOnly: true },
];

export function OrdersHubPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const isAdmin = user?.role === "Admin";
  const tableFromQuery = normalizeTableCode(searchParams.get("table"));
  const { activeTab } = useOpsHubTab(ORDER_TABS, "tab", isAdmin, isAdmin ? "table" : "kanban");
  const connectionStatus = useOpsConnectionStatus();

  if (isAdmin && tableFromQuery) {
    const name = searchParams.get("name")?.trim();
    const suffix = name ? `?name=${encodeURIComponent(name)}` : "";
    return <Navigate replace to={`${buildTableOrdersLink(tableFromQuery)}${suffix}`} />;
  }

  return (
    <OpsHubShell
      title="Đơn hàng"
      description={isAdmin
        ? "Theo dõi, lọc và đối soát đơn — không cần thao tác kanban bếp/phục vụ."
        : "Theo dõi kanban realtime và xử lý đơn tại quầy."}
      tabs={ORDER_TABS}
      isAdmin={isAdmin}
      connectionStatus={connectionStatus}
      defaultTabId={isAdmin ? "table" : "kanban"}
    >
      {activeTab === "kanban" ? <StaffOrderBoard embedded /> : null}
      {activeTab === "table" && isAdmin ? <AdminOrderManager embedded /> : null}
    </OpsHubShell>
  );
}
