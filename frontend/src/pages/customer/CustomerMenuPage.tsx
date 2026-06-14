import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CustomerCartBar } from "../../components/customer/CustomerCartBar";
import { TableContextBadge } from "../../components/customer/TableContextBadge";
import {
  loadMenuCart,
  saveMenuCart,
  saveOrderContext,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import { MenuCategoryTabs } from "../../components/menu/MenuCategoryTabs";
import { MenuItemCard, formatVnd } from "../../components/menu/MenuItemCard";
import { getCustomerMenu, type CustomerMenuCategory } from "../../services/menuService";
import type { MenuCart, MenuItem } from "../../types";

type CustomerMenuPageProps = {
  tableCode?: string;
};

const allCategory = "Tất cả";

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function getCartSummary(cart: MenuCart, menuItems: MenuItem[]) {
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
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [menuCategories, setMenuCategories] = useState<CustomerMenuCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState(allCategory);
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (tableCode) {
      saveOrderContext({ tableCode });
    }
  }, [tableCode]);

  useEffect(() => {
    let isMounted = true;

    setIsLoading(true);
    setErrorMessage("");

    getCustomerMenu()
      .then((menu) => {
        if (!isMounted) {
          return;
        }

        setMenuItems(menu.items);
        setMenuCategories(menu.categories);
      })
      .catch((error) => {
        if (isMounted) {
          setErrorMessage(error instanceof Error ? error.message : "Không tải được thực đơn.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const categoryNames = useMemo(
    () => [allCategory, ...menuCategories.map((category) => category.name)],
    [menuCategories],
  );

  const filteredItems = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return menuItems.filter((item) => {
      const matchesCategory = selectedCategory === allCategory || item.categoryName === selectedCategory;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        [item.name, item.description, item.categoryName, ...item.tags]
          .join(" ")
          .toLowerCase()
          .includes(normalizedSearch);

      return matchesCategory && matchesSearch;
    });
  }, [menuItems, search, selectedCategory]);

  const featuredItems = menuItems.filter((item) => item.isAvailable).slice(0, 6);
  const heroImages = featuredItems.slice(0, 3);
  const summary = getCartSummary(cart, menuItems);

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
            Gọi món nhanh <span>theo đúng luồng nhà hàng</span>
          </h2>
          <p>
            Quét mã QR tại bàn hoặc chọn mang về, xem thực đơn đang bán, xác nhận giỏ hàng và
            theo dõi trạng thái phục vụ trên điện thoại.
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
        {heroImages.length > 0 ? (
          <div className="cmc-hero-collage" aria-label="Món nổi bật">
            {heroImages.map((item) => (
              <img alt={item.name} key={item.id} src={item.imageUrl} />
            ))}
          </div>
        ) : null}
      </header>

      <section className="cmc-home-flow" aria-label="Luồng gọi món">
        <div className="cmc-section-title">
          <h3>Luồng gọi món dành cho khách</h3>
          <span>{tableCode ? `Bàn ${tableCode}` : "QR / mang về"}</span>
        </div>
        <div className="cmc-home-steps">
          <article className="cmc-step-card">
            <span>Bước 1</span>
            <h3>Vào đúng ngữ cảnh</h3>
            <p>Mã bàn từ QR được giữ trong giỏ hàng để bếp và nhân viên biết đúng vị trí phục vụ.</p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 2</span>
            <h3>Chọn món đang bán</h3>
            <p>Thực đơn lấy từ backend, món tạm hết sẽ không được gửi vào đơn.</p>
          </article>
          <article className="cmc-step-card">
            <span>Bước 3</span>
            <h3>Theo dõi đơn</h3>
            <p>Sau khi gửi đơn, khách mở trang trạng thái để biết món đang chờ, đang nấu hay sẵn sàng.</p>
          </article>
        </div>
      </section>

      <section className="cmc-menu-toolbar" aria-label="Bộ lọc thực đơn">
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
          categories={categoryNames}
          onSelectCategory={setSelectedCategory}
          selectedCategory={selectedCategory}
        />
      </section>

      {isLoading ? <div className="cmc-empty-state">Đang tải thực đơn...</div> : null}
      {errorMessage ? <div className="cmc-empty-state">{errorMessage}</div> : null}

      {!isLoading && !errorMessage && search.trim().length === 0 && selectedCategory === allCategory ? (
        <section className="cmc-featured-strip" aria-label="Món gợi ý">
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

      {!isLoading && !errorMessage ? (
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

          <aside className="cmc-cart-panel side" aria-label="Tóm tắt giỏ hàng">
            <h3>Giỏ hàng</h3>
            <p>Kiểm tra nhanh số lượng và tổng tiền trước khi xác nhận đặt món.</p>
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
              Xem giỏ và đặt món
            </Link>
          </aside>
        </div>
      ) : null}

      <CustomerCartBar itemCount={summary.itemCount} totalPrice={summary.totalPrice} />
    </section>
  );
}
