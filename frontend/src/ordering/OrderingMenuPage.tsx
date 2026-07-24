import { useEffect, useMemo, useState } from "react";
import { useI18n } from "@cmc/i18n";
import { localizeMenuCategory, localizeMenuItem } from "@cmc/i18n/menu";
import { Link } from "react-router-dom";
import {
  applyCartDelta,
  CART_UPDATED_EVENT,
  loadMenuCart,
  reconcileCartOnLoad,
} from "../components/customer/customerMenuStorage";
import "../components/customer/customer-menu.css";
import { MenuCategoryTabs } from "../components/menu/MenuCategoryTabs";
import { MenuItemCard } from "../components/menu/MenuItemCard";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../services/menuService";
import { formatCartErrorMessage } from "../services/cartService";
import { getTableInvoice, getTableSessionOrders } from "../services/orderService";
import type { MenuCart } from "../types";
import type { TableSessionResumeState } from "@cmc/shared-types";
import { useOrderingSession } from "./OrderingSessionProvider";
import { deriveSessionHubState } from "./sessionResumeState";

type SessionHubState = Exclude<TableSessionResumeState, "CartPending">;

const ALL_CATEGORY = "__all";
const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

function getInitialCart(): MenuCart {
  return typeof window === "undefined" ? {} : loadMenuCart();
}

export function OrderingMenuPage() {
  const { formatMoney, locale, t } = useI18n();
  const { context } = useOrderingSession();
  const [menu, setMenu] = useState(initialMenu);
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [selectedCategory, setSelectedCategory] = useState(ALL_CATEGORY);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hubState, setHubState] = useState<SessionHubState>("New");

  useEffect(() => {
    let active = true;
    void Promise.all([
      getTableSessionOrders(context.sessionId, context.sessionToken),
      getTableInvoice(context.sessionId, context.sessionToken),
    ])
      .then(([orders, invoice]) => {
        if (!active) return;
        setHubState(deriveSessionHubState(orders.map((order) => order.status), invoice?.status ?? null));
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [context.sessionId, context.sessionToken]);

  useEffect(() => {
    let active = true;
    fetchCustomerMenu()
      .then((result) => { if (active) setMenu(result); })
      .catch(() => { if (active) setError(t("Không tải được thực đơn. Hãy thử lại.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [t]);

  useEffect(() => {
    let active = true;
    void reconcileCartOnLoad()
      .then((nextCart) => {
        if (active) {
          setCart(nextCart);
        }
      })
      .catch(() => undefined);

    const handleCartUpdated = () => {
      setCart(loadMenuCart());
    };

    window.addEventListener(CART_UPDATED_EVENT, handleCartUpdated);
    return () => {
      active = false;
      window.removeEventListener(CART_UPDATED_EVENT, handleCartUpdated);
    };
  }, []);

  const categories = useMemo(
    () => [
      { id: ALL_CATEGORY, label: t("Tất cả") },
      ...menu.categories.map((category) => ({
        id: category.categoryId,
        label: localizeMenuCategory(category.categoryId, category.name, locale),
      })),
    ],
    [locale, menu.categories, t],
  );
  const filteredItems = useMemo(() => {
    const query = search.trim().toLocaleLowerCase(locale === "vi" ? "vi-VN" : "en-US");
    const categoryIdByName = new Map(menu.categories.map((category) => [category.name, category.categoryId]));
    return menu.items.filter((item) => {
      const matchesCategory = selectedCategory === ALL_CATEGORY || categoryIdByName.get(item.categoryName) === selectedCategory;
      return matchesCategory;
    }).map((item) => localizeMenuItem(item, locale)).filter((item) => {
      const matchesSearch = !query || `${item.name} ${item.description}`.toLocaleLowerCase(locale === "vi" ? "vi-VN" : "en-US").includes(query);
      return matchesSearch;
    });
  }, [locale, menu.categories, menu.items, search, selectedCategory]);
  const summary = useMemo(() => menu.items.reduce(
    (value, item) => {
      const quantity = cart[item.id] ?? 0;
      return { count: value.count + quantity, total: value.total + quantity * item.price };
    },
    { count: 0, total: 0 },
  ), [cart, menu.items]);

  function updateQuantity(itemId: string, delta: number) {
    void applyCartDelta(itemId, delta)
      .then((next) => {
        setError("");
        setCart(next);
        // #region agent log
        fetch('http://127.0.0.1:7639/ingest/45c610dd-1025-4f92-a068-a057f791be7f',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'613762'},body:JSON.stringify({sessionId:'613762',runId:'prod-ops',hypothesisId:'H-CART',location:'OrderingMenuPage.tsx:updateQuantity',message:'cart updated',data:{itemId,delta,itemCount:Object.values(next).reduce((s,q)=>s+q,0),sessionId:context.sessionId},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
      })
      .catch((error) => {
        const msg = formatCartErrorMessage(error, t("Không cập nhật được giỏ hàng. Vui lòng thử lại."));
        // #region agent log
        fetch('http://127.0.0.1:7639/ingest/45c610dd-1025-4f92-a068-a057f791be7f',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'613762'},body:JSON.stringify({sessionId:'613762',runId:'prod-ops',hypothesisId:'H-CART',location:'OrderingMenuPage.tsx:updateQuantity',message:'cart update failed',data:{itemId,delta,error:msg,sessionId:context.sessionId},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        setError(msg);
      });
  }

  return (
    <section className="cmc-customer-page ordering-menu-page">
      <section className="cmc-menu-toolbar" aria-label={t("Chọn món")}>
        <span className="cmc-table-badge">{t("Bàn {table}", { table: context.tableCode })}</span>
        {hubState === "ReadyForPayment" || hubState === "PaymentPending" ? (
          <p className="cmc-inline-notice" role="status">
            {t("Bàn sẵn sàng thanh toán. Bạn vẫn có thể gọi thêm món trước khi thanh toán.")}{" "}
            <Link to="../orders?focus=invoice">{t("Thanh toán hóa đơn")}</Link>
          </p>
        ) : null}
        {error ? <p className="cmc-inline-error" role="alert">{error}</p> : null}
        <div className="cmc-search-row">
          <input
            className="cmc-search-input"
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t("Tìm món ăn, đồ uống...")}
            type="search"
            value={search}
          />
          <span className="cmc-result-count">{t("{count} món", { count: filteredItems.length })}</span>
        </div>
        <MenuCategoryTabs
          categories={categories}
          onSelectCategory={setSelectedCategory}
          selectedCategory={selectedCategory}
        />
      </section>

      <section className="cmc-menu-sections" aria-busy={loading} aria-labelledby="ordering-menu-title">
        <div className="cmc-section-title cmc-menu-master-title">
          <div><p>{t("Gọi món tại bàn")}</p><h1 id="ordering-menu-title">{t("Chọn món")}</h1></div>
          {summary.count > 0 ? <Link to="../cart">{t("{count} món", { count: summary.count })} · {formatMoney(summary.total)}</Link> : null}
        </div>
        {loading ? <p>{t("Đang tải thực đơn…")}</p> : null}
        {!loading && !error && filteredItems.length === 0 ? <p>{t("Không tìm thấy món phù hợp.")}</p> : null}
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

      {summary.count > 0 ? (
        <Link
          aria-label={t("Xem giỏ hàng gồm {count} món, tổng {total}", { count: summary.count, total: formatMoney(summary.total) })}
          className="ordering-cart-dock"
          to="../cart"
        >
          <span className="ordering-cart-dock-count">
            <strong>{summary.count} món</strong>
            <small>{t("Đã chọn")}</small>
          </span>
          <strong className="ordering-cart-dock-total" data-money>{formatMoney(summary.total)}</strong>
          <span className="ordering-cart-dock-action">{t("Xem giỏ")}</span>
        </Link>
      ) : null}
    </section>
  );
}
