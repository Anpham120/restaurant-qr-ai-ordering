import { AdminCategoryManager } from "../../components/admin/AdminCategoryManager";
import { PageShell } from "../PageShell";

export function AdminCategoriesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý danh mục"
      description="Tạo, sửa, xóa và sắp xếp danh mục thực đơn cho nhà hàng."
      variant="admin"
      stats={[
        { label: "Chức năng", value: "CRUD", detail: "Create, Read, Update, Delete" },
        { label: "Nguồn dữ liệu", value: "API", detail: "Qua adminCategoryService" },
      ]}
    >
      <AdminCategoryManager />
    </PageShell>
  );
}
