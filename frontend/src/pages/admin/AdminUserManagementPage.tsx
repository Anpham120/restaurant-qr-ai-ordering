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
        { label: "Chức năng", value: "Tạo & reset", detail: "Admin tạo tài khoản và đặt lại mật khẩu" },
        { label: "Phân quyền", value: "3 roles", detail: "Staff, Kitchen, Admin" },
      ]}
    >
      <AdminUserManager />
    </PageShell>
  );
}
