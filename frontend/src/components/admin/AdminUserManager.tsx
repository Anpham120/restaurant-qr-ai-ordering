import { useCallback, useEffect, useState } from "react";
import type { UserSummary, UserRole, CreateUserRequest } from "@cmc/shared-types";
import { ApiError } from "@cmc/api-client";
import { api } from "../../services/apiClient";
import { Plus, Users, X } from "lucide-react";
import "../operations/operations.css";

// Backend chỉ cho phép tạo tài khoản vận hành: Staff, Kitchen, Admin.
// Tài khoản Customer do khách tự đăng ký qua /api/auth/register.
const ROLES: UserRole[] = ["Staff", "Kitchen", "Admin"];

const ROLE_LABELS: Record<string, string> = {
  Staff: "Nhân viên phục vụ",
  Kitchen: "Nhân viên bếp",
  Admin: "Quản trị viên",
  Customer: "Khách hàng",
};

const ERROR_MESSAGES: Record<string, string> = {
  EMAIL_ALREADY_REGISTERED: "Email này đã được đăng ký. Vui lòng dùng email khác.",
  EMAIL_INVALID: "Email không hợp lệ.",
  PASSWORD_TOO_SHORT: "Mật khẩu phải có ít nhất 8 ký tự.",
  FULL_NAME_REQUIRED: "Họ tên không được để trống.",
  ROLE_INVALID: "Vai trò chỉ được là Nhân viên phục vụ, Nhân viên bếp hoặc Quản trị viên.",
  USER_NOT_FOUND: "Không tìm thấy tài khoản.",
  HTTP_401: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  HTTP_403: "Bạn không có quyền thực hiện thao tác này (chỉ Admin).",
};

function translateError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return ERROR_MESSAGES[err.code] ?? `${fallback} (${err.code})`;
  }
  return fallback;
}

const EMPTY: CreateUserRequest = { fullName: "", email: "", password: "", role: "Staff" };

export function AdminUserManager() {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateUserRequest>(EMPTY);
  const [isSaving, setIsSaving] = useState(false);
  const [resetId, setResetId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api.users.list();
      setUsers(data.users);
    } catch {
      setError("Không tải được danh sách người dùng.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = users.filter((u) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return u.fullName.toLowerCase().includes(q) || u.email.toLowerCase().includes(q) || u.role.toLowerCase().includes(q);
  });

  async function handleCreate() {
    if (!form.fullName.trim()) {
      setNotice("Vui lòng nhập họ tên.");
      return;
    }
    if (!form.email.trim() || !form.email.includes("@")) {
      setNotice("Vui lòng nhập email hợp lệ.");
      return;
    }
    if (form.password.length < 8) {
      setNotice("Mật khẩu phải có ít nhất 8 ký tự.");
      return;
    }
    setIsSaving(true);
    setNotice("");
    try {
      await api.users.create({
        ...form,
        fullName: form.fullName.trim(),
        email: form.email.trim(),
      });
      setNotice(`Đã tạo tài khoản ${ROLE_LABELS[form.role] ?? form.role} cho ${form.email.trim()}.`);
      setShowForm(false);
      await load();
    } catch (err) {
      setNotice(translateError(err, "Tạo tài khoản thất bại."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleResetPassword(userId: string) {
    if (newPassword.length < 8) { setNotice("Mật khẩu mới phải có ít nhất 8 ký tự."); return; }
    try {
      await api.users.resetPassword(userId, { newPassword });
      setNotice("Đã đặt lại mật khẩu.");
      setResetId(null);
      setNewPassword("");
    } catch (err) {
      setNotice(translateError(err, "Đặt lại mật khẩu thất bại."));
    }
  }

  if (isLoading) return <div className="ops-empty"><div className="ops-empty-icon"><Users aria-hidden="true" /></div>Đang tải...</div>;

  return (
    <div>
      <div className="ops-page-header">
        <h1>Người dùng</h1>
        <p>Tạo tài khoản nhân viên phục vụ, bếp, quản trị viên và đặt lại mật khẩu</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-toolbar">
        <div className="ops-toolbar-search">
          <input className="ops-form-input" placeholder="Tìm theo tên, email, vai trò..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <button className="ops-btn ops-btn--primary" onClick={() => { setForm(EMPTY); setShowForm(true); }} type="button">
          <Plus aria-hidden="true" size={16} /> Tạo tài khoản
        </button>
      </div>

      {showForm ? (
        <div className="ops-modal-overlay" onClick={() => setShowForm(false)}>
          <div
            aria-labelledby="create-user-title"
            aria-modal="true"
            className="ops-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
          >
            <div className="ops-modal-header">
              <h2 id="create-user-title">Tạo tài khoản</h2>
              <button aria-label="Đóng" className="ops-modal-close" onClick={() => setShowForm(false)} type="button"><X aria-hidden="true" size={18} /></button>
            </div>
            <div className="ops-modal-body">
              <div className="ops-form-group">
                <label className="ops-form-label" htmlFor="create-user-full-name">Họ tên *</label>
                <input id="create-user-full-name" className="ops-form-input" value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label" htmlFor="create-user-email">Email *</label>
                <input id="create-user-email" className="ops-form-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label" htmlFor="create-user-password">Mật khẩu * (tối thiểu 8 ký tự)</label>
                <input id="create-user-password" className="ops-form-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label" htmlFor="create-user-role">Vai trò</label>
                <select id="create-user-role" className="ops-form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
                  {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r] ?? r}</option>)}
                </select>
              </div>
            </div>
            <div className="ops-modal-footer">
              <button className="ops-btn ops-btn--ghost" onClick={() => setShowForm(false)} type="button">Hủy</button>
              <button className="ops-btn ops-btn--primary" disabled={isSaving} onClick={handleCreate} type="button">
                {isSaving ? "Đang tạo..." : "Tạo tài khoản"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <table className="ops-table">
        <thead>
          <tr>
            <th>Họ tên</th>
            <th>Email</th>
            <th>Vai trò</th>
            <th>Ngày tạo</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((user) => (
            <tr key={user.userId}>
              <td><strong>{user.fullName}</strong></td>
              <td>{user.email}</td>
              <td>
                <span className={`ops-badge ops-badge--${user.role === "Admin" ? "placed" : user.role === "Staff" ? "served" : user.role === "Kitchen" ? "preparing" : "ready"}`}>
                  {ROLE_LABELS[user.role] ?? user.role}
                </span>
              </td>
              <td style={{ fontSize: 12, color: "var(--color-muted)" }}>{new Date(user.createdAt).toLocaleDateString("vi-VN")}</td>
              <td>
                {resetId === user.userId ? (
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <input
                      className="ops-form-input"
                      type="password"
                      placeholder="Mật khẩu mới"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      style={{ width: 140, padding: "4px 8px", fontSize: 12 }}
                    />
                    <button className="ops-btn ops-btn--primary ops-btn--sm" onClick={() => handleResetPassword(user.userId)} type="button">Lưu</button>
                    <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => { setResetId(null); setNewPassword(""); }} type="button">Hủy</button>
                  </div>
                ) : (
                  <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => { setResetId(user.userId); setNewPassword(""); }} type="button">
                    Reset mật khẩu
                  </button>
                )}
              </td>
            </tr>
          ))}
          {filtered.length === 0 ? <tr><td colSpan={5}><div className="ops-empty">Không tìm thấy</div></td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}
