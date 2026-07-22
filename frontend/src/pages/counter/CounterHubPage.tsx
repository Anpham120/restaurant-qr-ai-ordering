import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { AdminInvoicesPanel } from "../AdminInvoicesPage";
import { StaffPaymentsPage } from "../StaffPaymentsPage";
import { CounterShiftPanel } from "./CounterShiftPanel";
import { OpsHubShell } from "../../components/operations/OpsHubShell";
import { useOpsHubTab } from "../../components/operations/OpsHubTabs";
import { useOpsConnectionStatus } from "../../components/operations/OpsRealtimeProvider";
import { hasPendingCounterPayments } from "../../services/opsSummaryService";
import "../../components/operations/operations.css";

const COUNTER_TABS = [
  { id: "shift", label: "Ca làm việc" },
  { id: "payments", label: "Chờ thanh toán" },
  { id: "invoices", label: "Lịch sử hóa đơn" },
];

export function CounterHubPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeTab } = useOpsHubTab(COUNTER_TABS);
  const connectionStatus = useOpsConnectionStatus();

  useEffect(() => {
    if (searchParams.get("tab")) return;
    let active = true;
    void hasPendingCounterPayments()
      .then((hasPending) => {
        if (!active || !hasPending) return;
        setSearchParams({ tab: "payments" }, { replace: true });
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [searchParams, setSearchParams]);

  return (
    <OpsHubShell
      title="Quầy thu ngân"
      description="Mở ca, thu tiền và tra cứu hóa đơn phiên bàn."
      tabs={COUNTER_TABS}
      connectionStatus={connectionStatus}
    >
      {activeTab === "shift" ? <CounterShiftPanel embedded /> : null}
      {activeTab === "payments" ? <StaffPaymentsPage embedded /> : null}
      {activeTab === "invoices" ? <AdminInvoicesPanel embedded /> : null}
    </OpsHubShell>
  );
}
