import { useCallback, useEffect, useState } from "react";
import type { UserSummary, UserRole, CreateUserRequest } from "@cmc/shared-types";
import { createApiClient } from "@cmc/api-client";
import "../operations/operations.css";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});

const ROLES: UserRole[] = ["Admin", "Staff", "Kitchen", "Customer"];

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
    if (!form.fullName.trim() || !form.email.trim() || form.password.length < 8) {
      setNotice("Họ tên, email và mật khẩu (≥ 8 ký tự) bắt buộc.");
      return;
    }
    setIsSaving(true);
    setNotice("");
    try {
      await api.users.create(form);
      setNotice("Đã tạo tài khoản.");
      setShowForm(false);
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Tạo thất bại.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleResetPassword(userId: string) {
    if (newPassword.length < 8) { setNotice("Mật khẩu mới ≥ 8 ký tự."); return; }
    try {
      await api.users.resetPassword(userId, { newPassword });
      setNotice("Đã reset mật khẩu.");
      setResetId(null);
      setNewPassword("");
    } catch {
      setNotice("Reset thất bại.");
    }
  }

  if (isLoading) return <div className="ops-empty"><div className="ops-empty-icon">👥</div>Đang tải...</div>;

  return (
    <div>
      <div className="ops-page-header">
        <h1>Người dùng</h1>
        <p>Tạo tài khoản Staff, Kitchen, Admin và reset mật khẩu</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-toolbar">
        <div className="ops-toolbar-search">
          <input className="ops-form-input" placeholder="Tìm theo tên, email, vai trò..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <button className="ops-btn ops-btn--primary" onClick={() => { setForm(EMPTY); setShowForm(true); }} type="button">+ Tạo tài khoản</button>
      </div>

      {showForm ? (
        <div className="ops-modal-overlay" onClick={() => setShowForm(false)}>
          <div className="ops-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ops-modal-header">
              <h2>Tạo tài khoản</h2>
              <button className="ops-modal-close" onClick={() => setShowForm(false)} type="button">✕</button>
            </div>
            <div className="ops-modal-body">
              <div className="ops-form-group">
                <label className="ops-form-label">Họ tên *</label>
                <input className="ops-form-input" value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Email *</label>
                <input className="ops-form-input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Mật khẩu * (≥ 8 ký tự)</label>
                <input className="ops-form-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Vai trò</label>
                <select className="ops-form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
                  {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>
            <div className="ops-modal-footer">
              <button className="ops-btn ops-btn--ghost" onClick={() => setShowForm(false)} type="button">Hủy</button>
              <button className="ops-btn ops-btn--primary" disabled={isSaving} onClick={handleCreate} type="button">
                {isSaving ? "Đang tạo..." : "Tạo"}
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
                  {user.role}
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
