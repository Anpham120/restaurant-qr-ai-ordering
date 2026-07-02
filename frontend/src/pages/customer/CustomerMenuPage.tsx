import { useEffect, useMemo, useState } from "react";
import "@fontsource/newsreader/latin-500.css";
import "@fontsource/newsreader/vietnamese-500.css";
import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/vietnamese-400.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/vietnamese-700.css";
import { Link } from "react-router-dom";
import { CustomerCartBar } from "../../components/customer/CustomerCartBar";
import { TableContextBadge } from "../../components/customer/TableContextBadge";
import {
  loadMenuCart,
  loadOrderContext,
  saveMenuCart,
  saveOrderContext,
} from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import { MenuCategoryTabs } from "../../components/menu/MenuCategoryTabs";
import { MenuItemCard, formatVnd } from "../../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../../services/menuService";
import { openDineInSession } from "../../services/tableSessionService";
import type { MenuCart, MenuItem } from "../../types";

type CustomerMenuPageProps = {
  tableCode?: string;
  qrToken?: string;
};

const ALL_CATEGORY = "Tất cả";
const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function hasStoredSession(tableCode?: string, qrToken?: string) {
  if (typeof window === "undefined" || !tableCode || !qrToken) {
    return false;
  }

  const context = loadOrderContext();
  return Boolean(
    context.tableCode === tableCode && context.qrToken === qrToken && context.sessionId,
  );
}

function getCartSummary(cart: MenuCart, items: MenuItem[]) {
  return items.reduce(
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

export function CustomerMenuPage({ tableCode, qrToken }: CustomerMenuPageProps) {
  const [customerMenu, setCustomerMenu] = useState(initialMenu);
  const [selectedCategory, setSelectedCategory] = useState(ALL_CATEGORY);
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [menuError, setMenuError] = useState("");
  const [sessionNotice, setSessionNotice] = useState("");
  const [isSessionOpen, setIsSessionOpen] = useState(() => hasStoredSession(tableCode, qrToken));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    fetchCustomerMenu()
      .then((menu) => {
        if (isMounted) {
          setCustomerMenu(menu);
        }
      })
      .catch(() => {
        if (isMounted) {
          setMenuError("Không tải được thực đơn từ hệ thống.");
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

  useEffect(() => {
    if (!tableCode || !qrToken) {
      setIsSessionOpen(false);
      setSessionNotice("Vui lòng quét QR tại bàn để mở thực đơn.");
      return;
    }

    let isMounted = true;

    openDineInSession(qrToken, tableCode).then((result) => {
      if (!isMounted) {
        return;
      }

      if (result.status === "open") {
        saveOrderContext({ tableCode, qrToken, sessionId: result.session.sessionId });
        setIsSessionOpen(true);
        setSessionNotice("");
      } else if (result.status === "expired") {
        setIsSessionOpen(false);
        setSessionNotice("Phiên bàn đã hết hạn. Vui lòng quét lại QR tại bàn.");
      } else if (result.status === "invalid") {
        setIsSessionOpen(false);
        setSessionNotice("Mã QR không hợp lệ cho bàn này. Vui lòng quét lại QR tại bàn.");
      } else {
        setIsSessionOpen(false);
        setSessionNotice("Chưa thể mở phiên bàn. Vui lòng gọi nhân viên hỗ trợ.");
      }
    });

    return () => {
      isMounted = false;
    };
  }, [tableCode, qrToken]);

  const menuItems = customerMenu.items;
  const menuCategories = useMemo(
    () => [ALL_CATEGORY, ...customerMenu.categories.map((category) => category.name)],
    [customerMenu.categories],
  );

  const filteredItems = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return menuItems.filter((item) => {
      const matchesCategory =
        selectedCategory === ALL_CATEGORY || item.categoryName === selectedCategory;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        [item.name, item.description, item.categoryName, ...item.tags]
          .join(" ")
          .toLowerCase()
          .includes(normalizedSearch);

      return matchesCategory && matchesSearch;
    });
  }, [menuItems, search, selectedCategory]);

  const featuredItems = menuItems.filter((item) => item.isAvailable).slice(0, 4);
  const summary = getCartSummary(cart, menuItems);
  const heroItems = featuredItems.length >= 3 ? featuredItems : menuItems.slice(0, 3);

  function updateCart(nextCart: MenuCart) {
    setCart(nextCart);
    saveMenuCart(nextCart);
  }

  function addItem(itemId: string) {
    if (!isSessionOpen) {
      setSessionNotice("Bạn cần quét QR tại bàn để thêm món.");
      return;
    }

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
      <header className="cmc-hero cmc-menu-hero">
        <div className="cmc-menu-hero-copy">
          <p className="cmc-kicker">CMC Restaurant</p>
          <h2>
            Thực đơn tại bàn <span>{tableCode ? `Bàn ${tableCode}` : "QR"}</span>
          </h2>
          <p>
            Khách chọn món từ phiên QR đang mở tại bàn. Đơn gửi đi sẽ gắn đúng bàn để bếp và nhân viên phục vụ xử lý.
          </p>
          <div className="cmc-hero-actions">
            <a className="cmc-primary-link" href="#cmc-menu-list">
              Xem thực đơn
            </a>
            {tableCode ? <span className="cmc-table-badge">Bàn {tableCode}</span> : null}
          </div>
        </div>
        {heroItems.length > 0 ? (
          <div className="cmc-hero-collage" aria-label="Món nổi bật">
            {heroItems.slice(0, 3).map((item) => (
              <img alt={item.name} key={item.id} src={item.imageUrl} />
            ))}
          </div>
        ) : null}
      </header>

      <section className="cmc-menu-toolbar" aria-label="Bộ lọc thực đơn">
        {menuError ? <p className="cmc-inline-error">{menuError}</p> : null}
        {sessionNotice ? (
          <p className="cmc-inline-error" role="alert">
            {sessionNotice}
          </p>
        ) : null}
        <TableContextBadge tableCode={tableCode} />
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
          categories={menuCategories}
          onSelectCategory={setSelectedCategory}
          selectedCategory={selectedCategory}
        />
      </section>

      {search.trim().length === 0 && selectedCategory === ALL_CATEGORY ? (
        <section className="cmc-featured-strip" aria-label="Món nổi bật hôm nay">
          <div className="cmc-section-title">
            <h3>Món nổi bật</h3>
            <span>{featuredItems.length} món đang bán</span>
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
        <section className="cmc-menu-grid" id="cmc-menu-list" aria-busy={isLoading}>
          {isLoading ? (
            Array.from({ length: 6 }).map((_, index) => (
              <article className="cmc-menu-card cmc-menu-card-skeleton" key={index} aria-hidden="true">
                <div className="cmc-card-image-wrap">
                  <div className="cmc-skel cmc-skel-image anim-shimmer" />
                </div>
                <div className="cmc-card-content">
                  <div className="cmc-skel cmc-skel-line short anim-shimmer" />
                  <div className="cmc-skel cmc-skel-line title anim-shimmer" />
                  <div className="cmc-skel cmc-skel-line anim-shimmer" />
                  <div className="cmc-card-footer">
                    <div className="cmc-skel cmc-skel-price anim-shimmer" />
                    <div className="cmc-skel cmc-skel-button anim-shimmer" />
                  </div>
                </div>
              </article>
            ))
          ) : (
            <>
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
            </>
          )}
        </section>

        <aside className="cmc-cart-panel side" aria-label="Tóm tắt giỏ hàng">
          <h3>Giỏ hàng</h3>
          <p>Kiểm tra món đã chọn trước khi gửi đơn cho bếp.</p>
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
          <Link className="cmc-secondary-link" to="/cart" aria-disabled={!isSessionOpen}>
            Xem giỏ & gửi đơn
          </Link>
        </aside>
      </div>

      <CustomerCartBar itemCount={summary.itemCount} totalPrice={summary.totalPrice} />
    </section>
  );
}
