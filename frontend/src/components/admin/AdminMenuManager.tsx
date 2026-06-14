import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createAdminMenuItem,
  getAdminMenuOverview,
  updateAdminMenuItem,
  updateAdminMenuItemAvailability,
  type AdminMenuItemInput,
} from "../../services/adminMenuService";
import type { AdminMenuCategory, AdminMenuItem } from "../../types";
import { AdminStatePanel } from "./AdminStatePanel";
import { AdminStatusBadge } from "./AdminStatusBadge";

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

type MenuFormState = {
  name: string;
  categoryId: string;
  price: string;
  imageUrl: string;
  description: string;
  tags: string;
  isAvailable: boolean;
};

function buildEmptyForm(categoryId = ""): MenuFormState {
  return {
    name: "",
    categoryId,
    price: "",
    imageUrl: "",
    description: "",
    tags: "",
    isAvailable: true,
  };
}

function buildFormFromItem(item: AdminMenuItem): MenuFormState {
  return {
    name: item.name,
    categoryId: item.categoryId,
    price: String(item.price),
    imageUrl: item.imageUrl,
    description: item.description,
    tags: item.tags.join(", "),
    isAvailable: item.isAvailable,
  };
}

function toMenuInput(form: MenuFormState): AdminMenuItemInput {
  return {
    name: form.name,
    categoryId: form.categoryId,
    description: form.description,
    price: Number(form.price),
    imageUrl: form.imageUrl,
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
  const [form, setForm] = useState<MenuFormState>(buildEmptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getAdminMenuOverview()
      .then((overview) => {
        setItems(overview.items);
        setCategories(overview.categories);
        const firstItem = overview.items[0] ?? null;
        const firstCategoryId = overview.categories[0]?.id ?? "";
        setSelectedItemId(firstItem?.id ?? null);
        setForm(firstItem ? buildFormFromItem(firstItem) : buildEmptyForm(firstCategoryId));
      })
      .catch((loadError) =>
        setError(loadError instanceof Error ? loadError.message : "Không tải được dữ liệu thực đơn."),
      )
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

  function updateForm(field: keyof MenuFormState, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function beginCreate() {
    setIsCreating(true);
    setSelectedItemId(null);
    setNotice("");
    setForm(buildEmptyForm(categories[0]?.id ?? ""));
  }

  function beginEdit(item: AdminMenuItem) {
    setIsCreating(false);
    setSelectedItemId(item.id);
    setNotice("");
    setForm(buildFormFromItem(item));
  }

  async function toggleAvailability(item: AdminMenuItem) {
    setError(null);
    setNotice("");

    try {
      const updatedItem = await updateAdminMenuItemAvailability(item.id, !item.isAvailable);
      setItems((currentItems) =>
        currentItems.map((currentItem) =>
          currentItem.id === updatedItem.id ? updatedItem : currentItem,
        ),
      );
      if (selectedItemId === updatedItem.id) {
        setForm(buildFormFromItem(updatedItem));
      }
      setNotice(`${updatedItem.name} đã được cập nhật trạng thái.`);
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "Không cập nhật được trạng thái món.");
    }
  }

  async function saveMenuItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice("");

    if (!form.name.trim() || !form.categoryId || Number(form.price) <= 0) {
      setError("Vui lòng nhập tên món, danh mục và giá bán hợp lệ.");
      return;
    }

    setIsSaving(true);

    try {
      const input = toMenuInput(form);
      const savedItem =
        isCreating || !selectedItem
          ? await createAdminMenuItem(input)
          : await updateAdminMenuItem(selectedItem.id, input);

      setItems((currentItems) => {
        const exists = currentItems.some((item) => item.id === savedItem.id);
        return exists
          ? currentItems.map((item) => (item.id === savedItem.id ? savedItem : item))
          : [...currentItems, savedItem];
      });
      setSelectedItemId(savedItem.id);
      setIsCreating(false);
      setForm(buildFormFromItem(savedItem));
      setNotice(`${savedItem.name} đã được lưu qua API.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Không lưu được món.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <AdminStatePanel
        title="Đang tải thực đơn"
        description="Đang lấy danh mục và món ăn từ backend."
      />
    );
  }

  if (error && items.length === 0) {
    return <AdminStatePanel title="Có lỗi dữ liệu" description={error} />;
  }

  return (
    <div className="admin-workspace">
      <section className="admin-toolbar">
        <div>
          <span className="panel-kicker">Menu control</span>
          <h3>{items.length} món trong thực đơn</h3>
          <p>
            {availableCount} món đang bán, {unavailableCount} món tạm hết. Dữ liệu được lấy và cập
            nhật qua API quản trị thực đơn.
          </p>
        </div>
        <div className="admin-toolbar-metrics">
          <span>{categories.length} danh mục</span>
          <span>{visibleItems.length} món đang xem</span>
        </div>
        <button className="button primary" type="button" onClick={beginCreate}>
          + Tạo món
        </button>
      </section>

      {notice ? <p className="admin-status admin-status-ready">{notice}</p> : null}
      {error ? <p className="admin-status admin-status-alert">{error}</p> : null}

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
            <span className="admin-status admin-status-ready">API-ready</span>
          </div>

          {visibleItems.length === 0 ? (
            <AdminStatePanel
              title="Không có món phù hợp"
              description="Thử chọn danh mục khác hoặc tạo món mới."
            />
          ) : (
            <div className="admin-menu-table">
              {visibleItems.map((item) => (
                <article className="admin-menu-row" key={item.id}>
                  <img alt={item.name} src={item.imageUrl} />
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
                    <button type="button" onClick={() => toggleAvailability(item)}>
                      {item.isAvailable ? "Tạm hết" : "Mở bán"}
                    </button>
                    <button type="button" onClick={() => beginEdit(item)}>
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
          <p>
            Form này gửi trực tiếp lên API quản trị thực đơn. Thay đổi thành công sẽ cập nhật lại
            danh sách đang hiển thị.
          </p>
          <form className="admin-form" onSubmit={saveMenuItem}>
            <label>
              Tên món
              <input
                onChange={(event) => updateForm("name", event.target.value)}
                placeholder="Nhập tên món"
                value={form.name}
              />
            </label>
            <label>
              Danh mục
              <select
                onChange={(event) => updateForm("categoryId", event.target.value)}
                value={form.categoryId}
              >
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
                inputMode="numeric"
                onChange={(event) => updateForm("price", event.target.value)}
                placeholder="65000"
                value={form.price}
              />
            </label>
            <label>
              Ảnh món
              <input
                onChange={(event) => updateForm("imageUrl", event.target.value)}
                placeholder="https://..."
                value={form.imageUrl}
              />
            </label>
            <label>
              Mô tả
              <textarea
                onChange={(event) => updateForm("description", event.target.value)}
                placeholder="Mô tả ngắn cho khách và admin"
                value={form.description}
              />
            </label>
            <label>
              Tags
              <input
                onChange={(event) => updateForm("tags", event.target.value)}
                placeholder="fresh, lunch, spicy"
                value={form.tags}
              />
            </label>
            <label className="admin-check-row">
              <input
                checked={form.isAvailable}
                onChange={(event) => updateForm("isAvailable", event.target.checked)}
                type="checkbox"
              />
              Hiển thị là còn món
            </label>
            <button className="button primary" disabled={isSaving} type="submit">
              {isSaving ? "Đang lưu..." : isCreating ? "Lưu món mới" : "Lưu thay đổi"}
            </button>
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
