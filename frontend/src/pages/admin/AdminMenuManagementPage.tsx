import { AdminMenuManager } from "../../components/admin/AdminMenuManager";
import { PageShell } from "../PageShell";

export function AdminMenuManagementPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý thực đơn"
      description="Quản lý món ăn, danh mục, giá bán và trạng thái còn món theo contract menu."
      variant="admin"
      stats={[
        { label: "Màn hình", value: "Menu", detail: "List, form, category" },
        { label: "Nguồn dữ liệu", value: "Mock", detail: "Qua adminMenuService" },
      ]}
    >
      <AdminMenuManager />
    </PageShell>
  );
}
