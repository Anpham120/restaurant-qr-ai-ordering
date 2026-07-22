import { useAuth } from "@cmc/auth";
import { AdminOrderManager } from "../../components/admin/AdminOrderManager";
import { StaffOrderBoard } from "../../components/staff/StaffOrderBoard";
import { OpsHubShell } from "../../components/operations/OpsHubShell";
import { useOpsHubTab } from "../../components/operations/OpsHubTabs";
import { useOpsConnectionStatus } from "../../components/operations/OpsRealtimeProvider";
import "../../components/operations/operations.css";

const ORDER_TABS = [
  { id: "kanban", label: "Kanban" },
  { id: "table", label: "Bảng chi tiết", adminOnly: true },
];

export function OrdersHubPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";
  const { activeTab } = useOpsHubTab(ORDER_TABS, "tab", isAdmin);
  const connectionStatus = useOpsConnectionStatus();

  return (
    <OpsHubShell
      title="Đơn hàng"
      description="Theo dõi kanban realtime hoặc quản lý chi tiết toàn bộ đơn."
      tabs={ORDER_TABS}
      isAdmin={isAdmin}
      connectionStatus={connectionStatus}
    >
      {activeTab === "kanban" ? <StaffOrderBoard embedded /> : null}
      {activeTab === "table" && isAdmin ? <AdminOrderManager embedded /> : null}
    </OpsHubShell>
  );
}
