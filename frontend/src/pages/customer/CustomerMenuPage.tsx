import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { CustomerTestimonials } from "../../components/customer/CustomerTestimonials";
import { CustomerWhyChooseUs } from "../../components/customer/CustomerWhyChooseUs";
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

type MenuSection = {
  name: string;
  items: MenuItem[];
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

function buildMenuSections(menu: CustomerMenuResponse, items: MenuItem[]): MenuSection[] {
  const categoryNames = menu.categories.map((category) => category.name);
  const knownCategoryNames = new Set(categoryNames);
  const orderedNames = [
    ...categoryNames,
    ...Array.from(new Set(items.map((item) => item.categoryName))).filter(
      (categoryName) => !knownCategoryNames.has(categoryName),
    ),
  ];

  return orderedNames
    .map((name) => ({
      name,
      items: items.filter((item) => item.categoryName === name),
    }))
    .filter((section) => section.items.length > 0);
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
      setSessionNotice("Bạn có thể xem thực đơn. Để đặt món, vui lòng quét QR tại bàn.");
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
        setSessionNotice("Phiên bàn đã hết hạn. Bạn vẫn có thể xem thực đơn, nhưng cần quét lại QR để đặt món.");
      } else if (result.status === "invalid") {
        setIsSessionOpen(false);
        setSessionNotice("Mã QR không hợp lệ cho bàn này. Bạn vẫn có thể xem thực đơn, nhưng cần quét lại QR để đặt món.");
      } else {
        setIsSessionOpen(false);
        setSessionNotice("Chưa thể mở phiên bàn. Bạn vẫn có thể xem thực đơn và gọi nhân viên hỗ trợ khi cần đặt món.");
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

  const menuSections = useMemo(
    () => buildMenuSections(customerMenu, filteredItems),
    [customerMenu, filteredItems],
  );
  const isFilteredView = search.trim().length > 0 || selectedCategory !== ALL_CATEGORY;
  const featuredItems = menuItems.filter((item) => item.isAvailable).slice(0, 4);
  const summary = getCartSummary(cart, menuItems);
  const heroItems = featuredItems.length >= 3 ? featuredItems : menuItems.slice(0, 3);

  function updateCart(nextCart: MenuCart) {
    setCart(nextCart);
    saveMenuCart(nextCart);
  }

  function addItem(itemId: string) {
    if (!isSessionOpen) {
      setSessionNotice("Bạn cần quét QR tại bàn để thêm món vào giỏ.");
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
    <section className={`cmc-customer-page${summary.itemCount > 0 ? " has-cart-bar" : ""}`}>
      <header className="cmc-hero cmc-menu-hero">
        <div className="cmc-menu-hero-copy">
          <p className="cmc-kicker">CMC Restaurant</p>
          <h2>
            Thực đơn <span>{tableCode ? `Bàn ${tableCode}` : "nhà hàng"}</span>
          </h2>
          <p>
            Khám phá hương vị đặc biệt từ những món ăn được chế biến tươi ngon mỗi ngày.
            Chọn món yêu thích và gửi đơn trực tiếp từ điện thoại.
          </p>
          <div className="cmc-hero-actions">
            <a className="cmc-primary-link" href="#cmc-menu-sections">
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
        {tableCode ? (
          <span className="cmc-table-badge">Bàn {tableCode} · QR dine-in</span>
        ) : (
          <span className="cmc-table-badge muted">Khách chọn món tại nhà hàng hoặc đặt online</span>
        )}
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

      {/* WhyChooseUs, Testimonials, and CTA sections are shown when not filtered */}

      <div className="cmc-menu-layout">
        <section
          className="cmc-menu-sections"
          id="cmc-menu-sections"
          aria-busy={isLoading}
          aria-labelledby="cmc-table-menu-title"
        >
          <div className="cmc-section-title cmc-menu-master-title">
            <div>
              <p>Thực đơn QR bàn</p>
              <h3 id="cmc-table-menu-title">
                {tableCode ? `Thực đơn bàn ${tableCode}` : "Thực đơn nhà hàng"}
              </h3>
            </div>
            <span>{filteredItems.length} món</span>
          </div>

          {isLoading ? (
            <div className="cmc-menu-grid" id="cmc-menu-list">
              {Array.from({ length: 6 }).map((_, index) => (
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
              ))}
            </div>
          ) : (
            <>
              {menuSections.map((section) => (
                <section className="cmc-menu-category-section" key={section.name}>
                  <header className="cmc-menu-category-heading">
                    <div>
                      <p>Danh mục</p>
                      <h4>{section.name}</h4>
                    </div>
                    <span>{section.items.length} món</span>
                  </header>
                  <div className="cmc-menu-grid" id={section.name === menuSections[0]?.name ? "cmc-menu-list" : undefined}>
                    {section.items.map((item) => (
                      <MenuItemCard
                        item={item}
                        key={item.id}
                        onAdd={addItem}
                        onRemove={removeItem}
                        quantity={cart[item.id] ?? 0}
                      />
                    ))}
                  </div>
                </section>
              ))}
              {filteredItems.length === 0 ? (
                <div className="cmc-empty-state">
                  Không tìm thấy món phù hợp. Hãy thử danh mục hoặc từ khóa khác.
                </div>
              ) : null}
            </>
          )}
        </section>
      </div>

      {/* Giỏ hàng nổi toàn cục được mount ở CustomerLayout (main.tsx) */}

      {!isFilteredView && (
        <>
          <CustomerWhyChooseUs />
          <CustomerTestimonials menuItems={menuItems} />
          <section className="vian-cta-section">
            <div className="vian-cta-content">
              <h2>Bạn đã sẵn sàng đặt món?</h2>
              <p>
                Khám phá thực đơn đa dạng của chúng tôi và đặt món ngay hôm nay.
                Đội ngũ đầu bếp luôn sẵn sàng chế biến những món ăn ngon nhất cho bạn.
              </p>
              <a className="vian-cta-button" href="#cmc-menu-sections">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="20" height="20">
                  <path d="M3 3h18v18H3V3z" />
                  <path d="M3 9h18M9 21V9" />
                </svg>
                Xem thực đơn
              </a>
            </div>
          </section>
        </>
      )}
    </section>
  );
}
