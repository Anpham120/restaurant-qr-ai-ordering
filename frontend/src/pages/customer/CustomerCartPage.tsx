import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useI18n } from "@cmc/i18n";
import { localizeMenuItem } from "@cmc/i18n/menu";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, ReceiptText, ShoppingBasket } from "lucide-react";
import { clearMenuCart, applyCartDelta, CART_UPDATED_EVENT, loadMenuCart, reconcileCartOnLoad } from "../../components/customer/customerMenuStorage";
import { formatCartErrorMessage } from "../../services/cartService";
import "../../components/customer/customer-menu.css";
import "../../components/customer/customer-cart.css";
import { fetchCustomerMenu, type CustomerMenuResponse } from "../../services/menuService";
import { createOrder, getTableInvoice } from "../../services/orderService";
import { validateDineInSession } from "../../services/tableSessionService";
import type {
  CreateOrderRequest,
  MenuCart,
  MenuItem,
  TableInvoice,
} from "../../types";
import { useOrderingSession } from "../../ordering/OrderingSessionProvider";
import { buildCartSessionSummary } from "../../ordering/cartSessionSummary";

const initialMenu: CustomerMenuResponse = { categories: [], items: [] };

function getInitialCart() {
  if (typeof window === "undefined") {
    return {};
  }

  return loadMenuCart();
}

function getCartItems(cart: MenuCart, items: MenuItem[]) {
  return items.filter((item) => (cart[item.id] ?? 0) > 0);
}

function buildOrderPayload(
  cart: MenuCart,
  selectedItems: MenuItem[],
  context: { tableCode: string; qrToken: string; sessionId: string; sessionToken: string },
): CreateOrderRequest {
  return {
    orderType: "DineIn",
    tableCode: context.tableCode!,
    qrToken: context.qrToken!,
    tableSessionId: context.sessionId!,
    items: selectedItems.map((item) => ({
      menuItemId: item.id,
      quantity: cart[item.id] ?? 0,
    })),
    promotionCode: null,
    customerPhoneNumber: null,
  };
}

export function CustomerCartPage() {
  const { formatMoney, locale, t } = useI18n();
  const navigate = useNavigate();
  const { context: orderContext, refresh } = useOrderingSession();
  const [customerMenu, setCustomerMenu] = useState(initialMenu);
  const [cart, setCart] = useState<MenuCart>(getInitialCart);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = useRef(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [invoice, setInvoice] = useState<TableInvoice | null>(null);
  const [invoiceError, setInvoiceError] = useState("");
  const [isInvoiceLoading, setIsInvoiceLoading] = useState(true);

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
          setErrorMessage(t("Không tải được thực đơn từ hệ thống."));
        }
      });

    return () => {
      isMounted = false;
    };
  }, [t]);

  useEffect(() => {
    let isMounted = true;

    void reconcileCartOnLoad()
      .then((nextCart) => {
        if (isMounted) {
          setCart(nextCart);
        }
      })
      .catch(() => undefined);

    const handleCartUpdated = () => {
      setCart(loadMenuCart());
    };

    window.addEventListener(CART_UPDATED_EVENT, handleCartUpdated);
    return () => {
      isMounted = false;
      window.removeEventListener(CART_UPDATED_EVENT, handleCartUpdated);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    setIsInvoiceLoading(true);
    setInvoiceError("");

    getTableInvoice(orderContext.sessionId, orderContext.sessionToken)
      .then((nextInvoice) => {
        if (isMounted) {
          setInvoice(nextInvoice);
        }
      })
      .catch(() => {
        if (isMounted) {
          setInvoice(null);
          setInvoiceError(t("Chưa tải được tổng các món đã gọi trong phiên."));
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsInvoiceLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [orderContext.sessionId, orderContext.sessionToken, t]);

  const selectedItems = useMemo(
    () => getCartItems(cart, customerMenu.items).map((item) => localizeMenuItem(item, locale)),
    [cart, customerMenu.items, locale],
  );
  const unavailableItems = selectedItems.filter((item) => !item.isAvailable);
  const summary = useMemo(
    () => buildCartSessionSummary(
      invoice,
      selectedItems.map((item) => ({
        quantity: cart[item.id] ?? 0,
        unitPrice: item.price,
      })),
    ),
    [cart, invoice, selectedItems],
  );
  const hasActiveSession = true;
  const tableMenuPath = `/table-session/${orderContext.sessionId}/menu`;
  const tableOrdersPath = `/table-session/${orderContext.sessionId}/orders`;
  const canSubmit =
    hasActiveSession &&
    selectedItems.length > 0 &&
    unavailableItems.length === 0 &&
    !isSubmitting;

  function updateQuantity(itemId: string, nextQuantity: number) {
    const delta = nextQuantity - (cart[itemId] ?? 0);
    if (delta === 0) {
      return;
    }

    void applyCartDelta(itemId, delta)
      .then((nextCart) => setCart(nextCart))
      .catch((error) => setErrorMessage(formatCartErrorMessage(error, t("Không cập nhật được giỏ hàng. Vui lòng thử lại."))));
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmittingRef.current) return;
    setErrorMessage("");

    if (!hasActiveSession) {
      setErrorMessage(t("Phiên bàn không hợp lệ. Vui lòng quét lại QR tại bàn để gọi món."));
      return;
    }

    if (!canSubmit) {
      setErrorMessage(t("Vui lòng kiểm tra giỏ hàng trước khi gửi đơn."));
      return;
    }

    const payload = buildOrderPayload(
      cart,
      selectedItems,
      orderContext,
    );
    isSubmittingRef.current = true;
    setIsSubmitting(true);

    try {
      const validation = await validateDineInSession(
        orderContext.sessionId!,
        orderContext.sessionToken!,
        orderContext.tableCode!,
      );
      if (validation.status !== "open") {
        if (validation.status === "error") {
          setErrorMessage(t("Chưa kiểm tra được phiên bàn. Vui lòng thử gửi món lại."));
          return;
        }
        await refresh();
        setErrorMessage(t(
          validation.status === "expired"
            ? "Phiên bàn đã hết hạn. Vui lòng quét lại QR tại bàn."
            : "Phiên bàn không còn hợp lệ. Vui lòng quét lại QR tại bàn.",
        ));
        return;
      }

      const response = await createOrder(payload);
      setCart({});
      clearMenuCart();

      navigate(`/table-session/${orderContext.sessionId}/orders?highlight=${encodeURIComponent(response.orderCode)}`, { replace: true });
    } catch (error) {
      setErrorMessage(t(error instanceof Error ? error.message : "Không thể gửi đơn lúc này."));
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <section className="cmc-customer-page cmc-cart-page">
      <header className="cmc-hero cmc-checkout-hero">
        <div>
          <p className="cmc-kicker">{t("Giỏ hàng tại bàn")}</p>
          <h2>
            {t("Rà soát món mới,")} <span>{t("nắm trọn tổng phiên")}</span>
          </h2>
          <p>
            {t("Món đã gọi và món đang chọn được tách riêng, giúp bạn kiểm tra đúng số tiền trước mỗi lần gửi bếp.")}
          </p>
          <div className="cmc-hero-actions">
            <Link className="cmc-secondary-link" to={tableMenuPath}>
              {t("Thêm món khác")}
            </Link>
            {orderContext.tableCode ? (
              <span className="cmc-table-badge">{t("Bàn {table}", { table: orderContext.tableCode })}</span>
            ) : null}
          </div>
        </div>
      </header>

      {!hasActiveSession ? (
        <div className="cmc-empty-state" role="alert">
          {t("Vui lòng quét QR tại bàn để mở phiên trước khi gửi món.")}
        </div>
      ) : null}

      <div className="cmc-checkout-layout">
        <div className="cmc-cart-panel" aria-label={t("Chi tiết giỏ hàng")}>
          <div className="cmc-section-title">
            <div>
              <small>{t("Lần gọi món tiếp theo")}</small>
              <h3>{t("Món đang chọn")}</h3>
            </div>
            <span>{t("{count} phần", { count: summary.selectedQuantity })}</span>
          </div>

          {selectedItems.length === 0 ? (
            <div className="cmc-empty-state">{t("Giỏ hàng đang trống.")}</div>
          ) : (
            <div className="cmc-cart-list">
              {selectedItems.map((item) => (
                <div className={item.isAvailable ? "cmc-cart-row" : "cmc-cart-row muted"} key={item.id}>
                  <img alt={item.name} src={item.imageUrl} />
                  <div className="cmc-cart-item-copy">
                    <strong>{item.name}</strong>
                    <span>
                      {formatMoney(item.price)} / {item.categoryName}
                    </span>
                    {!item.isAvailable ? <em>{t("Tạm hết, không thể đặt món này")}</em> : null}
                  </div>
                  <strong className="cmc-cart-line-total">
                    {formatMoney((cart[item.id] ?? 0) * item.price)}
                  </strong>
                  <div className="cmc-stepper">
                    <button
                      onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) - 1)}
                      type="button"
                    >
                      -
                    </button>
                    <span>{cart[item.id]}</span>
                    <button
                      disabled={!item.isAvailable}
                      onClick={() => updateQuantity(item.id, (cart[item.id] ?? 0) + 1)}
                      type="button"
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="cmc-cart-total">
            <span>{t("Tạm tính món đang chọn")}</span>
            <strong data-money>{formatMoney(summary.cartSubtotal)}</strong>
          </div>

          {unavailableItems.length > 0 ? (
            <p className="cmc-inline-error">
              {t("Có {count} món tạm hết. Vui lòng bỏ món đó khỏi giỏ trước khi đặt.", { count: unavailableItems.length })}
            </p>
          ) : null}
        </div>

        <form className="cmc-checkout-panel" onSubmit={submitOrder}>
          <div className="cmc-bill-heading">
            <span className="cmc-bill-icon" aria-hidden="true">
              <ReceiptText size={22} />
            </span>
            <div>
              <small>{t("Phiếu bàn {table}", { table: orderContext.tableCode ?? "--" })}</small>
              <h3>{t("Tổng quan phiên")}</h3>
            </div>
          </div>

          <div className="cmc-session-bill" aria-live="polite">
            <div className="cmc-bill-row">
              <span>
                {t("Đã gọi trong phiên")}
                <small>{t("{count} lần gọi món", { count: summary.orderRoundCount })}</small>
              </span>
              <strong data-money>{isInvoiceLoading ? t("Đang tải…") : invoiceError ? "--" : formatMoney(summary.orderedSubtotal)}</strong>
            </div>
            <div className="cmc-bill-row cmc-bill-row--cart">
              <span>
                {t("Đang chọn thêm")}
                <small>{t("{count} phần chưa gửi bếp", { count: summary.selectedQuantity })}</small>
              </span>
              <strong data-money>{formatMoney(summary.cartSubtotal)}</strong>
            </div>
            <div className="cmc-bill-divider" aria-hidden="true" />
            <div className="cmc-bill-total">
              <span>{t("Tổng sau khi gửi")}</span>
              <strong data-money>{isInvoiceLoading ? t("Đang tải…") : invoiceError ? "--" : formatMoney(summary.projectedTotal)}</strong>
            </div>
          </div>

          {invoiceError ? (
            <p className="cmc-inline-warning" role="status">
              {invoiceError} {t("Bạn vẫn có thể gửi món đang chọn.")}
            </p>
          ) : null}

          <Link className="cmc-session-orders-link" to={tableOrdersPath}>
            <ShoppingBasket aria-hidden="true" size={18} />
            {t("Xem món đã gọi")}
            <ArrowRight aria-hidden="true" size={17} />
          </Link>

          <p className="cmc-checkout-footnote">
            {t("Ưu đãi, tích điểm và thanh toán chỉ áp dụng khi bạn yêu cầu thanh toán toàn bộ phiên bàn.")}
          </p>

          {errorMessage ? <p className="cmc-inline-error">{errorMessage}</p> : null}

          <button className="cmc-submit-order" disabled={!canSubmit} type="submit">
            {isSubmitting ? (
              t("Đang gửi món...")
            ) : (
              <>
                <span>{t("Gửi món tới bếp")}</span>
                <small>{t("{count} phần trong lần gọi này", { count: summary.selectedQuantity })}</small>
              </>
            )}
          </button>
        </form>
      </div>
    </section>
  );
}
