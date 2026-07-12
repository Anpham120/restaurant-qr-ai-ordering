import { useEffect, useMemo, useState } from "react";
import { MenuCategoryTabs } from "../../components/menu/MenuCategoryTabs";
import { MenuItemCard } from "../../components/menu/MenuItemCard";
import "../../components/customer/customer-menu.css";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../../services/menuService";

const ALL_CATEGORY = "Tất cả";
const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

export function PublicMenuPreviewPage() {
  const [menu, setMenu] = useState(initialMenu);
  const [selectedCategory, setSelectedCategory] = useState(ALL_CATEGORY);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetchCustomerMenu()
      .then((result) => { if (active) setMenu(result); })
      .catch(() => { if (active) setError("Không tải được thực đơn. Vui lòng thử lại sau."); })
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
  const heroItems = menu.items.filter((item) => item.isAvailable && item.imageUrl).slice(0, 3);

  return (
    <section className="cmc-customer-page">
      <header className="cmc-hero cmc-menu-hero">
        <div className="cmc-menu-hero-copy">
          <p className="cmc-kicker">CMC Restaurant</p>
          <h2>Thực đơn <span>nhà hàng</span></h2>
          <p>Xem trước món ăn và giá hiện tại. Quét QR trên bàn khi bạn muốn gọi món.</p>
          <div className="cmc-hero-actions"><a className="cmc-primary-link" href="#cmc-menu-list">Xem thực đơn</a></div>
        </div>
        {heroItems.length > 0 ? (
          <div className="cmc-hero-collage" aria-label="Món nổi bật">
            {heroItems.map((item) => <img alt={item.name} key={item.id} src={item.imageUrl} />)}
          </div>
        ) : null}
      </header>

      <section className="cmc-menu-toolbar" aria-label="Bộ lọc thực đơn">
        {error ? <p className="cmc-inline-error" role="alert">{error}</p> : null}
        <span className="cmc-table-badge muted">Thực đơn xem trước · không tạo giỏ hàng</span>
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

      <section className="cmc-menu-sections" id="cmc-menu-list" aria-busy={loading} aria-labelledby="preview-menu-title">
        <div className="cmc-section-title cmc-menu-master-title">
          <div><p>Xem trước</p><h3 id="preview-menu-title">Món đang phục vụ</h3></div>
          <span>{filteredItems.length} món</span>
        </div>
        {loading ? <p>Đang tải thực đơn…</p> : null}
        {!loading && !error && filteredItems.length === 0 ? <p>Không tìm thấy món phù hợp.</p> : null}
        {!loading ? (
          <div className="cmc-menu-grid">
            {filteredItems.map((item) => <MenuItemCard item={item} key={item.id} readOnly />)}
          </div>
        ) : null}
      </section>
    </section>
  );
}
