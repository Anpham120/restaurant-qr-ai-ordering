import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@cmc/auth";
import type { UserSummary, UserRole } from "@cmc/shared-types";
import { ApiError } from "@cmc/api-client";
import { api } from "../../services/apiClient";
import { Pencil, Plus, Trash2, Users, X } from "lucide-react";
import "../operations/operations.css";

const ROLES: UserRole[] = ["Customer", "Staff", "CounterStaff", "Kitchen", "Admin"];

const ROLE_LABELS: Record<string, string> = {
  Staff: "Nhân viên phục vụ",
  CounterStaff: "Nhân viên quầy",
  Kitchen: "Nhân viên bếp",
  Admin: "Quản trị viên",
  Customer: "Khách hàng",
};

const ERROR_MESSAGES: Record<string, string> = {
  EMAIL_ALREADY_REGISTERED: "Email này đã được đăng ký. Vui lòng dùng email khác.",
  EMAIL_INVALID: "Email không hợp lệ.",
  PASSWORD_TOO_SHORT: "Mật khẩu phải có ít nhất 8 ký tự.",
  FULL_NAME_REQUIRED: "Họ tên không được để trống.",
  ROLE_INVALID: "Vai trò tài khoản không hợp lệ.",
  USER_NOT_FOUND: "Không tìm thấy tài khoản.",
  CANNOT_DELETE_CURRENT_USER: "Bạn không thể xóa tài khoản đang đăng nhập.",
  CANNOT_REMOVE_OWN_ADMIN_ROLE: "Bạn không thể tự gỡ quyền Quản trị viên của tài khoản đang đăng nhập.",
  HTTP_401: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  HTTP_403: "Bạn không có quyền thực hiện thao tác này (chỉ Admin).",
};

function translateError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return ERROR_MESSAGES[err.code] ?? `${fallback} (${err.code})`;
  }
  return fallback;
}

type UserForm = { fullName: string; email: string; password: string; role: UserRole };

const EMPTY: UserForm = { fullName: "", email: "", password: "", role: "Staff" };

export function AdminUserManager() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<UserForm>(EMPTY);
  const [editingUser, setEditingUser] = useState<UserSummary | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [resetId, setResetId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
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

  function openCreateForm() {
    setEditingUser(null);
    setForm(EMPTY);
    setNotice("");
    setShowForm(true);
  }

  function openEditForm(user: UserSummary) {
    setEditingUser(user);
    setForm({ fullName: user.fullName, email: user.email, password: "", role: user.role });
    setNotice("");
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingUser(null);
  }

  async function handleSave() {
    if (!form.fullName.trim()) {
      setNotice("Vui lòng nhập họ tên.");
      return;
    }
    if (!form.email.trim() || !form.email.includes("@")) {
      setNotice("Vui lòng nhập email hợp lệ.");
      return;
    }
    if (!editingUser && form.password.length < 8) {
      setNotice("Mật khẩu phải có ít nhất 8 ký tự.");
      return;
    }
    setIsSaving(true);
    setNotice("");
    try {
      if (editingUser) {
        await api.users.update(editingUser.userId, {
          fullName: form.fullName.trim(),
          email: form.email.trim(),
          role: form.role,
        });
        setNotice(`Đã cập nhật tài khoản ${form.email.trim()}.`);
      } else {
        await api.users.create({
          ...form,
          fullName: form.fullName.trim(),
          email: form.email.trim(),
        });
        setNotice(`Đã tạo tài khoản ${ROLE_LABELS[form.role] ?? form.role} cho ${form.email.trim()}.`);
      }
      closeForm();
      await load();
    } catch (err) {
      setNotice(translateError(err, editingUser ? "Cập nhật tài khoản thất bại." : "Tạo tài khoản thất bại."));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(user: UserSummary) {
    if (!window.confirm(`Xóa tài khoản ${user.email}? Thao tác này không thể hoàn tác.`)) return;
    setDeletingId(user.userId);
    setNotice("");
    try {
      await api.users.delete(user.userId);
      setNotice(`Đã xóa tài khoản ${user.email}.`);
      await load();
    } catch (err) {
      setNotice(translateError(err, "Xóa tài khoản thất bại."));
    } finally {
      setDeletingId(null);
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
        <p>Thêm, sửa, xóa tài khoản, phân quyền và đặt lại mật khẩu</p>
      </div>

      <div className="ops-notice ops-notice--info" style={{ marginBottom: "1rem" }}>
        <strong>Phạm vi vai trò:</strong> Quản trị viên — toàn bộ cấu hình và báo cáo. Nhân viên quầy — thu ngân, đơn hàng, bàn (xem). Nhân viên bếp — bảng bếp và đơn. Phân quyền chi tiết theo vai trò được gán khi tạo hoặc sửa tài khoản.
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-toolbar">
        <div className="ops-toolbar-search">
          <input className="ops-form-input" placeholder="Tìm theo tên, email, vai trò..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <button className="ops-btn ops-btn--primary" onClick={openCreateForm} type="button">
          <Plus aria-hidden="true" size={16} /> Tạo tài khoản
        </button>
      </div>

      {showForm ? (
        <div className="ops-modal-overlay" onClick={closeForm}>
          <div
            aria-labelledby="user-form-title"
            aria-modal="true"
            className="ops-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
          >
            <div className="ops-modal-header">
              <h2 id="user-form-title">{editingUser ? "Sửa tài khoản" : "Tạo tài khoản"}</h2>
              <button aria-label="Đóng" className="ops-modal-close" onClick={closeForm} type="button"><X aria-hidden="true" size={18} /></button>
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
              {!editingUser ? (
                <div className="ops-form-group">
                  <label className="ops-form-label" htmlFor="create-user-password">Mật khẩu * (tối thiểu 8 ký tự)</label>
                  <input id="create-user-password" className="ops-form-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
              ) : null}
              <div className="ops-form-group">
                <label className="ops-form-label" htmlFor="create-user-role">Vai trò</label>
                <select id="create-user-role" className="ops-form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
                  {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r] ?? r}</option>)}
                </select>
              </div>
            </div>
            <div className="ops-modal-footer">
              <button className="ops-btn ops-btn--ghost" onClick={closeForm} type="button">Hủy</button>
              <button className="ops-btn ops-btn--primary" disabled={isSaving} onClick={handleSave} type="button">
                {isSaving ? "Đang lưu..." : editingUser ? "Lưu thay đổi" : "Tạo tài khoản"}
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
                <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
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
                  <>
                    <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => openEditForm(user)} type="button">
                      <Pencil aria-hidden="true" size={14} /> Sửa
                    </button>
                    <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => { setResetId(user.userId); setNewPassword(""); }} type="button">
                      Reset mật khẩu
                    </button>
                    <button
                      className="ops-btn ops-btn--danger ops-btn--sm"
                      disabled={deletingId === user.userId || currentUser?.userId === user.userId}
                      onClick={() => void handleDelete(user)}
                      title={currentUser?.userId === user.userId ? "Không thể xóa tài khoản đang đăng nhập" : "Xóa tài khoản"}
                      type="button"
                    >
                      <Trash2 aria-hidden="true" size={14} /> {deletingId === user.userId ? "Đang xóa..." : "Xóa"}
                    </button>
                  </>
                )}
                </div>
              </td>
            </tr>
          ))}
          {filtered.length === 0 ? <tr><td colSpan={5}><div className="ops-empty">Không tìm thấy</div></td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}
