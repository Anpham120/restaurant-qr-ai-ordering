import { useCallback, useEffect, useState } from "react";
import type { AdminMenuItem } from "../../types";
import {
  fetchAdminMenuItems,
  createAdminMenuItem,
  updateAdminMenuItem,
  deleteAdminMenuItem,
  setAdminMenuItemAvailability,
  type AdminMenuItemPayload,
} from "../../services/adminMenuService";
import { createApiClient } from "@cmc/api-client";
import type { AdminCategory } from "@cmc/shared-types";
import "../operations/operations.css";

const api = createApiClient({
  getAccessToken: () =>
    typeof window === "undefined" ? null : window.localStorage.getItem("cmc.accessToken"),
});

const formatVnd = (v: number) => v.toLocaleString("vi-VN") + "đ";

const EMPTY_FORM: AdminMenuItemPayload = {
  categoryId: "",
  name: "",
  description: "",
  price: 0,
  imageUrl: "",
  isAvailable: true,
  tags: [],
};

export function AdminMenuManager() {
  const [items, setItems] = useState<AdminMenuItem[]>([]);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [filterCat, setFilterCat] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<AdminMenuItemPayload>(EMPTY_FORM);
  const [tagsInput, setTagsInput] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [menuItems, cats] = await Promise.all([
        fetchAdminMenuItems(),
        api.categories.list(),
      ]);
      setItems(menuItems);
      setCategories(cats);
    } catch {
      setError("Không tải được thực đơn.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter((item) => {
    if (search && !item.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterCat && item.categoryId !== filterCat) return false;
    return true;
  });

  function openCreate() {
    setEditingId(null);
    setForm({ ...EMPTY_FORM, categoryId: categories[0]?.categoryId ?? "" });
    setTagsInput("");
    setShowForm(true);
  }

  function openEdit(item: AdminMenuItem) {
    setEditingId(item.id);
    setForm({
      categoryId: item.categoryId,
      name: item.name,
      description: item.description,
      price: item.price,
      imageUrl: item.imageUrl ?? "",
      isAvailable: item.isAvailable,
      tags: item.tags ?? [],
    });
    setTagsInput((item.tags ?? []).join(", "));
    setShowForm(true);
  }

  async function handleSave() {
    if (!form.name.trim() || !form.categoryId || form.price <= 0) {
      setNotice("Tên, danh mục và giá không được để trống.");
      return;
    }
    setIsSaving(true);
    setNotice("");
    const payload: AdminMenuItemPayload = {
      ...form,
      name: form.name.trim(),
      description: form.description.trim(),
      imageUrl: form.imageUrl?.trim() || null,
      tags: tagsInput.split(",").map((t) => t.trim()).filter(Boolean),
    };
    try {
      if (editingId) {
        await updateAdminMenuItem(editingId, payload);
        setNotice("Đã cập nhật.");
      } else {
        await createAdminMenuItem(payload);
        setNotice("Đã tạo món mới.");
      }
      setShowForm(false);
      await load();
    } catch {
      setNotice("Lưu thất bại.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Xóa món này?")) return;
    try {
      await deleteAdminMenuItem(id);
      setNotice("Đã xóa.");
      await load();
    } catch {
      setNotice("Xóa thất bại.");
    }
  }

  async function handleToggle(id: string, available: boolean) {
    try {
      await setAdminMenuItemAvailability(id, !available);
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, isAvailable: !available } : i)));
    } catch {
      setNotice("Cập nhật tình trạng thất bại.");
    }
  }

  if (isLoading) {
    return <div className="ops-empty"><div className="ops-empty-icon">📋</div>Đang tải...</div>;
  }

  return (
    <div>
      <div className="ops-page-header">
        <h1>Quản lý thực đơn</h1>
        <p>Thêm, sửa, xóa món ăn và toggle tình trạng bán</p>
      </div>

      {error ? <div className="ops-notice ops-notice--danger">{error}</div> : null}
      {notice ? <div className="ops-notice ops-notice--info">{notice}</div> : null}

      <div className="ops-toolbar">
        <div className="ops-toolbar-search">
          <input
            className="ops-form-input"
            placeholder="Tìm theo tên món..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="ops-form-select" style={{ width: 180 }} value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
          <option value="">Tất cả danh mục</option>
          {categories.map((c) => <option key={c.categoryId} value={c.categoryId}>{c.name}</option>)}
        </select>
        <button className="ops-btn ops-btn--primary" onClick={openCreate} type="button">+ Thêm món</button>
      </div>

      {/* Form modal */}
      {showForm ? (
        <div className="ops-modal-overlay" onClick={() => setShowForm(false)}>
          <div className="ops-modal" onClick={(e) => e.stopPropagation()}>
            <div className="ops-modal-header">
              <h2>{editingId ? "Sửa món" : "Thêm món mới"}</h2>
              <button className="ops-modal-close" onClick={() => setShowForm(false)} type="button">✕</button>
            </div>
            <div className="ops-modal-body">
              <div className="ops-form-group">
                <label className="ops-form-label">Tên món *</label>
                <input className="ops-form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Danh mục *</label>
                <select className="ops-form-select" value={form.categoryId} onChange={(e) => setForm({ ...form, categoryId: e.target.value })}>
                  <option value="">Chọn danh mục</option>
                  {categories.map((c) => <option key={c.categoryId} value={c.categoryId}>{c.name}</option>)}
                </select>
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Giá (VNĐ) *</label>
                <input className="ops-form-input" type="number" min={0} value={form.price} onChange={(e) => setForm({ ...form, price: Number(e.target.value) })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Mô tả</label>
                <textarea className="ops-form-textarea" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">URL Ảnh</label>
                <input className="ops-form-input" value={form.imageUrl ?? ""} onChange={(e) => setForm({ ...form, imageUrl: e.target.value })} />
              </div>
              <div className="ops-form-group">
                <label className="ops-form-label">Tags (cách nhau dấu phẩy)</label>
                <input className="ops-form-input" value={tagsInput} onChange={(e) => setTagsInput(e.target.value)} placeholder="bán chạy, mới, cay" />
              </div>
              <div className="ops-form-group">
                <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={form.isAvailable} onChange={(e) => setForm({ ...form, isAvailable: e.target.checked })} />
                  <span className="ops-form-label" style={{ margin: 0 }}>Đang bán</span>
                </label>
              </div>
            </div>
            <div className="ops-modal-footer">
              <button className="ops-btn ops-btn--ghost" onClick={() => setShowForm(false)} type="button">Hủy</button>
              <button className="ops-btn ops-btn--primary" disabled={isSaving} onClick={handleSave} type="button">
                {isSaving ? "Đang lưu..." : editingId ? "Cập nhật" : "Tạo mới"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Table */}
      <table className="ops-table">
        <thead>
          <tr>
            <th>Tên món</th>
            <th>Danh mục</th>
            <th>Giá</th>
            <th>Tình trạng</th>
            <th>Tags</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((item) => (
            <tr key={item.id}>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  {item.imageUrl ? (
                    <img src={item.imageUrl} alt={item.name} style={{ width: 40, height: 40, objectFit: "cover", borderRadius: 6 }} />
                  ) : null}
                  <div>
                    <strong>{item.name}</strong>
                    {item.description ? <div style={{ fontSize: 12, color: "var(--color-muted)" }}>{item.description.slice(0, 60)}</div> : null}
                  </div>
                </div>
              </td>
              <td>{item.categoryName}</td>
              <td>{formatVnd(item.price)}</td>
              <td>
                <button
                  className={`ops-toggle-switch ${item.isAvailable ? "ops-toggle-switch--on" : ""}`}
                  onClick={() => handleToggle(item.id, item.isAvailable)}
                  type="button"
                  aria-label={item.isAvailable ? "Tắt bán" : "Mở bán"}
                />
              </td>
              <td>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {(item.tags ?? []).map((t) => <span key={t} className="ops-card-item-chip">{t}</span>)}
                </div>
              </td>
              <td>
                <div style={{ display: "flex", gap: 4 }}>
                  <button className="ops-btn ops-btn--ghost ops-btn--sm" onClick={() => openEdit(item)} type="button">Sửa</button>
                  <button className="ops-btn ops-btn--danger ops-btn--sm" onClick={() => handleDelete(item.id)} type="button">Xóa</button>
                </div>
              </td>
            </tr>
          ))}
          {filtered.length === 0 ? (
            <tr><td colSpan={6}><div className="ops-empty">Không tìm thấy món nào</div></td></tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
