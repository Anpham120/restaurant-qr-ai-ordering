import { useState } from "react";
import { ApiError } from "@cmc/api-client";
import type { AuthUser, UserRole } from "@cmc/shared-types";
import { registerUser } from "../../services/adminUserService";
import { AdminStatePanel } from "./AdminStatePanel";

type FormState = {
  fullName: string;
  email: string;
  password: string;
  role: UserRole;
};

const roles: Array<{ value: UserRole; label: string; description: string }> = [
  { value: "Admin", label: "Quản trị viên", description: "Toàn quyền quản lý hệ thống" },
  { value: "Staff", label: "Nhân viên phục vụ", description: "Phục vụ, thu ngân, xác nhận đơn" },
  { value: "Kitchen", label: "Đầu bếp", description: "Nhận và chế biến món từ bảng bếp" },
  { value: "Customer", label: "Khách hàng", description: "Đặt món, theo dõi đơn" },
];

function createEmptyForm(): FormState {
  return { fullName: "", email: "", password: "", role: "Staff" };
}

export function AdminUserManager() {
  const [form, setForm] = useState<FormState>(createEmptyForm);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [createdUsers, setCreatedUsers] = useState<AuthUser[]>([]);

  function updateForm(patch: Partial<FormState>) {
    setForm((current) => ({ ...current, ...patch }));
  }

  function validateForm(): string | null {
    if (!form.fullName.trim()) return "Họ tên là bắt buộc.";
    if (!form.email.trim()) return "Email là bắt buộc.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return "Email không hợp lệ.";
    if (form.password.length < 8) return "Mật khẩu tối thiểu 8 ký tự.";
    return null;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const validationError = validateForm();
    if (validationError) {
      setMessage({ type: "error", text: validationError });
      return;
    }

    setIsSaving(true);
    setMessage(null);

    try {
      const user = await registerUser({
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      setCreatedUsers((prev) => [user, ...prev]);
      setForm(createEmptyForm());
      setMessage({
        type: "success",
        text: `Đã tạo tài khoản ${user.fullName} (${user.role}).`,
      });
    } catch (err) {
      if (err instanceof ApiError && err.code === "EMAIL_ALREADY_REGISTERED") {
        setMessage({ type: "error", text: "Email này đã được đăng ký." });
      } else {
        setMessage({ type: "error", text: "Không tạo được tài khoản. Kiểm tra backend." });
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="admin-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">User management</span>
          <h3>Quản lý tài khoản</h3>
          <p>
            Tạo tài khoản vận hành cho admin, nhân viên và đầu bếp. Mỗi tài khoản có vai trò
            xác định quyền truy cập trong hệ thống.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{createdUsers.length} tài khoản mới trong phiên</span>
        </div>
      </section>

      <div className="admin-split-layout">
        <section className="admin-panel admin-form-panel">
          <span className="panel-kicker">Tạo tài khoản</span>
          <h3>Thêm người dùng mới</h3>
          <p>Điền thông tin bên dưới để cấp tài khoản vận hành.</p>

          <form className="admin-form" onSubmit={handleSubmit}>
            <label>
              Họ và tên
              <input
                value={form.fullName}
                onChange={(e) => updateForm({ fullName: e.target.value })}
                placeholder="Nguyễn Văn A"
              />
            </label>
            <label>
              Email
              <input
                value={form.email}
                onChange={(e) => updateForm({ email: e.target.value })}
                placeholder="user@restaurant.local"
                type="email"
                autoComplete="off"
              />
            </label>
            <label>
              Mật khẩu
              <input
                value={form.password}
                onChange={(e) => updateForm({ password: e.target.value })}
                placeholder="Tối thiểu 8 ký tự"
                type="password"
                autoComplete="new-password"
              />
            </label>
            <label>
              Vai trò
              <div className="admin-role-selector">
                {roles.map((role) => (
                  <button
                    className={`admin-role-option ${form.role === role.value ? "active" : ""}`}
                    key={role.value}
                    type="button"
                    onClick={() => updateForm({ role: role.value })}
                  >
                    <span className={`admin-role-icon role-${role.value.toLowerCase()}`}>
                      {role.value === "Admin" ? "👑" : role.value === "Staff" ? "🧑‍💼" : role.value === "Kitchen" ? "👨‍🍳" : "👤"}
                    </span>
                    <div>
                      <strong>{role.label}</strong>
                      <small>{role.description}</small>
                    </div>
                  </button>
                ))}
              </div>
            </label>

            {message ? (
              <p className={`admin-form-note ${message.type === "error" ? "is-error" : ""}`} role="status">
                {message.text}
              </p>
            ) : null}

            <button className="button primary" type="submit" disabled={isSaving}>
              {isSaving ? "Đang tạo..." : "Tạo tài khoản"}
            </button>
          </form>
        </section>

        <aside className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <span className="panel-kicker">Tài khoản mặc định</span>
              <h3>Seed accounts</h3>
            </div>
          </div>

          <div className="admin-seed-accounts">
            <article className="admin-seed-card">
              <span className="admin-role-icon role-admin">👑</span>
              <div>
                <strong>Quản trị viên</strong>
                <code>admin@restaurant.local</code>
                <small>Role: Admin</small>
              </div>
            </article>
            <article className="admin-seed-card">
              <span className="admin-role-icon role-staff">🧑‍💼</span>
              <div>
                <strong>Nhân viên thu ngân</strong>
                <code>staff@restaurant.local</code>
                <small>Role: Staff</small>
              </div>
            </article>
            <article className="admin-seed-card">
              <span className="admin-role-icon role-kitchen">👨‍🍳</span>
              <div>
                <strong>Đầu bếp</strong>
                <code>kitchen@restaurant.local</code>
                <small>Role: Kitchen</small>
              </div>
            </article>
          </div>

          {createdUsers.length > 0 ? (
            <>
              <div className="admin-panel-heading" style={{ marginTop: "1.5rem" }}>
                <div>
                  <span className="panel-kicker">Mới tạo</span>
                  <h3>Trong phiên này</h3>
                </div>
              </div>
              <div className="admin-seed-accounts">
                {createdUsers.map((user) => (
                  <article className="admin-seed-card" key={user.userId}>
                    <span className={`admin-role-icon role-${user.role.toLowerCase()}`}>
                      {user.role === "Admin" ? "👑" : user.role === "Staff" ? "🧑‍💼" : user.role === "Kitchen" ? "👨‍🍳" : "👤"}
                    </span>
                    <div>
                      <strong>{user.fullName}</strong>
                      <code>{user.email}</code>
                      <small>Role: {user.role}</small>
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <AdminStatePanel
              title="Chưa tạo tài khoản mới"
              description="Tài khoản vừa tạo sẽ hiện ở đây."
            />
          )}
        </aside>
      </div>
    </div>
  );
}
