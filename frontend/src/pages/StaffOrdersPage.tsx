import { StaffOrderBoard } from "../components/staff/StaffOrderBoard";
import { PageShell } from "./PageShell";

export function StaffOrdersPage() {
  return (
    <PageShell
      eyebrow="Staff"
      title="Đơn cần phục vụ"
      description="Bảng theo dõi để nhân viên CMC nhận món từ bếp, phục vụ khách, chuyển thu COD và hoàn tất đơn trong ca."
      variant="staff"
      stats={[
        { label: "Món chờ mang ra", value: "5", detail: "Theo dõi với bếp" },
        { label: "Đơn COD", value: "2", detail: "Cần thu ngân xác nhận" },
        { label: "Luồng xử lý", value: "Ready -> Served", detail: "Theo dõi phục vụ và thu tiền" },
      ]}
    >
      <StaffOrderBoard />
    </PageShell>
  );
}
