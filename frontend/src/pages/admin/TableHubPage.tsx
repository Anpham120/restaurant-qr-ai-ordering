import { useAuth } from "@cmc/auth";
import { AdminTableSessionMonitor } from "../../components/admin/AdminTableSessionMonitor";
import { AdminTableCrudPanel } from "../../components/admin/AdminTableCrudPanel";
import { AdminQrTableManager } from "../../components/qr/AdminQrTableManager";
import { OpsHubShell } from "../../components/operations/OpsHubShell";
import { useOpsHubTab } from "../../components/operations/OpsHubTabs";
import { useOpsConnectionStatus } from "../../components/operations/OpsRealtimeProvider";
import "../../components/operations/operations.css";

const TABLE_TABS = [
  { id: "sessions", label: "Sơ đồ / phiên" },
  { id: "qr", label: "QR & link" },
  { id: "manage", label: "Quản lý bàn", adminOnly: true },
];

export function TableHubPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";
  const { activeTab } = useOpsHubTab(TABLE_TABS, "tab", isAdmin);
  const connectionStatus = useOpsConnectionStatus();

  return (
    <OpsHubShell
      title="Bàn"
      description="Theo dõi phiên, quản lý QR và cấu hình bàn trên cùng một màn hình."
      tabs={TABLE_TABS}
      isAdmin={isAdmin}
      connectionStatus={connectionStatus}
    >
      {activeTab === "sessions" ? <AdminTableSessionMonitor embedded /> : null}
      {activeTab === "qr" ? <AdminQrTableManager embedded /> : null}
      {activeTab === "manage" && isAdmin ? <AdminTableCrudPanel /> : null}
    </OpsHubShell>
  );
}
