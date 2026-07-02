import { AdminCategoryManager } from "../../components/admin/AdminCategoryManager";
import { PageShell } from "../PageShell";

export function AdminCategoriesPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý danh mục"
      description="Tạo, sửa, xóa và sắp xếp danh mục thực đơn đang lưu trong backend."
      variant="admin"
    >
      <AdminCategoryManager />
    </PageShell>
  );
}
