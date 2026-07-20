import { StaffPaymentsPage } from "../StaffPaymentsPage";
import { CounterShiftPanel } from "./CounterShiftPanel";

export function CounterWorkspacePage() {
  return (
    <div className="counter-workspace">
      <CounterShiftPanel />
      <StaffPaymentsPage />
    </div>
  );
}
