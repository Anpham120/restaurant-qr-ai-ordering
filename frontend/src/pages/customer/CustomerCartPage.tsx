import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, ReceiptText, ShoppingBasket } from "lucide-react";
import { clearMenuCart, loadMenuCart, saveMenuCart } from "../../components/customer/customerMenuStorage";
import "../../components/customer/customer-menu.css";
import "../../components/customer/customer-cart.css";
import { formatVnd } from "../../components/menu/MenuItemCard";
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
          setErrorMessage("Không tải được thực đơn từ hệ thống.");
        }
      });

    return () => {
      isMounted = false;
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
          setInvoiceError("Chưa tải được tổng các món đã gọi trong phiên.");
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
  }, [orderContext.sessionId, orderContext.sessionToken]);

  const selectedItems = useMemo(
    () => getCartItems(cart, customerMenu.items),
    [cart, customerMenu.items],
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
    const nextCart = { ...cart };
    if (nextQuantity <= 0) {
      delete nextCart[itemId];
    } else {
      nextCart[itemId] = nextQuantity;
    }

    setCart(nextCart);
    saveMenuCart(nextCart);
  }

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmittingRef.current) return;
    setErrorMessage("");

    if (!hasActiveSession) {
      setErrorMessage("Phiên bàn không hợp lệ. Vui lòng quét lại QR tại bàn để gọi món.");
      return;
    }

    if (!canSubmit) {
      setErrorMessage("Vui lòng kiểm tra giỏ hàng trước khi gửi đơn.");
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
          setErrorMessage("Chưa kiểm tra được phiên bàn. Vui lòng thử gửi món lại.");
          return;
        }
        await refresh();
        setErrorMessage(
          validation.status === "expired"
            ? "Phiên bàn đã hết hạn. Vui lòng quét lại QR tại bàn."
            : "Phiên bàn không còn hợp lệ. Vui lòng quét lại QR tại bàn.",
        );
        return;
      }

      const response = await createOrder(payload);
      setCart({});
      clearMenuCart();

      navigate(`/table-session/${orderContext.sessionId}/orders/${response.orderCode}`, { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Không thể gửi đơn lúc này.");
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <section className="cmc-customer-page cmc-cart-page">
      <header className="cmc-hero cmc-checkout-hero">
        <div>
          <p className="cmc-kicker">Giỏ hàng tại bàn</p>
          <h2>
            Rà soát món mới, <span>nắm trọn tổng phiên</span>
          </h2>
          <p>
            Món đã gọi và món đang chọn được tách riêng, giúp bạn kiểm tra đúng số tiền trước mỗi lần gửi bếp.
          </p>
          <div className="cmc-hero-actions">
            <Link className="cmc-secondary-link" to={tableMenuPath}>
              Thêm món khác
            </Link>
            {orderContext.tableCode ? (
              <span className="cmc-table-badge">Bàn {orderContext.tableCode}</span>
            ) : null}
          </div>
        </div>
      </header>

      {!hasActiveSession ? (
        <div className="cmc-empty-state" role="alert">
          Vui lòng quét QR tại bàn để mở phiên trước khi gửi món.
        </div>
      ) : null}

      <div className="cmc-checkout-layout">
        <div className="cmc-cart-panel" aria-label="Chi tiết giỏ hàng">
          <div className="cmc-section-title">
            <div>
              <small>Lần gọi món tiếp theo</small>
              <h3>Món đang chọn</h3>
            </div>
            <span>{summary.selectedQuantity} phần</span>
          </div>

          {selectedItems.length === 0 ? (
            <div className="cmc-empty-state">Giỏ hàng đang trống.</div>
          ) : (
            <div className="cmc-cart-list">
              {selectedItems.map((item) => (
                <div className={item.isAvailable ? "cmc-cart-row" : "cmc-cart-row muted"} key={item.id}>
                  <img alt={item.name} src={item.imageUrl} />
                  <div className="cmc-cart-item-copy">
                    <strong>{item.name}</strong>
                    <span>
                      {formatVnd(item.price)} / {item.categoryName}
                    </span>
                    {!item.isAvailable ? <em>Tạm hết, không thể đặt món này</em> : null}
                  </div>
                  <strong className="cmc-cart-line-total">
                    {formatVnd((cart[item.id] ?? 0) * item.price)}
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
            <span>Tạm tính món đang chọn</span>
            <strong>{formatVnd(summary.cartSubtotal)}</strong>
          </div>

          {unavailableItems.length > 0 ? (
            <p className="cmc-inline-error">
              Có {unavailableItems.length} món tạm hết. Vui lòng bỏ món đó khỏi giỏ trước khi đặt.
            </p>
          ) : null}
        </div>

        <form className="cmc-checkout-panel" onSubmit={submitOrder}>
          <div className="cmc-bill-heading">
            <span className="cmc-bill-icon" aria-hidden="true">
              <ReceiptText size={22} />
            </span>
            <div>
              <small>Phiếu bàn {orderContext.tableCode ?? "--"}</small>
              <h3>Tổng quan phiên</h3>
            </div>
          </div>

          <div className="cmc-session-bill" aria-live="polite">
            <div className="cmc-bill-row">
              <span>
                Đã gọi trong phiên
                <small>{summary.orderRoundCount} lần gọi món</small>
              </span>
              <strong>{isInvoiceLoading ? "Đang tải…" : invoiceError ? "--" : formatVnd(summary.orderedSubtotal)}</strong>
            </div>
            <div className="cmc-bill-row cmc-bill-row--cart">
              <span>
                Đang chọn thêm
                <small>{summary.selectedQuantity} phần chưa gửi bếp</small>
              </span>
              <strong>{formatVnd(summary.cartSubtotal)}</strong>
            </div>
            <div className="cmc-bill-divider" aria-hidden="true" />
            <div className="cmc-bill-total">
              <span>Tổng sau khi gửi</span>
              <strong>{isInvoiceLoading ? "Đang tải…" : invoiceError ? "--" : formatVnd(summary.projectedTotal)}</strong>
            </div>
          </div>

          {invoiceError ? (
            <p className="cmc-inline-warning" role="status">
              {invoiceError} Bạn vẫn có thể gửi món đang chọn.
            </p>
          ) : null}

          <Link className="cmc-session-orders-link" to={tableOrdersPath}>
            <ShoppingBasket aria-hidden="true" size={18} />
            Xem món đã gọi
            <ArrowRight aria-hidden="true" size={17} />
          </Link>

          <p className="cmc-checkout-footnote">
            Ưu đãi, tích điểm và thanh toán chỉ áp dụng khi bạn yêu cầu thanh toán toàn bộ phiên bàn.
          </p>

          {errorMessage ? <p className="cmc-inline-error">{errorMessage}</p> : null}

          <button className="cmc-submit-order" disabled={!canSubmit} type="submit">
            {isSubmitting ? (
              "Đang gửi món..."
            ) : (
              <>
                <span>Gửi món tới bếp</span>
                <small>{summary.selectedQuantity} phần trong lần gọi này</small>
              </>
            )}
          </button>
        </form>
      </div>
    </section>
  );
}
