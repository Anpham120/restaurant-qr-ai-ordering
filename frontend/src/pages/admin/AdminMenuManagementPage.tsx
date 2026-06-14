import { AdminMenuManager } from "../../components/admin/AdminMenuManager";
import { PageShell } from "../PageShell";

export function AdminMenuManagementPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý thực đơn"
      description="Quản lý món ăn, danh mục, giá bán và trạng thái còn món trên thực đơn."
      variant="admin"
      stats={[
        { label: "Màn hình", value: "Menu", detail: "Danh sách, form, danh mục" },
        { label: "Nguồn dữ liệu", value: "Thực đơn", detail: "Qua adminMenuService" },
      ]}
    >
      <AdminMenuManager />
    </PageShell>
  );
}
