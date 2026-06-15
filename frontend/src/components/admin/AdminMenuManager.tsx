import { useEffect, useMemo, useState } from "react";
import {
  createAdminMenuItem,
  deleteAdminMenuItem,
  getAdminMenuOverview,
  setAdminMenuItemAvailability,
  updateAdminMenuItem,
  type AdminMenuItemPayload,
} from "../../services/adminMenuService";
import type { AdminMenuCategory, AdminMenuItem } from "../../types";
import { resolveMenuImage } from "../../utils/menuImages";
import { AdminStatePanel } from "./AdminStatePanel";
import { AdminStatusBadge } from "./AdminStatusBadge";

type FormState = {
  name: string;
  categoryId: string;
  price: string;
  description: string;
  imageUrl: string;
  tags: string;
  isAvailable: boolean;
};

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

function createEmptyForm(categoryId = ""): FormState {
  return {
    name: "",
    categoryId,
    price: "",
    description: "",
    imageUrl: "",
    tags: "",
    isAvailable: true,
  };
}

function formFromItem(item: AdminMenuItem): FormState {
  return {
    name: item.name,
    categoryId: item.categoryId,
    price: String(item.price),
    description: item.description,
    imageUrl: item.imageUrl ?? "",
    tags: item.tags.join(", "),
    isAvailable: item.isAvailable,
  };
}

function toPayload(form: FormState): AdminMenuItemPayload {
  return {
    categoryId: form.categoryId,
    name: form.name.trim(),
    description: form.description.trim(),
    price: Number(form.price),
    imageUrl: form.imageUrl.trim() || null,
    isAvailable: form.isAvailable,
    tags: form.tags
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
  };
}

export function AdminMenuManager() {
  const [items, setItems] = useState<AdminMenuItem[]>([]);
  const [categories, setCategories] = useState<AdminMenuCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [form, setForm] = useState<FormState>(() => createEmptyForm());
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadOverview = async (preferredItemId?: string | null) => {
    const overview = await getAdminMenuOverview();
    const nextSelectedId = preferredItemId ?? overview.items[0]?.id ?? null;

    setItems(overview.items);
    setCategories(overview.categories);
    setSelectedItemId(nextSelectedId);
    setIsCreating(false);

    const nextSelectedItem = overview.items.find((item) => item.id === nextSelectedId);
    setForm(nextSelectedItem ? formFromItem(nextSelectedItem) : createEmptyForm(overview.categories[0]?.id));
  };

  useEffect(() => {
    loadOverview()
      .catch(() => setError("Không tải được dữ liệu thực đơn từ backend."))
      .finally(() => setIsLoading(false));
  }, []);

  const visibleItems = useMemo(
    () =>
      selectedCategory === "all"
        ? items
        : items.filter((item) => item.categoryId === selectedCategory),
    [items, selectedCategory],
  );

  const selectedItem = items.find((item) => item.id === selectedItemId) ?? items[0];
  const availableCount = items.filter((item) => item.isAvailable).length;
  const unavailableCount = items.length - availableCount;

  const startCreate = () => {
    setIsCreating(true);
    setSelectedItemId(null);
    setForm(createEmptyForm(categories[0]?.id));
    setActionMessage(null);
  };

  const startEdit = (item: AdminMenuItem) => {
    setIsCreating(false);
    setSelectedItemId(item.id);
    setForm(formFromItem(item));
    setActionMessage(null);
  };

  const updateForm = (patch: Partial<FormState>) => {
    setForm((current) => ({ ...current, ...patch }));
  };

  const validateForm = () => {
    if (!form.name.trim()) {
      return "Tên món là bắt buộc.";
    }
    if (!form.categoryId) {
      return "Vui lòng chọn danh mục.";
    }
    if (!Number.isFinite(Number(form.price)) || Number(form.price) <= 0) {
      return "Giá bán phải lớn hơn 0.";
    }
    return null;
  };

  const saveMenuItem = async () => {
    const validationError = validateForm();
    if (validationError) {
      setActionMessage(validationError);
      return;
    }

    setIsSaving(true);
    setActionMessage(null);

    try {
      const savedItem = isCreating
        ? await createAdminMenuItem(toPayload(form))
        : selectedItemId
          ? await updateAdminMenuItem(selectedItemId, toPayload(form))
          : null;

      await loadOverview(savedItem?.id ?? selectedItemId);
      setActionMessage(isCreating ? "Đã tạo món mới." : "Đã lưu thay đổi món.");
    } catch {
      setActionMessage("Không lưu được món. Kiểm tra quyền admin hoặc dữ liệu nhập.");
    } finally {
      setIsSaving(false);
    }
  };

  const removeSelectedItem = async () => {
    if (!selectedItemId || isCreating) {
      return;
    }

    setIsSaving(true);
    setActionMessage(null);

    try {
      await deleteAdminMenuItem(selectedItemId);
      await loadOverview(null);
      setActionMessage("Đã xóa món khỏi thực đơn.");
    } catch {
      setActionMessage("Không xóa được món. Có thể món đang được tham chiếu bởi đơn hàng.");
    } finally {
      setIsSaving(false);
    }
  };

  const toggleAvailability = async (itemId: string) => {
    const currentItem = items.find((item) => item.id === itemId);
    if (!currentItem) {
      return;
    }

    setItems((currentItems) =>
      currentItems.map((item) =>
        item.id === itemId ? { ...item, isAvailable: !item.isAvailable } : item,
      ),
    );
    setActionMessage(null);

    try {
      const updatedItem = await setAdminMenuItemAvailability(itemId, !currentItem.isAvailable);
      setItems((currentItems) =>
        currentItems.map((item) => (item.id === itemId ? { ...item, ...updatedItem } : item)),
      );
      if (selectedItemId === itemId) {
        setForm(formFromItem({ ...currentItem, ...updatedItem }));
      }
    } catch {
      setItems((currentItems) =>
        currentItems.map((item) =>
          item.id === itemId ? { ...item, isAvailable: currentItem.isAvailable } : item,
        ),
      );
      setActionMessage("Không thể cập nhật trạng thái món.");
    }
  };

  if (isLoading) {
    return (
      <AdminStatePanel
        title="Đang tải thực đơn"
        description="Đang tải dữ liệu món ăn cho màn quản trị."
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
          <span className="panel-kicker">Menu control</span>
          <h3>{items.length} món trong thực đơn</h3>
          <p>
            {availableCount} món đang bán, {unavailableCount} món tạm hết. Quản lý danh mục,
            giá bán và trạng thái hiển thị cho khách.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{categories.length} danh mục</span>
          <span>{visibleItems.length} món đang xem</span>
        </div>
        <button className="button primary" type="button" onClick={startCreate}>
          + Tạo món
        </button>
      </section>

      <section className="admin-category-strip" aria-label="Lọc danh mục">
        <button
          className={selectedCategory === "all" ? "admin-chip active" : "admin-chip"}
          type="button"
          onClick={() => setSelectedCategory("all")}
        >
          Tất cả ({items.length})
        </button>
        {categories.map((category) => (
          <button
            className={selectedCategory === category.id ? "admin-chip active" : "admin-chip"}
            key={category.id}
            type="button"
            onClick={() => setSelectedCategory(category.id)}
          >
            {category.name} ({category.itemCount})
          </button>
        ))}
      </section>

      <div className="admin-split-layout">
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <div>
              <span className="panel-kicker">Danh sách món</span>
              <h3>Trạng thái hiển thị</h3>
            </div>
            <span className="admin-status admin-status-ready">Đang hoạt động</span>
          </div>

          {visibleItems.length === 0 ? (
            <AdminStatePanel
              title="Không có món phù hợp"
              description="Thử chọn danh mục khác hoặc tạo món mới."
            />
          ) : (
            <div className="admin-menu-table">
              {visibleItems.map((item, index) => (
                <article className="admin-menu-row" key={item.id}>
                  <img alt={item.name} src={resolveMenuImage(item.name, item.imageUrl, index)} />
                  <div>
                    <span className="panel-kicker">{item.categoryName}</span>
                    <h4>{item.name}</h4>
                    <p>{item.description}</p>
                    <div className="admin-tag-row">
                      {item.tags.map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div className="admin-row-actions">
                    <strong>{formatCurrency(item.price)}</strong>
                    <AdminStatusBadge status={item.isAvailable ? "Available" : "Unavailable"} />
                    <button type="button" onClick={() => toggleAvailability(item.id)}>
                      {item.isAvailable ? "Tạm hết" : "Mở bán"}
                    </button>
                    <button type="button" onClick={() => startEdit(item)}>
                      Sửa
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <aside className="admin-panel admin-form-panel">
          <span className="panel-kicker">{isCreating ? "Create" : "Edit"}</span>
          <h3>{isCreating ? "Tạo món mới" : selectedItem?.name ?? "Chọn món"}</h3>
          <p>Cập nhật món qua API admin để khách, bếp và nhân viên cùng dùng một nguồn dữ liệu.</p>
          <form
            className="admin-form"
            onSubmit={(event) => {
              event.preventDefault();
              void saveMenuItem();
            }}
          >
            <label>
              Tên món
              <input
                value={form.name}
                onChange={(event) => updateForm({ name: event.target.value })}
                placeholder="Nhập tên món"
              />
            </label>
            <label>
              Danh mục
              <select
                value={form.categoryId}
                onChange={(event) => updateForm({ categoryId: event.target.value })}
              >
                <option value="" disabled>
                  Chọn danh mục
                </option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Giá bán
              <input
                value={form.price}
                onChange={(event) => updateForm({ price: event.target.value })}
                inputMode="numeric"
                placeholder="65000"
              />
            </label>
            <label>
              Ảnh món
              <input
                value={form.imageUrl}
                onChange={(event) => updateForm({ imageUrl: event.target.value })}
                placeholder="https://..."
              />
            </label>
            <label>
              Mô tả
              <textarea
                value={form.description}
                onChange={(event) => updateForm({ description: event.target.value })}
                placeholder="Mô tả ngắn cho khách và admin"
              />
            </label>
            <label>
              Tags
              <input
                value={form.tags}
                onChange={(event) => updateForm({ tags: event.target.value })}
                placeholder="signature, cay nhẹ, bán chạy"
              />
            </label>
            <label className="admin-check-row">
              <input
                checked={form.isAvailable}
                onChange={(event) => updateForm({ isAvailable: event.target.checked })}
                type="checkbox"
              />
              Hiển thị là còn món
            </label>
            {actionMessage ? (
              <p className="admin-form-note" role="status">
                {actionMessage}
              </p>
            ) : null}
            <button className="button primary" type="submit" disabled={isSaving}>
              {isSaving ? "Đang lưu..." : isCreating ? "Lưu món mới" : "Lưu thay đổi"}
            </button>
            {!isCreating && selectedItemId ? (
              <button className="button" type="button" onClick={removeSelectedItem} disabled={isSaving}>
                Xóa món
              </button>
            ) : null}
          </form>

          <div className="admin-category-summary">
            <span className="panel-kicker">Danh mục</span>
            {categories.map((category) => (
              <div key={category.id}>
                <strong>{category.name}</strong>
                <span>{category.itemCount} món</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
