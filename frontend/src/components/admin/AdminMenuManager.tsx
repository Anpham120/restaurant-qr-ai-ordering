import { useEffect, useMemo, useState } from "react";
import { getAdminMenuOverview } from "../../services/adminMenuService";
import type { AdminMenuCategory, AdminMenuItem } from "../../types";
import { AdminStatePanel } from "./AdminStatePanel";
import { AdminStatusBadge } from "./AdminStatusBadge";

const formatCurrency = (value: number) => `${value.toLocaleString("vi-VN")}đ`;

export function AdminMenuManager() {
  const [items, setItems] = useState<AdminMenuItem[]>([]);
  const [categories, setCategories] = useState<AdminMenuCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminMenuOverview()
      .then((overview) => {
        setItems(overview.items);
        setCategories(overview.categories);
        setSelectedItemId(overview.items[0]?.id ?? null);
      })
      .catch(() => setError("Không tải được dữ liệu thực đơn mẫu."))
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

  const toggleAvailability = (itemId: string) => {
    setItems((currentItems) =>
      currentItems.map((item) =>
        item.id === itemId ? { ...item, isAvailable: !item.isAvailable } : item,
      ),
    );
  };

  if (isLoading) {
    return <AdminStatePanel title="Đang tải thực đơn" description="Chuẩn bị dữ liệu món ăn mẫu." />;
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
            {availableCount} món đang bán, {unavailableCount} món tạm hết. Dữ liệu dùng cùng shape
            với menu contract.
          </p>
        </div>
        <button className="button primary" type="button" onClick={() => setIsCreating(true)}>
          + Tạo món
        </button>
      </section>

      <section className="admin-category-strip" aria-label="Lọc danh mục">
        <button
          className={selectedCategory === "all" ? "admin-chip active" : "admin-chip"}
          type="button"
          onClick={() => setSelectedCategory("all")}
        >
          Tất cả
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
                    <button type="button" onClick={() => toggleAvailability(item.id)}>
                      {item.isAvailable ? "Tạm hết" : "Mở bán"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setIsCreating(false);
                        setSelectedItemId(item.id);
                      }}
                    >
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
          <form className="admin-form">
            <label>
              Tên món
              <input defaultValue={isCreating ? "" : selectedItem?.name} placeholder="Nhập tên món" />
            </label>
            <label>
              Danh mục
              <select defaultValue={isCreating ? categories[0]?.id : selectedItem?.categoryId}>
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
                defaultValue={isCreating ? "" : selectedItem?.price}
                inputMode="numeric"
                placeholder="65000"
              />
            </label>
            <label>
              Mô tả
              <textarea
                defaultValue={isCreating ? "" : selectedItem?.description}
                placeholder="Mô tả ngắn cho khách và admin"
              />
            </label>
            <label className="admin-check-row">
              <input
                defaultChecked={isCreating ? true : selectedItem?.isAvailable}
                type="checkbox"
              />
              Hiển thị là còn món
            </label>
            <button className="button primary" type="button">
              {isCreating ? "Lưu món mới" : "Lưu thay đổi"}
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
