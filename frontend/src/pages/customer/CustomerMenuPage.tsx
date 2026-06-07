import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CustomerCartBar } from "../../components/customer/CustomerCartBar";
import { TableContextBadge } from "../../components/customer/TableContextBadge";
import {
  loadMenuCart,
  saveOrderContext,
  saveMenuCart,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import { MenuCategoryTabs } from "../../components/menu/MenuCategoryTabs";
import { MenuItemCard, formatVnd } from "../../components/menu/MenuItemCard";
import { getCustomerMenu } from "../../services/menuService";
import type { MenuCart } from "../../types";

type CustomerMenuPageProps = {
  tableCode?: string;
};

const customerMenu = getCustomerMenu();
const menuItems = customerMenu.items;
const menuCategories = ["Tất cả", ...customerMenu.categories.map((category) => category.name)];

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function getCartSummary(cart: MenuCart) {
  return menuItems.reduce(
    (summary, item) => {
      const quantity = cart[item.id] ?? 0;
      return {
        itemCount: summary.itemCount + quantity,
        totalPrice: summary.totalPrice + quantity * item.price,
      };
    },
    { itemCount: 0, totalPrice: 0 },
  );
}

export function CustomerMenuPage({ tableCode }: CustomerMenuPageProps) {
  const [selectedCategory, setSelectedCategory] = useState("Tất cả");
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<MenuCart>(getInitialCart);

  useEffect(() => {
    if (tableCode) {
      saveOrderContext({ tableCode });
    }
  }, [tableCode]);

  const filteredItems = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return menuItems.filter((item) => {
      const matchesCategory =
        selectedCategory === "Tất cả" || item.categoryName === selectedCategory;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        [item.name, item.description, item.categoryName, ...item.tags]
          .join(" ")
          .toLowerCase()
          .includes(normalizedSearch);

      return matchesCategory && matchesSearch;
    });
  }, [search, selectedCategory]);

  const featuredItems = menuItems.filter((item) => item.isAvailable).slice(0, 6);
  const summary = getCartSummary(cart);

  function updateCart(nextCart: MenuCart) {
    setCart(nextCart);
    saveMenuCart(nextCart);
  }

  function addItem(itemId: string) {
    const item = menuItems.find((menuItem) => menuItem.id === itemId);
    if (!item?.isAvailable) {
      return;
    }

    updateCart({ ...cart, [itemId]: (cart[itemId] ?? 0) + 1 });
  }

  function removeItem(itemId: string) {
    const nextQuantity = (cart[itemId] ?? 0) - 1;
    const nextCart = { ...cart };

    if (nextQuantity <= 0) {
      delete nextCart[itemId];
    } else {
      nextCart[itemId] = nextQuantity;
    }

    updateCart(nextCart);
  }

  return (
    <section className="cmc-customer-page">
      <header className="cmc-hero">
        <div>
          <p className="cmc-kicker">CMC Restaurant</p>
          <h2>
            Ẩm thực Việt Nam <span>tinh tế & đậm đà</span>
          </h2>
          <p>
            Quét mã QR tại bàn để xem thực đơn, chọn món, xác nhận giỏ hàng và
            theo dõi trạng thái phục vụ ngay trên điện thoại.
          </p>
          <div className="cmc-hero-actions">
            <a className="cmc-primary-link" href="#cmc-menu-list">
              Xem thực đơn
            </a>
            <Link className="cmc-secondary-link" to="/chat">
              Hỏi AI gợi ý món
            </Link>
          </div>
        </div>
        <div className="cmc-hero-collage" aria-label="Featured dishes">
          <img alt="Bò lúc lắc" src={menuItems[5].imageUrl} />
          <img alt="Phở bò đặc biệt" src={menuItems[4].imageUrl} />
          <img alt="Trà đào cam sả" src={menuItems[10].imageUrl} />
        </div>
      </header>

      <section className="cmc-home-flow" aria-label="Customer order journey">
        <div className="cmc-section-title">
          <h3>Luồng gọi món dành cho khách</h3>
          <span>{tableCode ? `Bàn ${tableCode}` : "QR / Pickup"}</span>
        </div>
        <div className="cmc-home-steps">
          <article className="cmc-step-card">
            <span>Bước 1</span>
            <h3>Quét QR hoặc chọn mang về</h3>
            <p>
              Mã bàn được giữ xuyên suốt giỏ hàng để bếp biết đúng vị trí phục vụ.
            </p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 2</span>
            <h3>Chọn món và xác nhận giỏ</h3>
            <p>
              Món hết hàng được khóa trước khi đặt, tránh gửi đơn sai cho bếp.
            </p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 3</span>
            <h3>Theo dõi trạng thái món</h3>
            <p>
              Sau khi gửi đơn, khách có thể mở trang tracking và xem cập nhật realtime.
            </p>
          </article>
        </div>
      </section>

      <section className="cmc-menu-toolbar" aria-label="Menu filters">
        <TableContextBadge tableCode={tableCode} />
        <div className="cmc-search-row">
          <input
            className="cmc-search-input"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Tìm món ăn, đồ uống, hải sản..."
            type="search"
            value={search}
          />
          <span className="cmc-result-count">{filteredItems.length} món</span>
        </div>
        <MenuCategoryTabs
          categories={menuCategories}
          onSelectCategory={setSelectedCategory}
          selectedCategory={selectedCategory}
        />
      </section>

      {search.trim().length === 0 && selectedCategory === "Tất cả" ? (
        <section className="cmc-featured-strip" aria-label="Featured menu items">
          <div className="cmc-section-title">
            <h3>Gợi ý hôm nay</h3>
            <span>{featuredItems.length} món nổi bật</span>
          </div>
          <div className="cmc-featured-list">
            {featuredItems.map((item) => (
              <article className="cmc-featured-card" key={item.id}>
                <img alt={item.name} src={item.imageUrl} />
                <div>
                  <h4>{item.name}</h4>
                  <p>{formatVnd(item.price)}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <div className="cmc-menu-layout">
        <section className="cmc-menu-grid" id="cmc-menu-list">
          {filteredItems.map((item) => (
            <MenuItemCard
              item={item}
              key={item.id}
              onAdd={addItem}
              onRemove={removeItem}
              quantity={cart[item.id] ?? 0}
            />
          ))}
          {filteredItems.length === 0 ? (
            <div className="cmc-empty-state">
              Không tìm thấy món phù hợp. Hãy thử danh mục hoặc từ khóa khác.
            </div>
          ) : null}
        </section>

        <aside className="cmc-cart-panel side" aria-label="Cart summary">
          <h3>Giỏ hàng</h3>
          <p>Kiểm tra nhanh số lượng và tổng tiền trước khi sang bước xác nhận.</p>
          <div className="cmc-cart-list">
            {menuItems
              .filter((item) => (cart[item.id] ?? 0) > 0)
              .map((item) => (
                <div className="cmc-cart-row" key={item.id}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>x{cart[item.id]}</span>
                  </div>
                  <strong>{formatVnd((cart[item.id] ?? 0) * item.price)}</strong>
                </div>
              ))}
            {summary.itemCount === 0 ? <p>Chưa có món nào trong giỏ.</p> : null}
          </div>
          <div className="cmc-cart-total">
            <span>Tổng cộng</span>
            <strong>{formatVnd(summary.totalPrice)}</strong>
          </div>
          {tableCode ? <TableContextBadge tableCode={tableCode} /> : null}
          <Link className="cmc-secondary-link" to="/cart">
            Xem giỏ & đặt món
          </Link>
        </aside>
      </div>

      <CustomerCartBar itemCount={summary.itemCount} totalPrice={summary.totalPrice} />
    </section>
  );
}

