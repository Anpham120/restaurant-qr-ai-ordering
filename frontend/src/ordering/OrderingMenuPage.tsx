import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  loadMenuCart,
  saveMenuCart,
} from "../components/customer/customerMenuStorage";
import "../components/customer/customer-menu.css";
import { MenuCategoryTabs } from "../components/menu/MenuCategoryTabs";
import { MenuItemCard, formatVnd } from "../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../services/menuService";
import type { MenuCart } from "../types";
import { useOrderingSession } from "./OrderingSessionProvider";

const ALL_CATEGORY = "Tất cả";
const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

function getInitialCart(): MenuCart {
  return typeof window === "undefined" ? {} : loadMenuCart();
}

export function OrderingMenuPage() {
  const { context } = useOrderingSession();
  const [menu, setMenu] = useState(initialMenu);
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [selectedCategory, setSelectedCategory] = useState(ALL_CATEGORY);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchCustomerMenu()
      .then((result) => { if (active) setMenu(result); })
      .catch(() => { if (active) setError("Không tải được thực đơn. Hãy thử lại."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const categories = useMemo(
    () => [ALL_CATEGORY, ...menu.categories.map((category) => category.name)],
    [menu.categories],
  );
  const filteredItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("vi-VN");
    return menu.items.filter((item) => {
      const matchesCategory = selectedCategory === ALL_CATEGORY || item.categoryName === selectedCategory;
      const matchesSearch = !query || `${item.name} ${item.description}`.toLocaleLowerCase("vi-VN").includes(query);
      return matchesCategory && matchesSearch;
    });
  }, [menu.items, search, selectedCategory]);
  const summary = useMemo(() => menu.items.reduce(
    (value, item) => {
      const quantity = cart[item.id] ?? 0;
      return { count: value.count + quantity, total: value.total + quantity * item.price };
    },
    { count: 0, total: 0 },
  ), [cart, menu.items]);

  function updateQuantity(itemId: string, delta: number) {
    setCart((current) => {
      const next = { ...current };
      const quantity = Math.max(0, (next[itemId] ?? 0) + delta);
      if (quantity === 0) delete next[itemId];
      else next[itemId] = quantity;
      saveMenuCart(next);
      return next;
    });
  }

  return (
    <section className="cmc-customer-page ordering-menu-page">
      <section className="cmc-menu-toolbar" aria-label="Chọn món">
        <span className="cmc-table-badge">Bàn {context.tableCode}</span>
        {error ? <p className="cmc-inline-error" role="alert">{error}</p> : null}
        <div className="cmc-search-row">
          <input
            className="cmc-search-input"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Tìm món ăn, đồ uống..."
            type="search"
            value={search}
          />
          <span className="cmc-result-count">{filteredItems.length} món</span>
        </div>
        <MenuCategoryTabs
          categories={categories}
          onSelectCategory={setSelectedCategory}
          selectedCategory={selectedCategory}
        />
      </section>

      <section className="cmc-menu-sections" aria-busy={loading} aria-labelledby="ordering-menu-title">
        <div className="cmc-section-title cmc-menu-master-title">
          <div><p>Gọi món tại bàn</p><h1 id="ordering-menu-title">Chọn món</h1></div>
          {summary.count > 0 ? <Link to="../cart">{summary.count} món · {formatVnd(summary.total)}</Link> : null}
        </div>
        {loading ? <p>Đang tải thực đơn…</p> : null}
        {!loading && !error && filteredItems.length === 0 ? <p>Không tìm thấy món phù hợp.</p> : null}
        {!loading ? (
          <div className="cmc-menu-grid">
            {filteredItems.map((item) => (
              <MenuItemCard
                item={item}
                key={item.id}
                onAdd={(itemId) => updateQuantity(itemId, 1)}
                onRemove={(itemId) => updateQuantity(itemId, -1)}
                quantity={cart[item.id] ?? 0}
              />
            ))}
          </div>
        ) : null}
      </section>
    </section>
  );
}
