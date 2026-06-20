import { useEffect, useState } from "react";
import { ApiError } from "@cmc/api-client";
import type { UserRole, UserSummary } from "@cmc/shared-types";
import {
  createOperationalUser,
  listUsers,
  resetUserPassword,
} from "../../services/adminUserService";
import { AdminStatePanel } from "./AdminStatePanel";

type AssignableRole = Extract<UserRole, "Staff" | "Kitchen" | "Admin">;

type FormState = {
  fullName: string;
  email: string;
  password: string;
  role: AssignableRole;
};

const roles: Array<{ value: AssignableRole; label: string; description: string }> = [
  { value: "Staff", label: "Nhân viên phục vụ", description: "Phục vụ, thu ngân, xác nhận đơn" },
  { value: "Kitchen", label: "Đầu bếp", description: "Nhận và chế biến món từ bảng bếp" },
  { value: "Admin", label: "Quản trị viên", description: "Toàn quyền quản lý hệ thống" },
];

function roleIcon(role: UserRole) {
  if (role === "Admin") return "👑";
  if (role === "Staff") return "🧑‍💼";
  if (role === "Kitchen") return "👨‍🍳";
  return "👤";
}

function createEmptyForm(): FormState {
  return { fullName: "", email: "", password: "", role: "Staff" };
}

export function AdminUserManager() {
  const [form, setForm] = useState<FormState>(createEmptyForm);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [usersError, setUsersError] = useState("");
  const [resettingUserId, setResettingUserId] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetMessage, setResetMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  async function refreshUsers() {
    try {
      setUsers(await listUsers());
      setUsersError("");
    } catch {
      setUsersError("Không tải được danh sách người dùng.");
    }
  }

  useEffect(() => {
    void refreshUsers();
  }, []);

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
      const user = await createOperationalUser({
        fullName: form.fullName.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
      });
      setForm(createEmptyForm());
      setMessage({ type: "success", text: `Đã tạo tài khoản ${user.fullName} (${user.role}).` });
      await refreshUsers();
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

  function startReset(userId: string) {
    setResettingUserId(userId);
    setResetPassword("");
    setResetMessage(null);
  }

  async function handleReset(event: React.FormEvent, user: UserSummary) {
    event.preventDefault();
    if (resetPassword.length < 8) {
      setResetMessage({ type: "error", text: "Mật khẩu tối thiểu 8 ký tự." });
      return;
    }

    try {
      await resetUserPassword(user.userId, resetPassword);
      setResettingUserId(null);
      setResetPassword("");
      setResetMessage({ type: "success", text: `Đã đặt lại mật khẩu cho ${user.fullName}.` });
    } catch {
      setResetMessage({ type: "error", text: "Không đặt lại được mật khẩu. Kiểm tra backend." });
    }
  }

  return (
    <div className="admin-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">User management</span>
          <h3>Quản lý tài khoản</h3>
          <p>
            Tạo tài khoản vận hành cho nhân viên, đầu bếp và quản trị viên. Khách hàng đặt món qua
            mã QR tại bàn nên không cần tài khoản.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{users.length} tài khoản vận hành</span>
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
                      {roleIcon(role.value)}
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
              <span className="panel-kicker">Tài khoản vận hành</span>
              <h3>Danh sách người dùng</h3>
            </div>
          </div>

          {resetMessage ? (
            <p className={`admin-form-note ${resetMessage.type === "error" ? "is-error" : ""}`} role="status">
              {resetMessage.text}
            </p>
          ) : null}

          {usersError ? (
            <AdminStatePanel title="Lỗi tải dữ liệu" description={usersError} />
          ) : users.length === 0 ? (
            <AdminStatePanel
              title="Chưa có tài khoản vận hành"
              description="Tài khoản vừa tạo sẽ hiện ở đây."
            />
          ) : (
            <div className="admin-seed-accounts">
              {users.map((user) => (
                <article className="admin-seed-card" key={user.userId}>
                  <span className={`admin-role-icon role-${user.role.toLowerCase()}`}>
                    {roleIcon(user.role)}
                  </span>
                  <div className="admin-seed-card-body">
                    <strong>{user.fullName}</strong>
                    <code>{user.email}</code>
                    <small>Role: {user.role}</small>
                    {resettingUserId === user.userId ? (
                      <form className="admin-reset-form" onSubmit={(event) => handleReset(event, user)}>
                        <input
                          value={resetPassword}
                          onChange={(e) => setResetPassword(e.target.value)}
                          placeholder="Mật khẩu mới (≥ 8 ký tự)"
                          type="password"
                          autoComplete="new-password"
                        />
                        <div className="admin-reset-actions">
                          <button className="button primary" type="submit">
                            Lưu
                          </button>
                          <button
                            className="button"
                            type="button"
                            onClick={() => setResettingUserId(null)}
                          >
                            Huỷ
                          </button>
                        </div>
                      </form>
                    ) : (
                      <button
                        className="button admin-reset-trigger"
                        type="button"
                        onClick={() => startReset(user.userId)}
                      >
                        Đặt lại mật khẩu
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
