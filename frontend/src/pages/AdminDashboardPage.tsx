import { AdminDashboardOverview } from "../components/admin/AdminDashboardOverview";
import { PageShell } from "./PageShell";

export function AdminDashboardPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Tổng quan CMC"
      description="Bảng điều khiển theo dõi đơn đang phục vụ, bàn có khách, QR và trạng thái vận hành trong ngày."
      variant="admin"
      stats={[
        { label: "Đơn đang xử lý", value: "4", detail: "Cần theo dõi trong ca" },
        { label: "Bàn có khách", value: "7 / 12", detail: "Trạng thái bàn hiện tại" },
        { label: "Giá trị TB", value: "385.000đ", detail: "Theo dõi doanh thu trong ca" },
      ]}
    >
      <AdminDashboardOverview />
    </PageShell>
  );
}
