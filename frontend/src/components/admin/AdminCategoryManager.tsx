import { useEffect, useState } from "react";
import type { AdminCategory } from "@cmc/shared-types";
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
} from "../../services/adminCategoryService";
import { AdminStatePanel } from "./AdminStatePanel";

type FormState = {
  name: string;
  displayOrder: string;
  isActive: boolean;
};

function createEmptyForm(): FormState {
  return { name: "", displayOrder: "0", isActive: true };
}

function formFromCategory(cat: AdminCategory): FormState {
  return {
    name: cat.name,
    displayOrder: String(cat.displayOrder),
    isActive: cat.isActive,
  };
}

export function AdminCategoryManager() {
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [form, setForm] = useState<FormState>(createEmptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function loadCategories(preferredId?: string | null) {
    const result = await getCategories();
    setCategories(result);
    const nextId = preferredId ?? result[0]?.categoryId ?? null;
    setSelectedId(nextId);
    setIsCreating(false);
    const selected = result.find((c) => c.categoryId === nextId);
    setForm(selected ? formFromCategory(selected) : createEmptyForm());
  }

  useEffect(() => {
    loadCategories()
      .catch(() => setError("Không tải được danh sách danh mục."))
      .finally(() => setIsLoading(false));
  }, []);

  const selectedCategory = categories.find((c) => c.categoryId === selectedId);

  function startCreate() {
    setIsCreating(true);
    setSelectedId(null);
    setForm(createEmptyForm());
    setActionMessage(null);
  }

  function startEdit(cat: AdminCategory) {
    setIsCreating(false);
    setSelectedId(cat.categoryId);
    setForm(formFromCategory(cat));
    setActionMessage(null);
  }

  function updateForm(patch: Partial<FormState>) {
    setForm((current) => ({ ...current, ...patch }));
  }

  function validateForm(): string | null {
    if (!form.name.trim()) return "Tên danh mục là bắt buộc.";
    return null;
  }

  async function saveCategory() {
    const validationError = validateForm();
    if (validationError) {
      setActionMessage(validationError);
      return;
    }

    setIsSaving(true);
    setActionMessage(null);

    try {
      const payload = {
        name: form.name.trim(),
        displayOrder: Number(form.displayOrder) || 0,
        isActive: form.isActive,
      };

      const saved = isCreating
        ? await createCategory(payload)
        : selectedId
          ? await updateCategory(selectedId, payload)
          : null;

      await loadCategories(saved?.categoryId ?? selectedId);
      setActionMessage(isCreating ? "Đã tạo danh mục mới." : "Đã lưu thay đổi.");
    } catch {
      setActionMessage("Không lưu được danh mục. Kiểm tra quyền hoặc dữ liệu nhập.");
    } finally {
      setIsSaving(false);
    }
  }

  async function removeCategory() {
    if (!selectedId || isCreating) return;

    setIsSaving(true);
    setActionMessage(null);

    try {
      await deleteCategory(selectedId);
      await loadCategories(null);
      setActionMessage("Đã xóa danh mục.");
    } catch {
      setActionMessage("Không xóa được. Danh mục có thể đang chứa món ăn.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <AdminStatePanel
        title="Đang tải danh mục"
        description="Đang tải danh sách danh mục từ backend."
      />
    );
  }

  if (error) {
    return <AdminStatePanel title="Có lỗi dữ liệu" description={error} />;
  }

  return (
    <div className="admin-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">Category control</span>
          <h3>{categories.length} danh mục</h3>
          <p>
            Quản lý tên, thứ tự hiển thị và trạng thái active/inactive cho từng danh mục.
          </p>
        </div>
        <button className="button primary" type="button" onClick={startCreate}>
          + Tạo danh mục
        </button>
      </section>

      <div className="admin-split-layout">
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <span className="panel-kicker">Danh sách danh mục</span>
              <h3>Theo thứ tự hiển thị</h3>
            </div>
            <span className="admin-status admin-status-ready">Đang hoạt động</span>
          </div>

          {categories.length === 0 ? (
            <AdminStatePanel
              title="Chưa có danh mục"
              description="Tạo danh mục đầu tiên để bắt đầu."
            />
          ) : (
            <div className="admin-category-list">
              {categories.map((cat) => (
                <button
                  className={
                    selectedId === cat.categoryId
                      ? "admin-category-card active"
                      : "admin-category-card"
                  }
                  key={cat.categoryId}
                  type="button"
                  onClick={() => startEdit(cat)}
                >
                  <div className="admin-category-card-info">
                    <strong>{cat.name}</strong>
                    <small>ID: {cat.categoryId}</small>
                  </div>
                  <div className="admin-category-card-meta">
                    <span className="admin-category-order">#{cat.displayOrder}</span>
                    <span
                      className={`admin-status ${cat.isActive ? "admin-status-ready" : "admin-status-unavailable"}`}
                    >
                      {cat.isActive ? "Active" : "Inactive"}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        <aside className="admin-panel admin-form-panel">
          <span className="panel-kicker">{isCreating ? "Create" : "Edit"}</span>
          <h3>{isCreating ? "Tạo danh mục mới" : selectedCategory?.name ?? "Chọn danh mục"}</h3>
          <p>Danh mục giúp phân nhóm thực đơn để khách dễ tìm và admin quản lý.</p>

          <form
            className="admin-form"
            onSubmit={(event) => {
              event.preventDefault();
              void saveCategory();
            }}
          >
            <label>
              Tên danh mục
              <input
                value={form.name}
                onChange={(e) => updateForm({ name: e.target.value })}
                placeholder="Ví dụ: Khai vị, Món chính"
              />
            </label>
            <label>
              Thứ tự hiển thị
              <input
                value={form.displayOrder}
                onChange={(e) => updateForm({ displayOrder: e.target.value })}
                inputMode="numeric"
                placeholder="0"
              />
            </label>
            <label className="admin-check-row">
              <input
                checked={form.isActive}
                onChange={(e) => updateForm({ isActive: e.target.checked })}
                type="checkbox"
              />
              Hiển thị danh mục cho khách hàng
            </label>

            {actionMessage ? (
              <p className="admin-form-note" role="status">
                {actionMessage}
              </p>
            ) : null}

            <button className="button primary" type="submit" disabled={isSaving}>
              {isSaving ? "Đang lưu..." : isCreating ? "Lưu danh mục mới" : "Lưu thay đổi"}
            </button>

            {!isCreating && selectedId ? (
              <button
                className="button danger"
                type="button"
                onClick={removeCategory}
                disabled={isSaving}
              >
                Xóa danh mục
              </button>
            ) : null}
          </form>
        </aside>
      </div>
    </div>
  );
}
