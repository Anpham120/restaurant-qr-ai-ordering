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
        { label: "Màn hình", value: "Orders", detail: "List + detail" },
        { label: "Nguồn dữ liệu", value: "Mock", detail: "Qua adminOrderService" },
      ]}
    >
      <AdminOrderManager />
    </PageShell>
  );
}
