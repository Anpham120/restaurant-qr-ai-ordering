import { AdminOrderManager } from "../../components/admin/AdminOrderManager";
import { PageShell } from "../PageShell";

export function AdminOrderManagementPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý đơn hàng"
      description="Theo dõi danh sách đơn, trạng thái xử lý và chi tiết món cần phục vụ."
      variant="admin"
      stats={[
        { label: "Màn hình", value: "Orders", detail: "Danh sách và chi tiết" },
        { label: "Nguồn dữ liệu", value: "API", detail: "Qua adminOrderService" },
      ]}
    >
      <AdminOrderManager />
    </PageShell>
  );
}
