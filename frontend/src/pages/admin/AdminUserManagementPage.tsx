import { AdminUserManager } from "../../components/admin/AdminUserManager";
import { PageShell } from "../PageShell";

export function AdminUserManagementPage() {
  return (
    <PageShell
      eyebrow="Admin"
      title="Quản lý người dùng"
      description="Tạo tài khoản vận hành cho nhân viên, đầu bếp và quản trị viên."
      variant="admin"
      stats={[
        { label: "Chức năng", value: "Register", detail: "Tạo tài khoản qua API" },
        { label: "Phân quyền", value: "4 roles", detail: "Admin, Staff, Kitchen, Customer" },
      ]}
    >
      <AdminUserManager />
    </PageShell>
  );
}
